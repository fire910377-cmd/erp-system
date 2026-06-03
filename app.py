import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# =========================
# VALIDATION
# =========================
def valid_emp_id(e):
    return isinstance(e,str) and e.startswith("E") and len(e)==4 and e[1:].isdigit()

def valid_shift_id(s):
    return isinstance(s,str) and s.startswith("SH")

def valid_att_id(a):
    return isinstance(a,str) and a.startswith("A")

def safe_float(x):
    try:
        return float(x)
    except:
        return 0

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

# =========================
# UI
# =========================
st.title("🏢 ERP SYSTEM")

menu = st.sidebar.selectbox("Menu",
["Employee","Shift","Attendance","Payroll"])

# =========================
# EMPLOYEE
# =========================
if menu=="Employee":
    st.header("Employee System")

    action=st.selectbox("Action",
    ["Add","View","Search","Edit","Profile"])

    data=db["emp"].get_all_records()

    if action=="Add":
        name=st.text_input("Name")
        role=st.text_input("Role")
        dept=st.text_input("Department")
        rate=st.number_input("Hourly Rate",0.0)
        t=st.selectbox("Type",["Full-Time","Part-Time"])
        phone=st.text_input("Phone")
        email=st.text_input("Email")

        if st.button("Add"):
            new=f"E{len(data)+1:03d}"
            db["emp"].append_row([new,name,role,dept,rate,t,phone,email])
            st.success("Added")

    elif action=="View":
        st.dataframe(data)

    elif action=="Search":
        k=st.text_input("Keyword")
        res=[e for e in data if k.lower() in str(e).lower()]
        st.dataframe(res)

    elif action=="Edit":
        eid=st.text_input("Employee ID")

        if eid and not valid_emp_id(eid):
            st.error("Use E001")
            st.stop()

        emp=next((e for e in data if e["employee_id"]==eid),None)

        if emp:
            name=st.text_input("Name",emp["name"])
            role=st.text_input("Role",emp["role"])
            dept=st.text_input("Department",emp["department"])
            rate=st.number_input("Rate",value=safe_float(emp["hourly_rate"]))
            t=st.selectbox("Type",["Full-Time","Part-Time"])
            phone=st.text_input("Phone",emp["phone"])
            email=st.text_input("Email",emp["email"])

            if st.button("Save"):
                row=data.index(emp)+2
                db["emp"].update(f"B{row}:H{row}",
                [[name,role,dept,rate,t,phone,email]])
                st.success("Updated")

    # ✅🔥 只改這裡（Profile UI）
    elif action=="Profile":
        eid=st.text_input("Employee ID")
        emp=next((e for e in data if e["employee_id"]==eid),None)

        if emp:
            st.subheader("👤 Employee Profile")

            st.write(f"🆔 ID: {emp['employee_id']}")
            st.write(f"👤 Name: {emp['name']}")
            st.write(f"💼 Role: {emp['role']}")
            st.write(f"🏢 Department: {emp['department']}")
            st.write(f"💰 Hourly Rate: {emp['hourly_rate']}")
            st.write(f"📊 Type: {emp['employment_type']}")
            st.write(f"📞 Phone: {emp['phone']}")
            st.write(f"📧 Email: {emp['email']}")

# =========================
# SHIFT（完全不動）
# =========================
elif menu=="Shift":
    st.header("Shift System")

    action=st.selectbox("Action",
    ["Add","By Date","By Employee","Future","Cancel"])

    data=db["shift"].get_all_records()

    if action=="Add":
        eid=st.text_input("Employee")
        date=st.text_input("Date")
        start_time=st.text_input("Start Time")
        end_time=st.text_input("End Time")
        location=st.text_input("Location")

        if eid and not valid_emp_id(eid):
            st.error("Use E001")
            st.stop()

        if st.button("Add"):
            new=f"SH{len(data)+1:03d}"

            db["shift"].append_row([
                new,eid,date,
                start_time,end_time,
                location,"Scheduled"
            ])
            st.success("Added")

    elif action=="By Date":
        d=st.text_input("Date")
        st.dataframe([s for s in data if str(s["date"]).strip()==d])

    elif action=="By Employee":
        eid=st.text_input("Employee")
        st.dataframe([s for s in data if s["employee_id"]==eid])

    elif action=="Future":
        st.dataframe([s for s in data if s["status"]=="Scheduled"])

    elif action=="Cancel":
        sid=st.text_input("Shift ID")
        for i,s in enumerate(data):
            if s["shift_id"]==sid:
                db["shift"].update(f"G{i+2}", [["Cancelled"]])
                st.success("Cancelled")

