import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

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
        "employees": sheet.worksheet("Employees"),
        "shifts": sheet.worksheet("Shifts"),
        "attendance": sheet.worksheet("Attendance")
    }

tabs = connect()

# =========================
# PAY FUNCTION
# =========================
def calculate_pay(hours, rate, emp_type):
    if emp_type == "Full-Time":
        regular = min(hours, 8) * rate
        overtime = max(0, hours - 8) * rate * 1.5
    else:
        regular = hours * rate
        overtime = 0

    gross = regular + overtime
    tax = gross * 0.1
    net = gross - tax
    return regular, overtime, gross, tax, net

# =========================
# UI
# =========================
st.set_page_config(page_title="ERP System", layout="wide")
st.title("🏢 ERP FULL SYSTEM (FINAL)")

menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard","Employee","Shift","Attendance","Payroll"]
)

# =========================
# DASHBOARD（加分🔥）
# =========================
if menu == "Dashboard":
    st.header("📊 Dashboard")

    emp = pd.DataFrame(tabs["employees"].get_all_records())
    att = pd.DataFrame(tabs["attendance"].get_all_records())

    st.subheader("Employees per Department")
    if not emp.empty:
        st.bar_chart(emp["department"].value_counts())

    st.subheader("Work Hours Distribution")
    if not att.empty:
        st.bar_chart(att["actual_hours"])

# =========================
# EMPLOYEE（完整CRUD🔥）
# =========================
elif menu == "Employee":
    st.header("👥 Employee System")

    action = st.selectbox("Action", ["Add","View","Edit","Delete"])

    data = tabs["employees"].get_all_records()

    if action == "Add":
        name = st.text_input("Name")
        role = st.text_input("Role")
        dept = st.text_input("Department")
        rate = st.number_input("Hourly Rate", 0.0)
        emp_type = st.selectbox("Type", ["Full-Time","Part-Time"])
        phone = st.text_input("Phone")
        email = st.text_input("Email")

        if st.button("Add"):
            new_id = f"E{len(data)+1:03d}"
            tabs["employees"].append_row(
                [new_id,name,role,dept,rate,emp_type,phone,email]
            )
            st.success("Added")

    elif action == "View":
        st.dataframe(data)

    elif action == "Edit":
        emp_id = st.text_input("Employee ID")
        if st.button("Load"):
            emp = next((e for e in data if e["employee_id"]==emp_id),None)
            if emp:
                name = st.text_input("Name",emp["name"])
                role = st.text_input("Role",emp["role"])
                dept = st.text_input("Dept",emp["department"])
                rate = st.number_input("Rate",value=float(emp["hourly_rate"]))
                phone = st.text_input("Phone",emp["phone"])

                if st.button("Save"):
                    cell = data.index(emp)+2
                    tabs["employees"].update(f"B{cell}:F{cell}",
                        [[name,role,dept,rate,emp["employment_type"]]]
                    )
                    st.success("Updated")

    elif action == "Delete":
        emp_id = st.text_input("Employee ID")
        if st.button("Delete"):
            for i,e in enumerate(data):
                if e["employee_id"]==emp_id:
                    tabs["employees"].delete_rows(i+2)
                    st.success("Deleted")

# =========================
# SHIFT
# =========================
elif menu == "Shift":
    st.header("📅 Shift System")

    action = st.selectbox("Action", ["Add","View"])

    if action == "Add":
        emp_id = st.text_input("Employee ID")
        date = st.text_input("Date YYYYMMDD")
        start = st.text_input("Start")
        end = st.text_input("End")
        location = st.text_input("Location")

        if st.button("Add Shift"):
            data = tabs["shifts"].get_all_records()
            new_id = f"SH{len(data)+1:03d}"
            tabs["shifts"].append_row(
                [new_id,emp_id,date,start,end,location,"Scheduled"]
            )
            st.success("Added")

    else:
        st.dataframe(tabs["shifts"].get_all_records())

# =========================
# ATTENDANCE
# =========================
elif menu == "Attendance":
    st.header("🕒 Attendance")

    action = st.selectbox("Action", ["Check In","View"])

    if action == "Check In":
        emp_id = st.text_input("Employee ID")
        shift_id = st.text_input("Shift ID")
        date = st.text_input("Date")
        hours = st.number_input("Hours",0.0)
        status = st.selectbox("Status",["Present","Absent"])
        notes = st.text_input("Notes")

        if st.button("Submit"):
            data = tabs["attendance"].get_all_records()
            new_id = f"A{len(data)+1:03d}"
            tabs["attendance"].append_row(
                [new_id,shift_id,emp_id,date,hours,status,notes]
            )
            st.success("Recorded")

    else:
        st.dataframe(tabs["attendance"].get_all_records())

# =========================
# PAYROLL（滿分🔥）
# =========================
elif menu == "Payroll":
    st.header("💰 Payroll")

    emp_id = st.text_input("Employee ID")
    start = st.text_input("Start Date YYYYMMDD")
    end = st.text_input("End Date YYYYMMDD")

    if st.button("Calculate"):
        att = tabs["attendance"].get_all_records()
        emp = tabs["employees"].get_all_records()

        e = next((x for x in emp if x["employee_id"]==emp_id),None)

        if not e:
            st.error("Not found")
        else:
            rate = float(e["hourly_rate"])
            emp_type = e["employment_type"]

            total = 0
            for a in att:
                if (
                    a["employee_id"]==emp_id and
                    int(start)<=int(a["date"])<=int(end)
                ):
                    total += float(a["actual_hours"])

            reg,ot,gross,tax,net = calculate_pay(total,rate,emp_type)

            st.success(f"Net Pay: {net}")
            st.write(reg,ot,gross,tax)
