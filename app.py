import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="ERP SYSTEM", layout="wide")
st.title("🏢 ERP SYSTEM")

# -----------------------
# Utils
# -----------------------
def error(msg):
    st.warning(f"⚠️ {msg}")
    st.stop()

def fix_employee_id(eid):
    if not eid:
        error("Employee ID required")
    eid = eid.strip().upper()
    if not eid.startswith("E"):
        eid = "E" + eid
    if not eid[1:].isdigit():
        error("Employee ID format must be like E001")
    return eid

def fix_date(d):
    d = d.strip().replace("/", "").replace("-", "")
    if len(d) != 8 or not d.isdigit():
        error("Date must be YYYYMMDD")
    return d

def fix_time(t):
    t = t.strip()
    if ":" not in t:
        error("Time must be HH:MM")
    h, m = t.split(":")
    if not (h.isdigit() and m.isdigit()):
        error("Time must be numeric")
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        error("Invalid time")
    return f"{h:02d}:{m:02d}"

def safe_float(v):
    try:
        return float(v)
    except:
        return 0

# -----------------------
# Google Sheet
# -----------------------
@st.cache_resource
def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["google"],
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)

    sheet = client.open_by_key("1Y_BD6eCM_jt-FzwNjVrocPmRGr104pQcY1qoPPN2pnE")

    return {
        "emp": sheet.worksheet("Employees"),
        "shift": sheet.worksheet("Shifts"),
        "att": sheet.worksheet("Attendance")
    }

db = connect()

# -----------------------
# Load data
# -----------------------
emp_list = db["emp"].get_all_records()
shift_list = db["shift"].get_all_records()
att_list = db["att"].get_all_records()

emp_ids = [e["employee_id"] for e in emp_list]

# -----------------------
# Tabs
# -----------------------
tab1, tab2, tab3, tab4 = st.tabs(["Employees", "Shifts", "Attendance", "Payroll"])

# =====================================================
# ⏰ ATTENDANCE（已修）
# =====================================================
with tab3:
    st.header("Attendance System")

    action = st.selectbox("Action", ["Clock In","By Employee","By Date","No-show","Edit Notes","All"])

    if action == "Clock In":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        date = fix_date(st.text_input("Date"))
        h = safe_float(st.text_input("Hours"))

        status = "No-Show" if h==0 else ("Late" if h<8 else "Present")

        if st.button("Clock", key="att_clock"):
            # 🔥 找 shift_id
            shift_id = "-"
            for s in shift_list:
                if s["employee_id"] == eid and str(s["date"]) == str(date):
                    shift_id = s["shift_id"]

            aid = f"A{len(att_list)+1:03d}"

            # 🔥 寫入正確欄位順序
            db["att"].append_row([
                aid,
                shift_id,
                eid,
                str(date),
                h,
                status,
                ""
            ])

            st.success("Recorded")

    elif action == "By Employee":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        res = [a for a in att_list if a["employee_id"] == eid]
        st.dataframe(res if res else [{"Info":"No data"}])

    elif action == "By Date":
        d = fix_date(st.text_input("Date"))
        res = [a for a in att_list if str(a["date"]) == str(d)]
        st.dataframe(res if res else [{"Info":"No data"}])

    elif action == "No-show":
        res = [a for a in att_list if a["status"]=="No-Show"]
        st.dataframe(res if res else [{"Info":"No data"}])

    elif action == "Edit Notes":
        aid = st.text_input("Attendance ID")
        note = st.text_input("Note")

        if st.button("Save", key="att_note"):
            found = False
            for i,a in enumerate(att_list):
                if a["attendance_id"] == aid:
                    db["att"].update(f"G{i+2}", [[note]])
                    st.success("Updated")
                    found = True
            if not found:
                st.warning("⚠️ Attendance ID not found")

    elif action == "All":
        st.dataframe(att_list if att_list else [{"Info":"No data"}])

# =====================================================
# 💵 PAYROLL（已修）
# =====================================================
with tab4:
    st.header("Payroll System")

    action = st.selectbox("Action", ["Daily","Weekly","Ranking","Stats","Total"])

    if action == "Daily":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        d = fix_date(st.text_input("Date"))

        found = False

        for a in att_list:
            if a["employee_id"]==eid and str(a["date"])==str(d):

                emp = next(e for e in emp_list if e["employee_id"]==eid)

                hours = safe_float(a.get("actual_hours",0))
                rate = safe_float(emp.get("hourly_rate",0))

                pay = hours * rate

                st.success(f"💵 ${pay}")
                found = True

        if not found:
            st.warning("⚠️ No attendance record found")

    elif action == "Weekly":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        s = fix_date(st.text_input("Start"))
        e = fix_date(st.text_input("End"))

        total = 0
        found = False

        for a in att_list:
            if a["employee_id"]==eid and int(s)<=int(str(a["date"]))<=int(e):

                emp = next(e for e in emp_list if e["employee_id"]==eid)

                hours = safe_float(a.get("actual_hours",0))
                rate = safe_float(emp.get("hourly_rate",0))

                total += hours * rate
                found = True

        if found:
            st.success(f"💰 ${total}")
        else:
            st.warning("⚠️ No records in range")

    elif action == "Ranking":
        res = {}

        for a in att_list:
            eid = a["employee_id"]

            emp = next(e for e in emp_list if e["employee_id"]==eid)

            hours = safe_float(a.get("actual_hours",0))
            rate = safe_float(emp.get("hourly_rate",0))

            pay = hours * rate

            res[eid] = res.get(eid,0) + pay

        st.dataframe(
            sorted(res.items(), key=lambda x:x[1], reverse=True)
            if res else [{"Info":"No data"}]
        )

    elif action == "Stats":
        res = {}

        for a in att_list:
            res[a["status"]] = res.get(a["status"],0)+1

        st.dataframe(
            [{"Status":k,"Count":v} for k,v in res.items()]
            if res else [{"Info":"No data"}]
        )

    elif action == "Total":
        total = 0

        for a in att_list:
            eid = a["employee_id"]
            emp = next(e for e in emp_list if e["employee_id"]==eid)

            hours = safe_float(a.get("actual_hours",0))
            rate = safe_float(emp.get("hourly_rate",0))

            total += hours * rate

        if total == 0:
            st.warning("⚠️ No data")
        else:
            st.success(f"💰 ${total}")
