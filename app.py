import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# =========================
# Google Sheets 連線（雲端版）
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
# Helper
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
st.title("🏢 ERP FULL SYSTEM")

menu = st.sidebar.selectbox(
    "Menu",
    ["Employee Management", "Shift Management", "Attendance", "Payroll"]
)

# =========================
# 員工管理
# =========================
if menu == "Employee Management":
    st.header("👥 Employee Management")

    action = st.selectbox("Action", ["Add Employee", "View Employees"])

    if action == "Add Employee":
        name = st.text_input("Name")
        role = st.text_input("Role")
        dept = st.text_input("Department")
        rate = st.number_input("Hourly Rate", min_value=0.0)
        emp_type = st.selectbox("Type", ["Full-Time", "Part-Time"])
        phone = st.text_input("Phone")
        email = st.text_input("Email")

        if st.button("Add Employee"):
            data = tabs["employees"].get_all_records()
            new_id = f"E{len(data)+1:03d}"

            tabs["employees"].append_row([
                new_id, name, role, dept, rate, emp_type, phone, email
            ])

            st.success(f"Employee {new_id} added!")

    elif action == "View Employees":
        data = tabs["employees"].get_all_records()
        st.dataframe(data)

# =========================
# 排班管理
# =========================
elif menu == "Shift Management":
    st.header("📅 Shift Management")

    action = st.selectbox("Action", ["Add Shift", "View Shifts"])

    if action == "Add Shift":
        emp_id = st.text_input("Employee ID")
        date = st.text_input("Date (YYYYMMDD)")
        start = st.text_input("Start Time")
        end = st.text_input("End Time")
        location = st.text_input("Location")

        if st.button("Add Shift"):
            data = tabs["shifts"].get_all_records()
            new_id = f"SH{len(data)+1:03d}"

            tabs["shifts"].append_row([
                new_id, emp_id, date, start, end, location, "Scheduled"
            ])

            st.success(f"Shift {new_id} created!")

    elif action == "View Shifts":
        data = tabs["shifts"].get_all_records()
        st.dataframe(data)

# =========================
# 出勤管理
# =========================
elif menu == "Attendance":
    st.header("🕒 Attendance")

    action = st.selectbox("Action", ["Check In", "View Attendance"])

    if action == "Check In":
        emp_id = st.text_input("Employee ID")
        shift_id = st.text_input("Shift ID")
        date = st.text_input("Date (YYYYMMDD)")
        hours = st.number_input("Work Hours", min_value=0.0)
        status = st.selectbox("Status", ["Present", "Absent"])
        notes = st.text_input("Notes")

        if st.button("Submit Attendance"):
            data = tabs["attendance"].get_all_records()
            new_id = f"A{len(data)+1:03d}"

            tabs["attendance"].append_row([
                new_id, shift_id, emp_id, date, hours, status, notes
            ])

            st.success(f"Attendance {new_id} recorded!")

    elif action == "View Attendance":
        data = tabs["attendance"].get_all_records()
        st.dataframe(data)

# =========================
# 薪資系統
# =========================
elif menu == "Payroll":
    st.header("💰 Payroll System")

    emp_id = st.text_input("Employee ID")
    start_date = st.text_input("Start Date (YYYYMMDD)")

    if st.button("Calculate Weekly Pay"):
        attendance = tabs["attendance"].get_all_records()
        employees = tabs["employees"].get_all_records()

        emp = next((e for e in employees if e["employee_id"] == emp_id), None)

        if not emp:
            st.error("Employee not found")
        else:
            rate = float(emp["hourly_rate"])
            emp_type = emp["employment_type"]

            total_hours = 0

            for a in attendance:
                if (
                    a["employee_id"] == emp_id and
                    int(start_date) <= int(a["date"]) <= int(start_date) + 6
                ):
                    total_hours += float(a["actual_hours"])

            reg, ot, gross, tax, net = calculate_pay(total_hours, rate, emp_type)

            st.success(f"Weekly Pay: {net}")
            st.write(f"Regular: {reg}")
            st.write(f"Overtime: {ot}")
            st.write(f"Gross: {gross}")
            st.write(f"Tax: {tax}")
