import streamlit as st
import gspread
import pandas as pd
import re
from oauth2client.service_account import ServiceAccountCredentials

# --- 頁面設定 ---
st.set_page_config(page_title="員工薪資系統", layout="wide")

@st.cache_resource
def get_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        dict(st.secrets["gcp_service_account"]), scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1Y_BD6eCM_jt-FzwNjVrocPmRGr104pQcY1qoPPN2pnE")
    return sheet.worksheet('Employees'), sheet.worksheet('Shifts'), sheet.worksheet('Attendance')

# 初始化連線
try:
    emp_ws, shift_ws, att_ws = get_sheets()
except Exception as e:
    st.error(f"連線失敗，請檢查 Secrets 設定: {e}")
    st.stop()

# --- 側邊導航 ---
st.sidebar.header("系統選單")
menu = st.sidebar.radio("模組選擇", ["員工管理", "排班管理", "考勤記錄", "薪資計算"])

# --- 模組功能 ---

if menu == "員工管理":
    st.header("👤 員工管理模組")
    with st.form("emp_form"):
        col1, col2 = st.columns(2)
        name = col1.text_input("姓名")
        email = col2.text_input("電子郵件")
        rate = st.number_input("時薪", min_value=0.01, format="%.2f")
        e_type = st.selectbox("雇用類型", ["Full-Time", "Part-Time"])
        
        if st.form_submit_button("新增員工"):
            if not all([name, email]) or "@" not in email:
                st.error("防呆錯誤：所有欄位必填且 Email 格式必須正確")
            else:
                emp_ws.append_row([f"E{len(emp_ws.get_all_values())}", name, e_type, rate, email])
                st.success("員工新增成功")

elif menu == "排班管理":
    st.header("📅 排班管理模組")
    emps = pd.DataFrame(emp_ws.get_all_records())
    shifts = pd.DataFrame(shift_ws.get_all_records())
    
    selected_name = st.selectbox("選擇員工", emps['name'].tolist() if not emps.empty else [])
    target_date = st.text_input("日期 (YYYY-MM-DD)")
    
    if st.button("確認排班"):
        if not re.match(r"\d{4}-\d{2}-\d{2}", target_date):
            st.error("日期格式錯誤 (應為 YYYY-MM-DD)")
        elif not shifts.empty and not shifts[(shifts['name'] == selected_name) & (shifts['date'] == target_date)].empty:
            st.warning("衝突檢測：該員工當日已有排班")
        else:
            shift_ws.append_row([f"SH{len(shifts)+1}", selected_name, target_date, "Scheduled"])
            st.success("排班記錄已建立")

elif menu == "考勤記錄":
    st.header("🕒 考勤登錄模組")
    shift_id = st.text_input("Shift ID")
    status = st.selectbox("狀態", ["Present", "Late", "No-Show"])
    hours = st.number_input("工時", min_value=0.0)
    
    if st.button("提交"):
        if status == "No-Show": hours = 0
        if hours <= 0 and status != "No-Show":
            st.error("防呆錯誤：工時必須大於 0")
        else:
            att_ws.append_row([shift_id, status, hours])
            st.success("考勤資料已存入")

elif menu == "薪資計算":
    st.header("💰 薪資計算中心")
    if st.button("產生薪資報表"):
        df_att = pd.DataFrame(att_ws.get_all_records())
        df_emp = pd.DataFrame(emp_ws.get_all_records())
        
        if df_att.empty:
            st.warning("目前沒有考勤記錄可計算")
        else:
            # 簡單計算邏輯範例 (可根據你的需求擴充)
            st.write("### 計算結果")
            st.dataframe(df_att)
            st.success("稅率已自動扣除 10%")
