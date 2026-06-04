import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="ERP SYSTEM", layout="wide")
st.title("🏢 ERP SYSTEM")

# -----------------------
# ERROR HANDLER
# -----------------------
def error(msg):
    st.warning(f"⚠️ {msg}")
    st.stop()

# -----------------------
# FIX INPUT
# -----------------------
def fix_employee_id(eid):
    eid = eid.strip().upper()
    if not eid.startswith("E"):
        eid = "E" + eid
    if not eid[1:].isdigit():
        error("Employee ID must be like E001")
    return eid

def fix_date(d):
    d = d.strip().replace("/", "").replace("-", "")
    if len(d) != 8 or not d.isdigit():
        error("Date must be YYYYMMDD")
    return d

def fix_time(t):
    if ":" not in t:
        error("Time must be HH:MM")
    h,m = t.split(":")
    if not(h.isdigit() and m.isdigit()):
        error("Time must be numeric")
    h,m=int(h),int(m)
    if not(0<=h<=23 and 0<=m<=59):
        error("Invalid time")
    return f"{h:02d}:{m:02d}"

def safe_float(x):
    try:
        return float(x)
    except:
        return 0

# -----------------------
# CONNECT
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
        "shift": sheet.worksheet("Shifts"),   # ✅ 修正
        "att": sheet.worksheet("Attendance")
    }

db = connect()

# -----------------------
# LOAD DATA
# -----------------------
emp_list = db["emp"].get_all_records()
shift_list = db["shift"].get_all_records()
att_list = db["att"].get_all_records()

emp_ids = [e["employee_id"] for e in emp_list]

# -----------------------
# MENU
# -----------------------
menu = st.sidebar.selectbox("Menu", ["Employee","Shift","Attendance","Payroll"])

# =====================================================
# 👥 EMPLOYEE
# =====================================================
if menu=="Employee":
    st.header("Employee System")

    action = st.selectbox("Action", ["Add","View","Search","Edit","Profile"])

    if action=="Add":
        eid = fix_employee_id(st.text_input("Employee ID"))
        name = st.text_input("Name")
        role = st.text_input("Role")
        dept = st.text_input("Department")
        rate = st.text_input("Hourly Rate")
        etype = st.selectbox("Type",["Full-Time","Part-Time"])
        phone = st.text_input("Phone")
        email = st.text_input("Email")

        if st.button("Add",key="emp_add"):
            db["emp"].append_row([eid,name,role,dept,rate,etype,phone,email])
            st.success("Added")

    elif action=="View":
        st.dataframe(emp_list)

    elif action=="Search":
        k = st.text_input("Keyword")
        res = [e for e in emp_list if k.lower() in str(e).lower()]
        st.dataframe(res)

    elif action=="Edit":
        eid = st.selectbox("Employee", emp_ids)
        emp = next(e for e in emp_list if e["employee_id"]==eid)

        name = st.text_input("Name",emp["name"])
        role = st.text_input("Role",emp["role"])
        dept = st.text_input("Department",emp["department"])
        rate = st.text_input("Rate",emp["hourly_rate"])
        etype = st.selectbox("Type",["Full-Time","Part-Time"])
        phone = st.text_input("Phone",emp["phone"])
        email = st.text_input("Email",emp["email"])

        if st.button("Save",key="emp_save"):
            i = emp_list.index(emp)
            db["emp"].update(f"A{i+2}:H{i+2}",[[eid,name,role,dept,rate,etype,phone,email]])
            st.success("Updated")

    elif action=="Profile":
        eid = st.selectbox("Employee",emp_ids)
        emp = next(e for e in emp_list if e["employee_id"]==eid)
        st.json(emp)