# =========================
# ATTENDANCE（完全不動）
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
        h=st.number_input("Hours",0.0)

        if st.button("Submit"):
            new=f"A{len(data)+1:03d}"

            db["att"].append_row([
                new,sid,eid,date,h,
                "Present" if h>0 else "Absent",""
            ])
            st.success("Done")

    elif action=="By Employee":
        eid=st.text_input("Employee")
        st.dataframe([a for a in data if a["employee_id"]==eid])

    elif action=="By Date":
        d=st.text_input("Date")
        st.dataframe([a for a in data if str(a["date"]).strip()==d])

    elif action=="No Show":
        st.dataframe([a for a in data if a["status"]=="Absent"])

    elif action=="Edit Notes":
        aid=st.text_input("Attendance ID")
        note=st.text_input("Note")

        for i,a in enumerate(data):
            if a["attendance_id"]==aid:
                if st.button("Save"):
                    db["att"].update(f"G{i+2}", [[note]])
                    st.success("Updated")

    elif action=="All":
        st.dataframe(data)

# =========================
# PAYROLL（完全不動）
# =========================
elif menu=="Payroll":
    st.header("Payroll System")

    action=st.selectbox("Action",
    ["Daily","Weekly","Ranking","Stats","Total"])

    emp=db["emp"].get_all_records()
    att=db["att"].get_all_records()

    def get_emp(eid):
        return next((e for e in emp if e["employee_id"]==eid),None)

    if action=="Daily":
        eid=st.text_input("Employee")
        d=st.text_input("Date")

        rec=[a for a in att if a["employee_id"]==eid and str(a["date"]).strip()==d]

        if rec:
            e=get_emp(eid)
            if not e:
                st.error("❌ Employee not found")
                st.stop()

            h=sum(safe_float(a["actual_hours"]) for a in rec)

            _,_,_,_,n=calc(
                h,
                safe_float(e.get("hourly_rate",0)),
                e.get("employment_type","Part-Time")
            )

            st.success(f"{n}")

    elif action=="Weekly":
        eid=st.text_input("Employee")
        s=st.text_input("Start")
        e=st.text_input("End")

        if not (s.isdigit() and e.isdigit()):
            st.error("YYYYMMDD")
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
                st.error("❌ Employee not found")
                st.stop()

            h=sum(safe_float(a["actual_hours"]) for a in rec)

            _,_,_,_,n=calc(
                h,
                safe_float(emp_data.get("hourly_rate",0)),
                emp_data.get("employment_type","Part-Time")
            )

            st.success(f"{n}")
        else:
            st.warning("No data")

    elif action=="Ranking":
        result=[]
        for e in emp:
            h=sum(safe_float(a["actual_hours"]) for a in att if a["employee_id"]==e["employee_id"])
            _,_,_,_,n=calc(h,safe_float(e.get("hourly_rate",0)),e.get("employment_type","Part-Time"))
            result.append((e["name"],n))

        st.dataframe(sorted(result,key=lambda x:x[1],reverse=True))

    elif action=="Stats":
        st.write("Total records:",len(att))

    elif action=="Total":
        eid=st.text_input("Employee")
        e=get_emp(eid)

        if not e:
            st.error("❌ Employee not found")
            st.stop()

        h=sum(safe_float(a["actual_hours"]) for a in att if a["employee_id"]==eid)

        _,_,_,_,n=calc(
            h,
            safe_float(e.get("hourly_rate",0)),
            e.get("employment_type","Part-Time")
        )

        st.success(n)
