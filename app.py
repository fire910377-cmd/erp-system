import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pandas as pd

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="ERP System", layout="wide")

# =========================
# STYLE (🔥 UI美化)
# =========================
st.markdown("""
<style>
.main {
    background-color: #f5f7fa;
}
h1, h2, h3 {
    color: #1f3c88;
}
.stButton>button {
    background-color: #1f77b4;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONNECT
# =========================
@st.cache_resource
def connect():
    creds = Credentials.from_service_account_file(
        "payroll-key.json",
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

tabs = connect()

emp = tabs["emp"].get_all_records()
att = tabs["att"].get_all_records()

# =========================
# PAY CALC
# =========================
def calc_pay(rec, emp):
    h = float(rec.get("actual_hours", 0))
    r = float(emp.get("hourly_rate", 0))

    if emp.get("employment_type") == "Full-Time":
        reg = min(h, 8) * r
        ot = max(0, h - 8) * r * 1.5
    else:
        reg = h * r
        ot = 0

    gross = reg + ot
    tax = gross * 0.1
    net = gross - tax
    return reg, ot, gross, tax, net

# =========================
# TITLE
# =========================
st.title("🏢 Enterprise ERP System")

menu = st.sidebar.radio("Navigation", ["Employees", "Payroll Dashboard"])

# =========================
# EMPLOYEE
# =========================
if menu == "Employees":
    st.header("👥 Employee Management")

    df = pd.DataFrame(emp)
    st.dataframe(df, use_container_width=True)

# =========================
# PAYROLL DASHBOARD (🔥圖表)
# =========================
elif menu == "Payroll Dashboard":

    st.header("📊 Payroll Analytics")

    df_emp = pd.DataFrame(emp)
    df_att = pd.DataFrame(att)

    if not df_att.empty:

        merged = df_att.merge(df_emp, on="employee_id")

        merged["net"] = merged.apply(
            lambda x: calc_pay(x, x)[4], axis=1
        )

        # 🔥 圖表1：薪資排名
        st.subheader("🏆 Salary Ranking")

        rank = merged.groupby("employee_id")["net"].sum().reset_index()

        st.bar_chart(rank.set_index("employee_id"))

        # 🔥 圖表2：每日薪資趨勢
        st.subheader("📈 Daily Salary Trend")

        trend = merged.groupby("date")["net"].sum().reset_index()

        st.line_chart(trend.set_index("date"))

        # 🔥 KPI
        st.subheader("📌 KPI")

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Salary", int(merged["net"].sum()))
        col2.metric("Avg Salary", int(merged["net"].mean()))
        col3.metric("Total Records", len(merged))

    else:
        st.warning("No attendance data")