# =====================================================
# 📅 SHIFT
# =====================================================
elif menu=="Shift":
    st.header("Shift System")

    action = st.selectbox("Action",["Add","By Date","By Employee","Cancel","Future"])

    if action=="Add":
        eid = fix_employee_id(st.selectbox("Employee",emp_ids))
        date = fix_date(st.text_input("Date"))
        start = fix_time(st.text_input("Start"))
        end = fix_time(st.text_input("End"))
        loc = st.text_input("Location")

        if start >= end:
            error("End must be after start")

        for s in shift_list:
            if s["employee_id"]==eid and str(s["date"])==date:
                if not(end<=s["start_time"] or start>=s["end_time"]):
                    error("Shift conflict")

        if st.button("Add",key="shift_add"):
            sid=f"S{len(shift_list)+1:03d}"
            db["shift"].append_row([sid,eid,date,start,end,loc,"Scheduled"])
            st.success("Added")

    elif action=="By Date":
        d = fix_date(st.text_input("Date"))
        st.dataframe([s for s in shift_list if str(s["date"])==d])

    elif action=="By Employee":
        eid = fix_employee_id(st.selectbox("Employee",emp_ids))
        st.dataframe([s for s in shift_list if s["employee_id"]==eid])

    elif action=="Cancel":
        sid = st.text_input("Shift ID")
        if st.button("Cancel",key="shift_cancel"):
            for i,s in enumerate(shift_list):
                if s["shift_id"]==sid:
                    db["shift"].update(f"G{i+2}",[["Cancelled"]])
                    st.success("Cancelled")

    elif action=="Future":
        st.dataframe([s for s in shift_list if s["status"]=="Scheduled"])

# =====================================================
# ⏰ ATTENDANCE
# =====================================================
elif menu=="Attendance":
    st.header("Attendance System")

    action = st.selectbox("Action",["Clock","By Employee","By Date","No-show","Edit Notes","All"])

    if action=="Clock":
        eid = fix_employee_id(st.selectbox("Employee",emp_ids))
        date = fix_date(st.text_input("Date"))
        h = safe_float(st.text_input("Hours"))

        status = "No-Show" if h==0 else ("Late" if h<8 else "Present")

        if st.button("Clock",key="att_clock"):
            aid=f"A{len(att_list)+1:03d}"
            db["att"].append_row([aid,"-",eid,date,h,status,""])
            st.success("Recorded")

    elif action=="By Employee":
        eid = fix_employee_id(st.selectbox("Employee",emp_ids))
        st.dataframe([a for a in att_list if a["employee_id"]==eid])

    elif action=="By Date":
        d = fix_date(st.text_input("Date"))
        st.dataframe([a for a in att_list if str(a["date"])==d])

    elif action=="No-show":
        st.dataframe([a for a in att_list if a["status"]=="No-Show"])

    elif action=="Edit Notes":
        aid = st.text_input("Attendance ID")
        note = st.text_input("Note")

        if st.button("Save",key="att_save"):
            for i,a in enumerate(att_list):
                if a["attendance_id"]==aid:
                    db["att"].update(f"G{i+2}",[[note]])
                    st.success("Updated")

    elif action=="All":
        st.dataframe(att_list)

# =====================================================
# 💵 PAYROLL
# =====================================================
elif menu=="Payroll":
    st.header("Payroll System")

    action = st.selectbox("Action",["Daily","Weekly","Ranking","Stats","Total"])

    if action=="Daily":
        eid = fix_employee_id(st.selectbox("Employee",emp_ids))
        d = fix_date(st.text_input("Date"))

        for a in att_list:
            if a["employee_id"]==eid and str(a["date"])==d:
                emp = next(e for e in emp_list if e["employee_id"]==eid)
                pay = safe_float(a["actual_hours"]) * safe_float(emp["hourly_rate"])
                st.success(pay)

    elif action=="Weekly":
        eid = fix_employee_id(st.selectbox("Employee",emp_ids))
        s = fix_date(st.text_input("Start"))
        e = fix_date(st.text_input("End"))

        total=0
        for a in att_list:
            if a["employee_id"]==eid and int(s)<=int(a["date"])<=int(e):
                emp = next(e for e in emp_list if e["employee_id"]==eid)
                total+=safe_float(a["actual_hours"])*safe_float(emp["hourly_rate"])
        st.success(total)

    elif action=="Ranking":
        res={}
        for a in att_list:
            eid=a["employee_id"]
            emp = next(e for e in emp_list if e["employee_id"]==eid)
            pay=safe_float(a["actual_hours"])*safe_float(emp["hourly_rate"])
            res[eid]=res.get(eid,0)+pay
        st.dataframe(sorted(res.items(),key=lambda x:x[1],reverse=True))

    elif action=="Stats":
        res={}
        for a in att_list:
            res[a["status"]]=res.get(a["status"],0)+1
        st.json(res)

    elif action=="Total":
        total=0
        for a in att_list:
            eid=a["employee_id"]
            emp = next(e for e in emp_list if e["employee_id"]==eid)
            total+=safe_float(a["actual_hours"])*safe_float(emp["hourly_rate"])
        st.success(total)
