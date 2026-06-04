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
# 👥 EMPLOYEE SYSTEM
# =====================================================
with tab1:
    st.header("Employee System")

    action = st.selectbox("Action", ["View", "Add", "Edit", "Search", "Profile"])

    if action == "View":
        st.dataframe(emp_list)

    elif action == "Add":
        eid = fix_employee_id(st.text_input("Employee ID"))
        name = st.text_input("Name")
        role = st.text_input("Role")
        dept = st.text_input("Department")
        rate = st.text_input("Hourly Rate")
        etype = st.selectbox("Type", ["Full-Time", "Part-Time"])
        phone = st.text_input("Phone")
        email = st.text_input("Email")

        if st.button("Add", key="emp_add"):
            db["emp"].append_row([eid,name,role,dept,rate,etype,phone,email])
            st.success("Added")

    elif action == "Edit":
        eid = st.selectbox("Employee", emp_ids)
        emp = next(e for e in emp_list if e["employee_id"] == eid)

        name = st.text_input("Name", emp["name"])
        role = st.text_input("Role", emp["role"])
        dept = st.text_input("Department", emp["department"])
        rate = st.text_input("Hourly Rate", emp["hourly_rate"])
        etype = st.selectbox("Type", ["Full-Time","Part-Time"])
        phone = st.text_input("Phone", emp["phone"])
        email = st.text_input("Email", emp["email"])

        if st.button("Save", key="emp_save"):
            i = emp_list.index(emp)
            db["emp"].update(f"A{i+2}:H{i+2}", [[eid,name,role,dept,rate,etype,phone,email]])
            st.success("Updated")

    elif action == "Search":
        keyword = st.text_input("Search")
        res = [e for e in emp_list if keyword.lower() in str(e).lower()]
        st.dataframe(res)

    elif action == "Profile":
        eid = st.selectbox("Employee", emp_ids)
        emp = next(e for e in emp_list if e["employee_id"] == eid)
        st.json(emp)

# =====================================================
# 📅 SHIFT SYSTEM
# =====================================================
with tab2:
    st.header("Shift System")

    action = st.selectbox("Action", ["Add","By Date","By Employee","Cancel","Future"])

    if action == "Add":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        date = fix_date(st.text_input("Date"))
        start = fix_time(st.text_input("Start"))
        end = fix_time(st.text_input("End"))
        location = st.text_input("Location")

        if start >= end:
            error("End time must be after start")

        # conflict
        for s in shift_list:
            if s["employee_id"] == eid and str(s["date"]) == str(date):
                if not (end <= s["start_time"] or start >= s["end_time"]):
                    error("Shift conflict")

        if st.button("Add", key="shift_add"):
            sid = f"S{len(shift_list)+1:03d}"
            db["shift"].append_row([sid,eid,date,start,end,location,"Scheduled"])
            st.success("Added")

    elif action == "By Date":
        d = fix_date(st.text_input("Date"))
        res = [s for s in shift_list if str(s["date"]) == d]
        st.dataframe(res)

    elif action == "By Employee":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        res = [s for s in shift_list if s["employee_id"] == eid]
        st.dataframe(res)

    elif action == "Cancel":
        sid = st.text_input("Shift ID")

        if st.button("Cancel", key="shift_cancel"):
            for i,s in enumerate(shift_list):
                if s["shift_id"] == sid:
                    db["shift"].update(f"G{i+2}", [["Cancelled"]])
                    st.success("Cancelled")

    elif action == "Future":
        res = [s for s in shift_list if s["status"]=="Scheduled"]
        st.dataframe(res)

# =====================================================
# ⏰ ATTENDANCE SYSTEM
# =====================================================
with tab3:
    st.header("Attendance System")

    action = st.selectbox("Action", ["Clock In","By Employee","By Date","No-show","Edit Notes","All"])

    if action == "Clock In":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        date = fix_date(st.text_input("Date"))
        hours = st.text_input("Hours")

        h = safe_float(hours)

        if h == 0:
            status = "No-Show"
        elif h < 8:
            status = "Late"
        else:
            status = "Present"

        if st.button("Clock", key="att_clock"):
            aid = f"A{len(att_list)+1:03d}"
            db["att"].append_row([aid,"-",eid,date,h,status,""])
            st.success("Recorded")

    elif action == "By Employee":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        res = [a for a in att_list if a["employee_id"] == eid]
        st.dataframe(res)

    elif action == "By Date":
        d = fix_date(st.text_input("Date"))
        res = [a for a in att_list if str(a["date"]) == d]
        st.dataframe(res)

    elif action == "No-show":
        res = [a for a in att_list if a["status"]=="No-Show"]
        st.dataframe(res)

    elif action == "Edit Notes":
        aid = st.text_input("Attendance ID")
        note = st.text_input("Note")

        if st.button("Save", key="att_note"):
            for i,a in enumerate(att_list):
                if a["attendance_id"] == aid:
                    db["att"].update(f"G{i+2}", [[note]])
                    st.success("Updated")

    elif action == "All":
        st.dataframe(att_list)

# =====================================================
# 💵 PAYROLL
# =====================================================
with tab4:
    st.header("Payroll System")

    action = st.selectbox("Action", ["Daily","Weekly","Ranking","Stats","Total"])

    if action == "Daily":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        d = fix_date(st.text_input("Date"))

        for a in att_list:
            if a["employee_id"]==eid and str(a["date"])==d:
                emp = next(e for e in emp_list if e["employee_id"]==eid)
                pay = safe_float(a["actual_hours"]) * safe_float(emp["hourly_rate"])
                st.success(f"${pay}")

    elif action == "Weekly":
        eid = fix_employee_id(st.selectbox("Employee", emp_ids))
        s = fix_date(st.text_input("Start"))
        e = fix_date(st.text_input("End"))

        total = 0
        for a in att_list:
            if a["employee_id"]==eid and int(s)<=int(a["date"])<=int(e):
                emp = next(e for e in emp_list if e["employee_id"]==eid)
                total += safe_float(a["actual_hours"]) * safe_float(emp["hourly_rate"])

        st.success(f"${total}")

    elif action == "Ranking":
        res = {}
        for a in att_list:
            eid = a["employee_id"]
            emp = next(e for e in emp_list if e["employee_id"]==eid)
            pay = safe_float(a["actual_hours"]) * safe_float(emp["hourly_rate"])
            res[eid] = res.get(eid,0)+pay

        st.dataframe(sorted(res.items(), key=lambda x:x[1], reverse=True))

    elif action == "Stats":
        res = {}
        for a in att_list:
            res[a["status"]] = res.get(a["status"],0)+1
        st.json(res)

    elif action == "Total":
        total = 0
        for a in att_list:
            eid = a["employee_id"]
            emp = next(e for e in emp_list if e["employee_id"]==eid)
            total += safe_float(a["actual_hours"]) * safe_float(emp["hourly_rate"])

        st.success(f"${total}")
