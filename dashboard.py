import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# ==========================================
# 1. تنظیمات صفحه و استایل (CSS مخصوص موبایل)
# ==========================================
st.set_page_config(page_title="داشبورد پروژه", page_icon="📱", layout="wide", initial_sidebar_state="auto")

st.markdown("""
<style>
    /* تنظیمات کلی هدر */
    .main-header {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); /* گرادینت تیره‌تر و شیک */
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* استایل کارت‌های آماری (KPI) */
    .metric-box {
        background-color: white;
        border-left: 5px solid #2c5364; /* نوار رنگی سمت چپ */
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 10px;
    }
    
    /* استایل کارت‌های داده در حالت موبایل */
    .data-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-right: 5px solid #203a43; /* نشانگر رنگی */
        transition: transform 0.2s;
    }
    .data-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .card-header {
        font-weight: bold;
        font-size: 1.1rem;
        color: #203a43;
        margin-bottom: 8px;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }
    .card-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 5px;
        font-size: 0.9rem;
    }
    .card-label {
        color: #666;
        font-weight: 500;
    }
    .card-value {
        color: #333;
        font-weight: bold;
        text-align: left;
    }
    
    /* استایل فورس ماژور */
    .critical-badge {
        background-color: #ffebee;
        color: #c62828;
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: bold;
        display: inline-block;
        margin-top: 5px;
        border: 1px solid #ffcdd2;
    }

    /* مدیا کوئری برای موبایل (صفحات کوچک) */
    @media (max-width: 768px) {
        .main-header h1 { font-size: 1.5rem; }
        .stButton button { width: 100%; border-radius: 8px; height: 3em; }
        .stTabs [data-baseweb="tab-list"] { flex-wrap: wrap; }
        .stDataFrame { font-size: 12px; }
        
        /* مخفی کردن المان‌های مزاحم در موبایل */
        section[data-testid="stSidebar"] {
            width: 100% !important; 
        }
    }
</style>
""", unsafe_allow_html=True)

SHEET_NAME = "ProjectData"
MAIN_SHEET_TITLE = "Main_Data"
DROPDOWN_SHEET_TITLE = "Dropdowns"

# ==========================================
# 2. توابع
# ==========================================
@st.cache_resource
def connect_to_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ خطا در اتصال: {e}")
        st.stop()

@st.cache_data(ttl=600)
def get_data_from_google():
    client = connect_to_gsheet()
    try:
        sh = client.open(SHEET_NAME)
        ws_main = sh.worksheet(MAIN_SHEET_TITLE)
        data = ws_main.get_all_values()
        if not data: return pd.DataFrame(), {}
        df = pd.DataFrame(data[1:], columns=data[0])
        
        dropdown_options = {}
        try:
            ws_drop = sh.worksheet(DROPDOWN_SHEET_TITLE)
            drop_data = ws_drop.get_all_values()
            if drop_data:
                headers = drop_data[0]
                for idx, header in enumerate(headers):
                    values = [row[idx] for row in drop_data[1:] if len(row) > idx and row[idx].strip()]
                    dropdown_options[header] = sorted(list(set(values)))
        except: pass
        return df, dropdown_options
    except Exception as e:
        st.error(f"خطا: {e}")
        return pd.DataFrame(), {}

def save_to_google(dataframe):
    client = connect_to_gsheet()
    try:
        sh = client.open(SHEET_NAME)
        ws_main = sh.worksheet(MAIN_SHEET_TITLE)
        updated_data = [dataframe.columns.values.tolist()] + dataframe.astype(str).values.tolist()
        ws_main.clear()
        ws_main.update(updated_data)
        return True
    except Exception as e:
        st.error(f"خطا در ذخیره: {e}")
        return False

# ==========================================
# 3. رابط کاربری (UI)
# ==========================================

