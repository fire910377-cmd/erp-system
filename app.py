import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

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
    sheet = client.open_by_key("你的sheet id")

    return {
        "emp": sheet.worksheet("Employees"),
        "shift": sheet.worksheet("Shifts"),
        "att": sheet.worksheet("Attendance")
    }

db = connect()

# =========================
# PAY
# =========================
def calc(hours, rate, t):
    if t == "Full-Time":
        reg = min(hours, 8) * rate
        ot = max(0, hours-8)*rate*1.5
    else:
        reg = hours*rate
        ot = 0
    gross = reg+ot
    tax = gross*0.1
    return reg,ot,gross,tax,gross-tax

# =========================
# UI
# =========================
st.title("🏢 ERP SYSTEM")

menu = st.sidebar.selectbox("Menu",
["Employee","Shift","Attendance","Payroll"])

# =========================
# EMPLOYEE
# =========================
if menu == "Employee":
    st.header("Employee System")

    action = st.selectbox("Action",
    ["Add","View","Search","Edit","Profile"])

    data = db["emp"].get_all_records()

    # ADD
    if action=="Add":
        name=st.text_input("Name")
        role=st.text_input("Role")
        dept=st.text_input("Dept")
        rate=st.number_input("Rate",0.0)
        t=st.selectbox("Type",["Full-Time","Part-Time"])
        phone=st.text_input("Phone")
        email=st.text_input("Email")

        if st.button("Add"):
            new=f"E{len(data)+1:03d}"
            db["emp"].append_row([new,name,role,dept,rate,t,phone,email])
            st.success("Added")

    # VIEW
    elif action=="View":
        sort=st.selectbox("Sort by",["name","department"])
        st.dataframe(sorted(data,key=lambda x:x[sort]))

    # SEARCH
    elif action=="Search":
        key=st.text_input("Keyword")
        res=[e for e in data if key.lower() in str(e).lower()]
        st.dataframe(res)

    # EDIT
    elif action=="Edit":
        eid=st.text_input("Employee ID")
        emp=next((e for e in data if e["employee_id"]==eid),None)

        if emp:
            name=st.text_input("Name",emp["name"])
            role=st.text_input("Role",emp["role"])
            dept=st.text_input("Dept",emp["department"])
            rate=st.number_input("Rate",value=float(emp["hourly_rate"]))
            t=st.selectbox("Type",["Full-Time","Part-Time"])
            phone=st.text_input("Phone",emp["phone"])
            email=st.text_input("Email",emp["email"])

            if st.button("Save"):
                row=data.index(emp)+2
                db["emp"].update(f"B{row}:H{row}",
                [[name,role,dept,rate,t,phone,email]])
                st.success("Updated")

    # PROFILE
    elif action=="Profile":
        eid=st.text_input("Employee ID")
        emp=next((e for e in data if e["employee_id"]==eid),None)

        if emp:
            st.markdown(f"""
            ### 👤 {emp['name']}
            **Role:** {emp['role']}  
            **Dept:** {emp['department']}  
            **Rate:** ${emp['hourly_rate']}  
            **Phone:** {emp['phone']}  
            **Email:** {emp['email']}
            """)

# =========================
# SHIFT
# =========================
elif menu=="Shift":
    st.header("Shift System")

    action=st.selectbox("Action",
    ["Add","By Date","By Employee","Future","Cancel"])

    data=db["shift"].get_all_records()

    if action=="Add":
        eid=st.text_input("Employee")
        date=st.text_input("Date")
        start=st.text_input("Start")
        end=st.text_input("End")

        conflict=[s for s in data if s["employee_id"]==eid and s["date"]==date]

        if conflict:
            st.error("⚠️ Conflict shift!")

        if st.button("Add"):
            new=f"SH{len(data)+1:03d}"
            db["shift"].append_row([new,eid,date,start,end,"","Scheduled"])
            st.success("Added")

    elif action=="By Date":
        d=st.text_input("Date")
        st.dataframe([s for s in data if s["date"]==d])

    elif action=="By Employee":
        eid=st.text_input("Employee")
        st.dataframe([s for s in data if s["employee_id"]==eid])

    elif action=="Future":
        st.dataframe([s for s in data if s["status"]=="Scheduled"])

    elif action=="Cancel":
        sid=st.text_input("Shift ID")
        for i,s in enumerate(data):
            if s["shift_id"]==sid:
                db["shift"].update(f"G{i+2}", "Cancelled")
                st.success("Cancelled")

