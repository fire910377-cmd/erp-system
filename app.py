import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="ERP SYSTEM", layout="wide")

# =====================
# CONNECT
# =====================
@st.cache_resource
def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["google"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)

    sheet = client.open_by_key("1Y_BD6eCM_jt-FzwNjVrocPmRGr104pQcY1qoPPN2pnE")

    return {
        "emp": sheet.worksheet("employees"),
        "shift": sheet.worksheet("shift"),
        "att": sheet.worksheet("attendance")
    }

db = connect()

# =====================
# SAFE FUNCTIONS
# =====================
def safe_float(x):
    try:
        return float(x)
    except:
        return 0

def safe_int(x):
    try:
        return int(x)
    except:
        return 0

def calc(hours, rate, emp_type):
    reg = hours * rate
    ot = 0
    gross = reg + ot
    tax = gross * 0.1
    net = gross - tax
    return reg, ot, gross, tax, net

def valid_eid(eid):
    return eid.startswith("E") and eid[1:].isdigit()

# =====================
# LOAD DATA
# =====================
emp = db["emp"].get_all_records()
shift = db["shift"].get_all_records()
att = db["att"].get_all_records()

# =====================
# UI
# =====================
st.title("🏢 ERP SYSTEM")

menu = st.selectbox("System", ["Employee","Shift","Attendance","Payroll"])

# =====================
# EMPLOYEE
# =====================
if menu=="Employee":
    st.header("Employee System")
    action = st.selectbox("Action",["Add","View","Search","Edit","Profile"])

    if action=="Add":
        eid=st.text_input("Employee ID")
        name=st.text_input("Name")
        role=st.text_input("Role")
        dept=st.text_input("Department")
        rate=st.text_input("Hourly Rate")
        etype=st.selectbox("Employment Type",["Full-Time","Part-Time"])
        phone=st.text_input("Phone")
        email=st.text_input("Email")

        if st.button("Add"):
            if not valid_eid(eid):
                st.warning("Employee ID must be like E001")
            else:
                db["emp"].append_row([eid,name,role,dept,rate,etype,phone,email])
                st.success("Added")

    elif action=="View":
        st.dataframe(emp)

    elif action=="Search":
        k=st.text_input("Employee ID")
        if k:
            res=[e for e in emp if e["employee_id"]==k]
            st.write(res)

    elif action=="Edit":
        k=st.text_input("Employee ID")
        for i,e in enumerate(emp):
            if e["employee_id"]==k:
                name=st.text_input("Name",e["name"])
                role=st.text_input("Role",e["role"])
                dept=st.text_input("Department",e["department"])
                rate=st.text_input("Rate",e["hourly_rate"])
                etype=st.text_input("Type",e["employment_type"])
                phone=st.text_input("Phone",e["phone"])
                email=st.text_input("Email",e["email"])

                if st.button("Save",key="emp_save"):
                    db["emp"].update(f"B{i+2}:H{i+2}",[[name,role,dept,rate,etype,phone,email]])
                    st.success("Updated")

    elif action=="Profile":
        k=st.text_input("Employee ID")
        for e in emp:
            if e["employee_id"]==k:
                st.json(e)

# =====================
# SHIFT
# =====================
elif menu=="Shift":
    st.header("Shift System")
    action=st.selectbox("Action",["Add","By Date","By Employee","Cancel"])

    if action=="Add":
        eid=st.text_input("Employee")
        d=st.text_input("Date")
        s=st.text_input("Start")
        e=st.text_input("End")
        loc=st.text_input("Location")

        if st.button("Add"):
            db["shift"].append_row(["S"+str(len(shift)+1),eid,d,s,e,loc,"Scheduled"])
            st.success("Added")

    elif action=="By Date":
        d=st.text_input("Date")
        res=[s for s in shift if str(s["date"])==str(d)]
        st.write(res)

    elif action=="By Employee":
        eid=st.text_input("Employee")
        res=[s for s in shift if s["employee_id"]==eid]
        st.write(res)

    elif action=="Cancel":
        sid=st.text_input("Shift ID")
        for i,s in enumerate(shift):
            if s["shift_id"]==sid:
                if st.button("Cancel",key="shift_cancel"):
                    db["shift"].update(f"G{i+2}",[["Cancelled"]])
                    st.success("Cancelled")

# =====================
# ATTENDANCE
# =====================
elif menu=="Attendance":
    st.header("Attendance System")
    action=st.selectbox("Action",["Clock","By Employee","By Date","No Show","Edit Notes","All"])

    if action=="Clock":
        eid=st.text_input("Employee")
        d=st.text_input("Date")
        h=st.text_input("Hours")

        if st.button("Clock"):
            db["att"].append_row(["A"+str(len(att)+1),"",eid,d,h,"Present",""])
            st.success("Clocked")

    elif action=="By Employee":
        eid=st.text_input("Employee")
        res=[a for a in att if a["employee_id"]==eid]
        st.write(res)

    elif action=="By Date":
        d=st.text_input("Date")
        res=[a for a in att if str(a["date"])==str(d)]
        st.write(res)

    elif action=="No Show":
        eid=st.text_input("Employee")
        d=st.text_input("Date")
        if st.button("Mark"):
            db["att"].append_row(["A"+str(len(att)+1),"",eid,d,0,"No-show",""])
            st.success("Marked")

    elif action=="Edit Notes":
        aid=st.text_input("Attendance ID")
        note=st.text_input("Note")

        if st.button("Save",key="att_save"):
            for i,a in enumerate(att):
                if a["attendance_id"]==aid:
                    db["att"].update(f"G{i+2}",[[note]])
                    st.success("Updated")

    elif action=="All":
        st.dataframe(att)

# =====================
# PAYROLL
# =====================
elif menu=="Payroll":
    st.header("Payroll System")
    action=st.selectbox("Action",["Daily","Weekly","Total"])

    if action=="Daily":
        eid=st.text_input("Employee")
        d=st.text_input("Date")

        for a in att:
            if a["employee_id"]==eid and str(a["date"])==str(d):
                for e in emp:
                    if e["employee_id"]==eid:
                        h=safe_float(a["actual_hours"])
                        _,_,g,t,n=calc(h,safe_float(e.get("hourly_rate",0)),e.get("employment_type",""))
                        st.write({"gross":g,"tax":t,"net":n})

    elif action=="Weekly":
        eid=st.text_input("Employee")
        s=st.text_input("Start")
        e=st.text_input("End")

        total=0
        for a in att:
            if a["employee_id"]==eid:
                if str(s)<=str(a["date"])<=str(e):
                    for empx in emp:
                        if empx["employee_id"]==eid:
                            h=safe_float(a["actual_hours"])
                            _,_,_,_,n=calc(h,safe_float(empx.get("hourly_rate",0)),empx.get("employment_type",""))
                            total+=n
        st.success(total)

    elif action=="Total":
        eid=st.text_input("Employee")

        total=0
        for a in att:
            if a["employee_id"]==eid:
                for e in emp:
                    if e["employee_id"]==eid:
                        h=safe_float(a["actual_hours"])
                        _,_,_,_,n=calc(h,safe_float(e.get("hourly_rate",0)),e.get("employment_type",""))
                        total+=n
        st.success(total)
