import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# =========================
# VALIDATION
# =========================
def valid_emp_id(eid):
    return isinstance(eid,str) and eid.startswith("E") and len(eid)==4 and eid[1:].isdigit()

def valid_shift_id(sid):
    return isinstance(sid,str) and sid.startswith("SH")

def valid_att_id(aid):
    return isinstance(aid,str) and aid.startswith("A")

# =========================
# CONNECT
# =========================
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

# =========================
# PAY
# =========================
def calc(h,rate,t):
    if t=="Full-Time":
        reg=min(h,8)*rate
        ot=max(0,h-8)*rate*1.5
    else:
        reg=h*rate
        ot=0
    gross=reg+ot
    tax=gross*0.1
    return reg,ot,gross,tax,gross-tax

def safe_float(x):
    try:
        return float(x)
    except:
        return 0

# =========================
# UI
# =========================
st.title("🏢 ERP SYSTEM")

menu=st.sidebar.selectbox("Menu",
["Employee","Shift","Attendance","Payroll"])

# =========================
# EMPLOYEE（不動）
# =========================
if menu=="Employee":
    st.header("Employee")

    data=db["emp"].get_all_records()

    st.dataframe(data)

# =========================
# SHIFT（修正欄位）
# =========================
elif menu=="Shift":
    st.header("Shift System")

    action=st.selectbox("Action",
    ["Add","By Date","By Employee"])

    data=db["shift"].get_all_records()

    if action=="Add":
        eid=st.text_input("Employee").strip()

        if eid and not valid_emp_id(eid):
            st.error("❌ Use E001")
            st.stop()

        date=st.text_input("Date").strip()
        start_time=st.text_input("Start Time")
        end_time=st.text_input("End Time")
        location=st.text_input("Location")

        if st.button("Add"):
            new=f"SH{len(data)+1:03d}"

            db["shift"].append_row([
                new,
                eid,
                date,
                start_time,
                end_time,
                location,
                "Scheduled"
            ])

            st.success("Added")

    elif action=="By Date":
        d=st.text_input("Date").strip()

        res=[s for s in data if str(s["date"]).strip()==d]

        if not res:
            st.warning("No data")

        st.dataframe(res)

    elif action=="By Employee":
        eid=st.text_input("Employee").strip()

        if eid and not valid_emp_id(eid):
            st.error("❌ Use E001")
            st.stop()

        res=[s for s in data if s["employee_id"]==eid]

        if not res:
            st.warning("No data")

        st.dataframe(res)

# =========================
# ATTENDANCE（修正日期）
# =========================
elif menu=="Attendance":
    st.header("Attendance")

    action=st.selectbox("Action",
    ["Check In","By Date","By Employee"])

    data=db["att"].get_all_records()

    if action=="Check In":
        eid=st.text_input("Employee").strip()
        sid=st.text_input("Shift ID").strip()
        date=st.text_input("Date").strip()
        h=st.number_input("Hours",0.0)

        if eid and not valid_emp_id(eid):
            st.error("❌ E001")
            st.stop()

        if st.button("Submit"):
            new=f"A{len(data)+1:03d}"

            db["att"].append_row([
                new,
                sid,
                eid,
                date,
                h,
                "Present" if h>0 else "Absent",
                ""
            ])

            st.success("Done")

    elif action=="By Date":
        d=st.text_input("Date").strip()

        res=[a for a in data if str(a["date"]).strip()==d]

        if not res:
            st.warning("No data")

        st.dataframe(res)

    elif action=="By Employee":
        eid=st.text_input("Employee").strip()

        res=[a for a in data if a["employee_id"]==eid]

        if not res:
            st.warning("No data")

        st.dataframe(res)

# =========================
# PAYROLL（修正所有錯）
# =========================
elif menu=="Payroll":
    st.header("Payroll")

    action=st.selectbox("Action",
    ["Daily","Weekly"])

    emp=db["emp"].get_all_records()
    att=db["att"].get_all_records()

    def get_emp(eid):
        return next((e for e in emp if e["employee_id"]==eid),None)

    if action=="Daily":
        eid=st.text_input("Employee").strip()
        d=st.text_input("Date").strip()

        rec=[
            a for a in att
            if a["employee_id"]==eid
            and str(a["date"]).strip()==d
        ]

        if rec:
            e=get_emp(eid)

            if not e:
                st.error("Employee not found")
                st.stop()

            h=sum(safe_float(a["actual_hours"]) for a in rec)

            _,_,_,_,n=calc(
                h,
                safe_float(e.get("hourly_rate",0)),
                e.get("employment_type","Part-Time")
            )

            st.success(f"💰 {n}")
        else:
            st.warning("No data")

    elif action=="Weekly":
        eid=st.text_input("Employee").strip()
        s=st.text_input("Start")
        e=st.text_input("End")

        if not (s.isdigit() and e.isdigit()):
            st.error("❌ YYYYMMDD")
            st.stop()

        rec=[
            a for a in att
            if a["employee_id"]==eid
            and str(a["date"]).strip().isdigit()
            and int(s)<=int(str(a["date"]).strip())<=int(e)
        ]

        if rec:
            emp_data=get_emp(eid)

            if not emp_data:
                st.error("Employee not found")
                st.stop()

            h=sum(safe_float(a["actual_hours"]) for a in rec)

            _,_,_,_,n=calc(
                h,
                safe_float(emp_data.get("hourly_rate",0)),
                emp_data.get("employment_type","Part-Time")
            )

            st.success(f"💰 {n}")
        else:
            st.warning("No data")