# --- سایدبار ---
with st.sidebar:
    st.header("⚙️ تنظیمات نمایش")
    
    # دکمه مهم برای موبایل
    view_mode = st.radio("حالت نمایش:", ["📱 نمای کارتی (موبایل)", "💻 نمای جدولی (دسکتاپ)"], index=0)
    
    if st.button("🔄 بروزرسانی"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    df, dropdown_options = get_data_from_google()

    if not df.empty:
        st.subheader("🔍 فیلترها")
        filtered_df = df.copy()
        
        # فیلتر پیمانکار
        contractors = ["همه"] + sorted(list(df["پیمانکار"].unique()))
        sel_con = st.selectbox("پیمانکار:", contractors)
        if sel_con != "همه": filtered_df = filtered_df[filtered_df["پیمانکار"] == sel_con]
        
        # فیلتر وضعیت
        stages = ["همه"] + sorted(list(df["مرحله انجام مجوز"].unique()))
        sel_stage = st.selectbox("مرحله مجوز:", stages)
        if sel_stage != "همه": filtered_df = filtered_df[filtered_df["مرحله انجام مجوز"] == sel_stage]

        st.divider()
        critical_keywords = st.multiselect(
            "🚨 کلمات کلیدی فورس ماژور:",
            options=["توقف", "فسخ", "تاخیر", "مشکل", "عدم تایید", "عودت"],
            default=["توقف", "فسخ", "عدم تایید"]
        )

# --- محتوای اصلی ---
st.markdown('<div class="main-header"><h1>📱 داشبورد هوشمند قراردادها</h1></div>', unsafe_allow_html=True)

if not df.empty:
    # شناسایی موارد اضطراری
    mask = filtered_df.astype(str).apply(lambda x: x.str.contains('|'.join(critical_keywords), case=False, na=False)).any(axis=1)
    critical_items = filtered_df[mask]

    # نمایش آمار کلی (همیشه بالا نشان داده شود)
    col1, col2, col3 = st.columns(3)
    col1.markdown(f'<div class="metric-box">📂 تعداد<br><b>{len(filtered_df)}</b></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-box">⚠️ فورس<br><b style="color:#c62828">{len(critical_items)}</b></div>', unsafe_allow_html=True)
    
    total_budget = 0
    if "برآورد اولیه" in df.columns:
        clean = filtered_df["برآورد اولیه"].astype(str).str.replace(',', '').str.replace('ریال', '')
        total_budget = pd.to_numeric(clean, errors='coerce').sum()
    col3.markdown(f'<div class="metric-box">💰 میلیارد ریال<br><b>{total_budget/1e9:,.1f}</b></div>', unsafe_allow_html=True)
    
    st.write("") # فاصله

    # =========================================================
    # حالت 1: نمای کارتی (مخصوص موبایل - Mobile First)
    # =========================================================
    if view_mode == "📱 نمای کارتی (موبایل)":
        st.info("💡 در این حالت، داده‌ها به صورت کارت نمایش داده می‌شوند تا در موبایل خوانا باشند. برای ویرایش کامل، به حالت جدولی بروید.")
        
        tab_list, tab_chart = st.tabs(["📇 لیست پروژه‌ها", "📊 نمودارها"])
        
        with tab_list:
            # نمایش موارد فورس ماژور اول
            if not critical_items.empty:
                st.error(f"⚠️ {len(critical_items)} پروژه در وضعیت اضطراری هستند:")
                for i, row in critical_items.iterrows():
                    # کارت قرمز برای موارد اضطراری
                    with st.expander(f"🚨 {row.get('پیمانکار', '-')} | {row.get('شرح عملیات', '')[:20]}...", expanded=True):
                        st.markdown(f"""
                        <b>وضعیت:</b> <span style="color:red">{row.get('وضعیت اسناد', '-')}</span><br>
                        <b>توضیحات:</b> {row.get('شرح عملیات', '-')}
                        """, unsafe_allow_html=True)
            
            st.write("---")
            
            # نمایش لیست کارت‌ها (صفحه‌بندی شده برای سرعت بیشتر)
            # نمایش 20 تای اول برای جلوگیری از کندی در موبایل
            display_limit = 50
            if len(filtered_df) > display_limit:
                st.warning(f"نمایش {display_limit} مورد اول (از {len(filtered_df)}). برای دیدن موارد خاص فیلتر کنید.")
            
            for index, row in filtered_df.head(display_limit).iterrows():
                # ساخت کارت HTML
                card_html = f"""
                <div class="data-card">
                    <div class="card-header">{row.get('پیمانکار', 'نامشخص')}</div>
                    <div class="card-row"><span class="card-label">موضوع:</span> <span class="card-value">{str(row.get('شرح عملیات', '-'))[:40]}...</span></div>
                    <div class="card-row"><span class="card-label">وضعیت اسناد:</span> <span class="card-value">{row.get('وضعیت اسناد', '-')}</span></div>
                    <div class="card-row"><span class="card-label">مرحله مجوز:</span> <span class="card-value">{row.get('مرحله انجام مجوز', '-')}</span></div>
                    <div class="card-row"><span class="card-label">مبلغ:</span> <span class="card-value">{row.get('برآورد اولیه', '0')}</span></div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)

        with tab_chart:
            # نمودار ساده شده برای موبایل
            chart_data = filtered_df["مرحله انجام مجوز"].value_counts().reset_index()
            chart_data.columns = ["مرحله", "تعداد"]
            fig = px.pie(chart_data, values="تعداد", names="مرحله", hole=0.5)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

    # =========================================================
    # حالت 2: نمای جدولی (دسکتاپ - Desktop Mode)
    # =========================================================
    else:
        tab1, tab2 = st.tabs(["📊 داشبورد تحلیلی", "✏️ ویرایش جدولی"])
        
        with tab1:
            st.markdown("### 📈 نمودار ساز پیشرفته")
            with st.expander("تنظیمات نمودار", expanded=True):
                c_1, c_2, c_3 = st.columns(3)
                chart_type = c_1.selectbox("نوع نمودار", ["میله‌ای", "دایره‌ای", "دونات"])
                cols = list(df.columns)
                x_ax = c_2.selectbox("محور X", [c for c in cols if df[c].dtype=='object'], index=2 if len(cols)>2 else 0)
                y_ax = c_3.selectbox("محور Y", ["تعداد"] + [c for c in cols if "مبلغ" in c or "برآورد" in c])
            
            # رسم نمودار
            if y_ax == "تعداد":
                p_df = filtered_df[x_ax].value_counts().reset_index()
                p_df.columns = [x_ax, "تعداد"]
                y_val = "تعداد"
            else:
                filtered_df[y_ax] = pd.to_numeric(filtered_df[y_ax].astype(str).str.replace(',', '').str.replace('ریال', ''), errors='coerce')
                p_df = filtered_df.groupby(x_ax)[y_ax].sum().reset_index()
                y_val = y_ax
                
            if "میله" in chart_type:
                fig = px.bar(p_df, x=x_ax, y=y_val, color=x_ax, text_auto=True)
            else:
                hole = 0.4 if "دونات" in chart_type else 0
                fig = px.pie(p_df, values=y_val, names=x_ax, hole=hole)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.warning("⚠️ برای حذف ردیف: روی شماره ردیف کلیک کنید و Delete بزنید. سپس ذخیره کنید.")
            
            column_config = {}
            for col_name, options in dropdown_options.items():
                if col_name in df.columns:
                    column_config[col_name] = st.column_config.SelectboxColumn(col_name, options=options, required=False)
            
            edited_df = st.data_editor(df, column_config=column_config, num_rows="dynamic", use_container_width=True, key="editor_desktop")
            
            if st.button("💾 ذخیره تغییرات در گوگل شیت", type="primary"):
                with st.spinner("در حال ذخیره..."):
                    if save_to_google(edited_df):
                        st.success("انجام شد!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()