# =========================
# ATTENDANCE
# =========================
elif menu=="Attendance":
    st.header("Attendance System")

    action=st.selectbox("Action",
    ["Check In","By Employee","By Date","No Show","Edit Notes","All"])

    data=db["att"].get_all_records()

    if action=="Check In":
        eid=st.text_input("Employee")
        sid=st.text_input("Shift ID")
        date=st.text_input("Date")
        hours=st.number_input("Hours",0.0)

        status="Present" if hours>0 else "Absent"

        if st.button("Submit"):
            new=f"A{len(data)+1:03d}"
            db["att"].append_row(
            [new,sid,eid,date,hours,status,""])
            st.success("Done")

    elif action=="By Employee":
        eid=st.text_input("Employee")
        st.dataframe([a for a in data if a["employee_id"]==eid])

    elif action=="By Date":
        d=st.text_input("Date")
        st.dataframe([a for a in data if a["date"]==d])

    elif action=="No Show":
        st.dataframe([a for a in data if a["status"]=="Absent"])

    elif action=="Edit Notes":
        aid=st.text_input("Attendance ID")
        note=st.text_input("New Note")

        for i,a in enumerate(data):
            if a["attendance_id"]==aid:
                if st.button("Update"):
                    db["att"].update(f"G{i+2}", note)
                    st.success("Updated")

    elif action=="All":
        st.dataframe(data)

# =========================
# PAYROLL
# =========================
elif menu=="Payroll":
    st.header("Payroll System")

    action=st.selectbox("Action",
    ["Daily","Weekly","Ranking","Stats","Total"])

    emp=db["emp"].get_all_records()
    att=db["att"].get_all_records()

    def get_emp(eid):
        return next((e for e in emp if e["employee_id"]==eid),None)

    # DAILY
    if action=="Daily":
        eid=st.text_input("Employee")
        d=st.text_input("Date")

        rec=[a for a in att if a["employee_id"]==eid and a["date"]==d]

        if rec:
            e=get_emp(eid)
            h=sum(float(a["actual_hours"]) for a in rec)
            r,o,g,t,n=calc(h,float(e["hourly_rate"]),e["employment_type"])

            st.success(f"💰 ${n}")
            st.write(r,o,g,t)

    # WEEKLY
    elif action=="Weekly":
        eid=st.text_input("Employee")
        s=st.text_input("Start")
        e=st.text_input("End")

        rec=[a for a in att if a["employee_id"]==eid and s<=a["date"]<=e]

        if rec:
            emp_data=get_emp(eid)
            h=sum(float(a["actual_hours"]) for a in rec)
            _,_,_,_,n=calc(h,float(emp_data["hourly_rate"]),emp_data["employment_type"])
            st.success(n)

    # RANKING
    elif action=="Ranking":
        result=[]
        for e in emp:
            h=sum(float(a["actual_hours"]) for a in att if a["employee_id"]==e["employee_id"])
            _,_,_,_,n=calc(h,float(e["hourly_rate"]),e["employment_type"])
            result.append((e["name"],n))

        st.dataframe(sorted(result,key=lambda x:x[1],reverse=True))

    # STATS
    elif action=="Stats":
        st.write("Total attendance:",len(att))

    # TOTAL
    elif action=="Total":
        eid=st.text_input("Employee")
        e=get_emp(eid)

        h=sum(float(a["actual_hours"]) for a in att if a["employee_id"]==eid)
        _,_,_,_,n=calc(h,float(e["hourly_rate"]),e["employment_type"])
        st.success(n)
