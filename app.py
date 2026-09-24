"""
app.py
Specimen Rejection Dashboard (รายงานการปฏิเสธสิ่งส่งตรวจทางห้องปฏิบัติการ)
Hospital Quality Improvement & Clinical Analytics Dashboard
Designed for Microbiology Lab & CQI/R2R Quality Teams.
Built with Streamlit & Plotly.
"""

import os
import io
import re
import base64
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import cleaner

# ==============================================================================
# 1. PAGE CONFIGURATION & MODERN CLINICAL THEME STYLING
# ==============================================================================

LOGO_PATH = os.path.join(os.path.dirname(__file__), "tuh_logo.jpg")
try:
    with open(LOGO_PATH, "rb") as _logo_file:
        LOGO_DATA_URI = "data:image/jpeg;base64," + base64.b64encode(_logo_file.read()).decode("ascii")
except OSError:
    LOGO_DATA_URI = ""

st.set_page_config(
    page_title="Specimen Rejection Dashboard",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Minimal + Professional Clinical Theme
st.markdown("""
<style>
    /* Typography & Font import */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"], .stMarkdown, .stText, h1, h2, h3, h4, h5, h6 {
        font-family: 'Noto Sans Thai', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    
    /* Background */
    .stApp {
        background-color: #FFFDF8;
    }
    
    /* Sidebar styling: width ~290px */
    [data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 300px !important;
        background-color: #FFFFFF !important;
        border-right: 1px solid #F1E5C8 !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Compact Header */
    .compact-header {
        background: #FFFFFF;
        border: 1px solid #F1E5C8;
        border-radius: 12px;
        padding: 0.9rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .compact-header-title {
        color: #5B146F;
        font-size: 1.45rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.2;
    }
    
    .compact-header-sub {
        color: #6B5A70;
        font-size: 0.85rem;
        margin: 0.2rem 0 0 0;
        font-weight: 400;
    }
    
    .header-badge {
        background-color: #FFF8D6;
        color: #6c5070;
        border: 1px solid #F5D85E;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    
    /* Responsive KPI Cards Container */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 12px;
        margin-bottom: 1.1rem;
    }
    
    @media (max-width: 1300px) {
        .kpi-container {
            grid-template-columns: repeat(3, 1fr);
        }
    }
    
    @media (max-width: 768px) {
        .kpi-container {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    
    @media (max-width: 480px) {
        .kpi-container {
            grid-template-columns: 1fr;
        }
    }
    
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #F1E5C8;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        min-width: 0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 104px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.07);
    }
    
    .kpi-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.3rem;
    }
    
    .kpi-label {
        color: #6B5A70;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    
    .kpi-icon {
        font-size: 1.15rem;
        opacity: 0.9;
    }
    
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 700;
        line-height: 1.15;
        margin-bottom: 0.2rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .kpi-sub {
        color: #94A3B8;
        font-size: 0.74rem;
        font-weight: 400;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    /* Quick Filter Summary Bar */
    .quick-filter-bar {
        background: #FFFFFF;
        border: 1px solid #F1E5C8;
        border-radius: 10px;
        padding: 0.55rem 1rem;
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.82rem;
        color: #475569;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
    }
    
    .qf-tag {
        background: #F1F5F9;
        padding: 2px 8px;
        border-radius: 6px;
        font-weight: 600;
        color: #1E293B;
    }
    
    /* Modern Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: transparent;
        border-bottom: 1px solid #F1E5C8;
        padding-bottom: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        color: #6B5A70 !important;
        padding: 8px 14px !important;
        border-radius: 8px 8px 0 0 !important;
        background: transparent !important;
        border: none !important;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #6c5070 !important;
        font-weight: 600 !important;
        background-color: #F7EAFB !important;
        border-bottom: 2px solid #6c5070 !important;
    }
    
    /* Popover button custom styling in sidebar */
    [data-testid="stPopover"] > button {
        background-color: #FFFFFF !important;
        border: 1px solid #F1E5C8 !important;
        color: #4B3153 !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        padding: 0.45rem 0.75rem !important;
        text-align: left !important;
        justify-content: flex-start !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02) !important;
        transition: all 0.15s ease !important;
    }
    
    [data-testid="stPopover"] > button:hover {
        border-color: #E6C94A !important;
        background-color: #FFFDF2 !important;
    }
    
    /* Card containers inside dashboard */
    .chart-card {
        background: #FFFFFF;
        border: 1px solid #F1E5C8;
        border-radius: 12px;
        padding: 1.1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
        margin-bottom: 1rem;
    }
    
    .chart-title {
        font-size: 0.96rem;
        font-weight: 600;
        color: #5B146F;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }
</style>
<style>
    /* K-Minimal pastel theme */
    :root {
        --k-purple: #6c5070;
        --k-coral: #df6a6a;
        --k-sage: #c2dbc1;
        --k-cream: #fbfaf8;
        --k-ink: #4e3f50;
        --k-muted: #867986;
        --k-border: #eadfe9;
    }

    .stApp {
        background: var(--k-cream) !important;
    }

    [data-testid="stSidebar"] {
        background: #fffdfb !important;
        border-right: 1px solid var(--k-border) !important;
    }

    .compact-header {
        border: 1px solid var(--k-border);
        border-top: 4px solid var(--k-coral);
        border-radius: 18px;
        background: #fff;
        box-shadow: 0 5px 18px rgba(108, 80, 112, 0.07);
    }

    .compact-header-title,
    .chart-title {
        color: var(--k-purple) !important;
    }

    .compact-header-sub,
    .kpi-label {
        color: var(--k-muted) !important;
    }

    .header-badge {
        background: var(--k-sage) !important;
        color: var(--k-purple) !important;
        border: 1px solid #a9c7a8 !important;
        border-radius: 999px !important;
    }

    .quick-filter-bar,
    .chart-card,
    .kpi-card {
        border-color: var(--k-border) !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 14px rgba(108, 80, 112, 0.055) !important;
    }

    .quick-filter-bar {
        background: #fff !important;
        color: var(--k-ink) !important;
    }

    .qf-tag {
        background: #f7eef6 !important;
        color: var(--k-purple) !important;
    }

    .kpi-card {
        background: #fff !important;
        border-top: 3px solid var(--k-sage) !important;
    }

    .kpi-card:nth-child(2) {
        border-top-color: var(--k-coral) !important;
    }

    .kpi-card:nth-child(3) {
        border-top-color: var(--k-purple) !important;
    }

    .kpi-card:nth-child(4) {
        border-top-color: var(--k-sage) !important;
    }

    .kpi-card:nth-child(5) {
        border-top-color: var(--k-coral) !important;
    }

    .kpi-card:nth-child(1) .kpi-value {
        color: var(--k-purple) !important;
    }

    .kpi-card:nth-child(2) .kpi-value,
    .kpi-card:nth-child(5) .kpi-value {
        color: var(--k-coral) !important;
    }

    .kpi-card:nth-child(3) .kpi-value {
        color: var(--k-purple) !important;
    }

    [data-testid="stPopover"] > button {
        background: #fff !important;
        border-color: var(--k-border) !important;
        color: var(--k-purple) !important;
        border-radius: 12px !important;
    }

    [data-testid="stPopover"] > button:hover {
        background: #fff6f6 !important;
        border-color: var(--k-coral) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        border-bottom-color: var(--k-border) !important;
    }

    .stTabs [data-baseweb="tab"] {
        color: var(--k-muted) !important;
        border-radius: 12px 12px 0 0 !important;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: var(--k-purple) !important;
        background: #f7eef6 !important;
        border-bottom-color: var(--k-coral) !important;
    }

    div[data-testid="stMetric"] {
        background: #fff;
        border: 1px solid var(--k-border);
        border-radius: 14px;
        padding: 0.65rem 0.8rem;
    }

    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 260px !important;
            max-width: 86vw !important;
        }

        .compact-header {
            padding: 0.8rem 0.9rem;
            align-items: flex-start;
        }

        .compact-header-title {
            font-size: 1.15rem !important;
        }

        .compact-header-sub {
            font-size: 0.74rem !important;
        }

        .quick-filter-bar {
            overflow-x: auto;
            white-space: nowrap;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 7px 8px !important;
            font-size: 0.76rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. DATA LOADING & CACHING
# ==============================================================================

DEFAULT_EXCEL_PATHS = [
    os.path.join(os.path.dirname(__file__), "แบบบันทึกการปฏิเสธสิ่งส่งตรวจ_public.xlsx"),
    r"c:\Users\kanokwan\Downloads\tuh-crab-research\แบบบันทึกการปฏิเสธสิ่งส่งตรวจ.xlsx",
    r"C:\Users\kanokwan\Downloads\แบบบันทึกการปฏิเสธสิ่งส่งตรวจ.xlsx",
    r"C:\Users\kanokwan\Downloads\สำเนาของ แบบบันทึกการปฏิเสธสิ่งส่งตรวจ (Google Sheets) - สรุป.csv",
]
GOOGLE_SHEET_ID = "1J16UXkoO5jW6X5jfiQ2lYTna3V2aJGZm"
GOOGLE_SHEET_XLSX_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx"
DEFAULT_MONTHLY_QUALITY_TARGET = 30

@st.cache_data(show_spinner="กำลังซิงก์และประมวลผลข้อมูล...", ttl=900)
def load_data(file_source, cache_version="monthly-tabs-20260924"):
    source_for_cleaner = file_source
    if isinstance(file_source, str) and file_source.startswith(('http://', 'https://')):
        response = requests.get(file_source, timeout=45)
        response.raise_for_status()
        source_for_cleaner = io.BytesIO(response.content)
        source_for_cleaner.name = "google_sheet_export.xlsx"

    df_cases, df_causes = cleaner.load_and_consolidate(source_for_cleaner)
    duplicate_columns = [
        c for c in ['date', 'time', 'hn', 'ward_raw', 'specimen_issue', 'request_issue', 'payment_issue', 'it_issue', 'other_issue']
        if c in df_cases.columns
    ]
    if duplicate_columns and 'hn' in df_cases.columns:
        hn = df_cases['hn'].astype(str).str.strip()
        has_hn = ~hn.isin(['', 'nan', 'None', 'HN-ปิดบัง'])
        df_cases['possible_duplicate'] = has_hn & df_cases.duplicated(subset=duplicate_columns, keep=False)
    else:
        df_cases['possible_duplicate'] = False

    # Backward-compatible fallback for cached/older cleaned data that predates
    # the fiscal_year column. Derive it from the normalized ISO date.
    def ensure_fiscal_year(df):
        if 'fiscal_year' in df.columns or 'date' not in df.columns:
            return df
        result = df.copy()
        parsed_dates = pd.to_datetime(result['date'], errors='coerce')
        labels = []
        for dt in parsed_dates:
            if pd.isna(dt):
                labels.append('ปีงบประมาณ -')
            else:
                fy = int(dt.year + (1 if dt.month >= 10 else 0) + 543)
                labels.append(f'ปีงบประมาณ {fy}')
        result['fiscal_year'] = labels
        return result

    def mask_public_identifiers(df):
        public_columns = {
            'case_id', 'date', 'date_valid', 'day', 'time', 'year_month',
            'thai_month_year', 'fiscal_quarter', 'fiscal_year', 'source_sheet',
            'hn', 'ward_raw', 'ward_standard', 'ward_group', 'specimen_issue',
            'request_issue', 'payment_issue', 'it_issue', 'other_issue',
            'receiver', 'status', 'evidence', 'reporter', 'followup',
            'resolution', 'follower', 'supervisor', 'is_incident',
            'specimen_type', 'risk_level', 'category', 'reason', 'notes',
            'possible_duplicate',
        }
        result = df[[col for col in df.columns if col in public_columns]].copy()
        masks = {
            'hn': 'HN-ปิดบัง',
            'receiver': 'ปิดบัง',
            'reporter': 'ปิดบัง',
            'follower': 'ปิดบัง',
            'supervisor': 'ปิดบัง',
        }
        for col, replacement in masks.items():
            if col in result.columns:
                values = result[col].astype(str).str.strip()
                result[col] = values.where(values.isin(['', 'nan', 'None']), replacement)
        # HN-like numbers can also be typed into free-text fields. Scrub those
        # before charts, tables, or exports can expose them on the public app.
        for col in ['specimen_issue', 'request_issue', 'payment_issue', 'it_issue',
                    'other_issue', 'reason', 'notes', 'status', 'resolution',
                    'followup', 'evidence']:
            if col in result.columns:
                result[col] = result[col].astype(str).str.replace(
                    r'(?<!\d)\d{6,10}(?!\d)', '[เลขอ้างอิงปิดบัง]', regex=True
                )
        return result

    ingestion_warnings = df_cases.attrs.get('ingestion_warnings', [])
    denominator = df_cases.attrs.get('denominator', pd.DataFrame())
    denominator_sheet_found = bool(df_cases.attrs.get('denominator_sheet_found', False))
    public_cases = mask_public_identifiers(ensure_fiscal_year(df_cases))
    public_causes = mask_public_identifiers(ensure_fiscal_year(df_causes))
    public_cases.attrs['ingestion_warnings'] = ingestion_warnings
    # Keep DataFrame metadata JSON-serializable so Streamlit can render tables
    # without warnings when the source has an optional denominator sheet.
    public_cases.attrs = {}
    public_cases.attrs['denominator_records'] = denominator.to_dict('records') if not denominator.empty else []
    public_cases.attrs['denominator_sheet_found'] = denominator_sheet_found
    latest_date = pd.to_datetime(public_cases.get('date'), errors='coerce').dropna()
    public_cases.attrs['sync_meta'] = {
        'status': 'success',
        'synced_at': datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%d/%m/%Y %H:%M น.'),
        'source': 'Google Sheets' if isinstance(file_source, str) and file_source.startswith(('http://', 'https://')) else 'ไฟล์อัปโหลด',
        'sheet_count': int(public_cases['source_sheet'].nunique()) if 'source_sheet' in public_cases.columns else 0,
        'case_count': int(len(public_cases)),
        'latest_date': latest_date.max().strftime('%Y-%m-%d') if not latest_date.empty else None,
        'denominator_rows': int(len(denominator)),
        'denominator_sheet_found': denominator_sheet_found,
    }
    return public_cases, public_causes


# ==============================================================================
# 3. REUSABLE POPOVER MULTISELECT FILTER
# ==============================================================================

def render_popover_multiselect(
    label: str,
    icon: str,
    all_options: list,
    state_key: str,
    unit: str = "รายการ",
    max_height: int = 210
) -> list:
    """
    Renders a compact, modern Popover filter button on the sidebar.
    When closed: Displays only the summary count (e.g. 'ทั้งหมด' or 'เลือกแล้ว 4 รายการ')
    When opened: Displays search input, Select All / Clear All buttons, and a scrollable checkbox list.
    """
    all_options_set = set(all_options)
    previous_options_key = f"_available_{state_key}"
    previous_options = set(st.session_state.get(previous_options_key, all_options))
    
    # Initialize session state if first run
    if state_key not in st.session_state:
        st.session_state[state_key] = set(all_options)

    current_selected = set(st.session_state[state_key])
    # Preserve the user's "all" choice when new months, Wards, or reasons
    # arrive from Google Sheets. Explicit partial selections remain partial.
    if current_selected == previous_options:
        current_selected = set(all_options)
    else:
        current_selected &= all_options_set
    st.session_state[state_key] = current_selected
    st.session_state[previous_options_key] = set(all_options)
    if previous_options != all_options_set:
        for opt in all_options:
            st.session_state[f"chk_{state_key}_{opt}"] = opt in current_selected

    total_count = len(all_options)
    selected_count = len(current_selected)
    
    # Format closed button summary text
    if selected_count == total_count or total_count == 0:
        summary_text = "ทั้งหมด"
    elif selected_count == 0:
        summary_text = "ไม่ได้เลือก"
    else:
        summary_text = f"เลือกแล้ว {selected_count} {unit}"
        
    button_label = f"{icon} {label} · {summary_text}"
    
    with st.popover(button_label, width="stretch"):
        st.markdown(f"<div style='font-size: 0.88rem; font-weight: 600; color: #0F172A; margin-bottom: 6px;'>{icon} {label}</div>", unsafe_allow_html=True)
        
        search_key = f"search_{state_key}"
        search_term = st.text_input(
            "ค้นหา",
            placeholder=f"🔍 ค้นหา {label}...",
            key=search_key,
            label_visibility="collapsed"
        )
        
        # Select All & Clear All buttons
        btn_c1, btn_c2 = st.columns(2)
        if btn_c1.button("เลือกทั้งหมด", key=f"all_{state_key}", width="stretch"):
            st.session_state[state_key] = set(all_options)
            for opt in all_options:
                st.session_state[f"chk_{state_key}_{opt}"] = True
            st.rerun()
            
        if btn_c2.button("ล้างทั้งหมด", key=f"clr_{state_key}", width="stretch"):
            st.session_state[state_key] = set()
            for opt in all_options:
                st.session_state[f"chk_{state_key}_{opt}"] = False
            st.rerun()
            
        # Filter options based on search query
        filtered_opts = [
            opt for opt in all_options
            if not search_term or search_term.lower() in str(opt).lower()
        ]
        
        # Scrollable Checkboxes Container
        with st.container(height=max_height):
            if not filtered_opts:
                st.caption("ไม่พบรายการที่ค้นหา")
            else:
                for opt in filtered_opts:
                    chk_key = f"chk_{state_key}_{opt}"
                    # Sync state value if missing
                    if chk_key not in st.session_state:
                        st.session_state[chk_key] = (opt in current_selected)
                    
                    chk_val = st.checkbox(str(opt), key=chk_key)
                    if chk_val and opt not in current_selected:
                        current_selected.add(opt)
                        st.session_state[state_key] = current_selected
                    elif not chk_val and opt in current_selected:
                        current_selected.discard(opt)
                        st.session_state[state_key] = current_selected

    # Keep the display order stable so summaries such as the month range follow
    # chronological/source order instead of the arbitrary order of a set.
    return [opt for opt in all_options if opt in st.session_state[state_key]]


# ==============================================================================
# 4. SIDEBAR RENDERING
# ==============================================================================

def render_sidebar():
    """
    Renders clean, compact sidebar with file uploader and popover-based filters.
    """
    with st.sidebar:
        # App brand header
        brand_logo, brand_copy = st.columns([0.8, 2.8], vertical_alignment="center")
        with brand_logo:
            if os.path.exists(LOGO_PATH):
                st.image(LOGO_PATH, width=52)
            else:
                st.markdown("<div style='font-size: 1.6rem;'>🧪</div>", unsafe_allow_html=True)
        with brand_copy:
            st.markdown("""
            <div style="font-weight: 700; font-size: 1.05rem; color: #5B146F; line-height: 1.2;">Rejection Lab</div>
            <div style="font-size: 0.72rem; color: #6B5A70;">TUH Quality Dashboard</div>
            """, unsafe_allow_html=True)
        
        with st.expander("📁 แหล่งข้อมูล (Data Source)", expanded=False):
            uploaded_file = st.file_uploader(
                "อัปโหลดไฟล์ (.xlsx หรือ .csv)",
                type=["xlsx", "xls", "csv"],
                help="รองรับไฟล์แบบบันทึกที่มีหลายชีทรายเดือน หรือไฟล์ CSV"
            )
            
        active_source = None
        source_label = ""
        google_sync_error = None
        
        if uploaded_file is not None:
            active_source = uploaded_file
            source_label = uploaded_file.name
        else:
            active_source = GOOGLE_SHEET_XLSX_URL
            source_label = "Google Sheets (ซิงก์อัตโนมัติ)"
                    
        if active_source is None:
            st.error("⚠️ ไม่พบไฟล์ข้อมูล กรุณาอัปโหลดไฟล์ Excel/CSV")
            st.stop()
            
        st.markdown("<hr style='margin: 0.6rem 0 0.8rem 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)
        
        # Load raw data
        try:
            df_cases_all, df_causes_all = load_data(active_source)
        except Exception as e:
            if uploaded_file is not None:
                st.error(f"อ่านไฟล์ที่อัปโหลดไม่ได้: {e}")
                st.stop()
            google_sync_error = e if active_source == GOOGLE_SHEET_XLSX_URL else None
            active_source = None
            for p in DEFAULT_EXCEL_PATHS:
                if os.path.exists(p):
                    try:
                        df_cases_all, df_causes_all = load_data(p)
                        source_label = f"ไฟล์สำรอง: {os.path.basename(p)}"
                        break
                    except Exception:
                        continue
            else:
                st.error(f"เกิดข้อผิดพลาดในการอ่านข้อมูล: {e}")
                st.stop()

        st.caption(f"📄 ใช้ข้อมูล: `{source_label}`")
        sync_meta = df_cases_all.attrs.get('sync_meta', {})
        if active_source == GOOGLE_SHEET_XLSX_URL:
            sync_time_text = sync_meta.get('synced_at') or 'ยังไม่ทราบเวลา'
            sheet_count = sync_meta.get('sheet_count', 0)
            sync_denominator = sync_meta.get('denominator_rows', 0)
            sync_denominator_sheet = sync_meta.get('denominator_sheet_found', False)
            denominator_status = 'พร้อมใช้งาน' if sync_denominator else ('พบแท็บแล้ว รอข้อมูล' if sync_denominator_sheet else 'ยังไม่พบแท็บยอดตรวจทั้งหมด')
            st.markdown(
                f"<div style='background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;padding:0.65rem 0.75rem;margin:0.45rem 0 0.7rem;'>"
                f"<div style='font-weight:700;color:#166534;'>✅ ซิงก์ Google Sheets สำเร็จ</div>"
                f"<div style='font-size:0.76rem;color:#475569;margin-top:0.2rem;'>อัปเดตล่าสุด: {sync_time_text}<br>อ่านแล้ว {sheet_count} ชีทรายเดือน · รีเฟรชอัตโนมัติทุก 15 นาที</div>"
                f"<div style='font-size:0.74rem;color:#64748B;margin-top:0.25rem;'>ตัวหารอัตราการปฏิเสธ: {denominator_status}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        elif google_sync_error is not None:
            st.error("❌ ซิงก์ Google Sheets ไม่สำเร็จ — ขณะนี้ใช้ไฟล์สำรองในแอป ตัวเลขอาจยังไม่ใช่ข้อมูลล่าสุด")

        for warning in df_cases_all.attrs.get('ingestion_warnings', []):
            st.warning(warning)
            
        if df_cases_all.empty:
            st.warning("⚠️ ไม่มีข้อมูลในไฟล์")
            st.stop()

        parsed_latest = pd.to_datetime(df_cases_all.get('date'), errors='coerce').dropna()
        if not parsed_latest.empty:
            latest_dt = parsed_latest.max()
            st.caption(f"🕒 ข้อมูลล่าสุดในตาราง: {latest_dt.day:02d}/{latest_dt.month:02d}/{latest_dt.year + 543}")
            
        st.markdown("<div style='font-size: 0.84rem; font-weight: 600; color: #334155; margin-bottom: 0.5rem;'>🔎 ตัวกรองข้อมูล (Filters)</div>", unsafe_allow_html=True)

        # 1. Fiscal Year Filter
        def fiscal_sort_key(label: str):
            match = re.search(r'(\d{4})$', str(label))
            return int(match.group(1)) if match else 0

        all_fiscal_years = sorted(
            df_cases_all['fiscal_year'].dropna().unique().tolist(),
            key=fiscal_sort_key
        )
        selected_fiscal_years = render_popover_multiselect(
            label="ปีงบประมาณ",
            icon="🗓️",
            all_options=all_fiscal_years,
            state_key="sel_fiscal_years",
            unit="ปี"
        )
        
        # 2. Month Filter
        all_months_ym = sorted(df_cases_all['year_month'].unique().tolist())
        ym_to_th = dict(zip(df_cases_all['year_month'], df_cases_all['thai_month_year']))
        th_to_ym = {v: k for k, v in ym_to_th.items()}
        all_months_th = [ym_to_th[ym] for ym in all_months_ym]
        
        selected_months_th = render_popover_multiselect(
            label="ช่วงเดือน",
            icon="📅",
            all_options=all_months_th,
            state_key="sel_months",
            unit="เดือน"
        )
        selected_ym = [th_to_ym[m] for m in selected_months_th if m in th_to_ym]
        
        # 3. Ward Group Filter
        all_ward_groups = sorted(df_cases_all['ward_group'].dropna().unique().tolist())
        selected_groups = render_popover_multiselect(
            label="กลุ่มหอผู้ป่วย",
            icon="🏥",
            all_options=all_ward_groups,
            state_key="sel_groups",
            unit="กลุ่ม"
        )
        
        # 4. Ward Filter (cascaded by selected Ward Groups)
        cascaded_wards = sorted(
            df_cases_all[df_cases_all['ward_group'].isin(selected_groups)]['ward_standard'].unique().tolist()
        )
        selected_wards = render_popover_multiselect(
            label="Ward",
            icon="🚪",
            all_options=cascaded_wards,
            state_key="sel_wards",
            unit="Ward"
        )
        
        # 5. Rejection Category Filter
        all_categories = sorted(df_causes_all['category'].dropna().unique().tolist())
        selected_categories = render_popover_multiselect(
            label="กลุ่มสาเหตุ",
            icon="⚠️",
            all_options=all_categories,
            state_key="sel_categories",
            unit="กลุ่ม"
        )
        
        # 6. Root Cause Filter (cascaded by selected Categories)
        cascaded_causes = sorted(
            df_causes_all[df_causes_all['category'].isin(selected_categories)]['reason'].unique().tolist()
        )
        selected_root_causes = render_popover_multiselect(
            label="Root Cause",
            icon="🔍",
            all_options=cascaded_causes,
            state_key="sel_root_causes",
            unit="สาเหตุ"
        )
        
        # 7. Specimen Type Filter
        all_specimens = sorted(df_cases_all['specimen_type'].dropna().unique().tolist())
        selected_specimens = render_popover_multiselect(
            label="สิ่งส่งตรวจ",
            icon="🧫",
            all_options=all_specimens,
            state_key="sel_specimens",
            unit="ชนิด"
        )
        
        # 8. Risk Level Filter
        all_risks = sorted(df_cases_all['risk_level'].dropna().unique().tolist())
        selected_risks = render_popover_multiselect(
            label="ความเสี่ยง",
            icon="🚨",
            all_options=all_risks,
            state_key="sel_risks",
            unit="ระดับ"
        )
        
        # 9. Resolution Status Filter
        all_resolutions = sorted(df_cases_all['resolution'].dropna().unique().tolist())
        selected_resolutions = render_popover_multiselect(
            label="การแก้ไข",
            icon="✅",
            all_options=all_resolutions,
            state_key="sel_resolutions",
            unit="สถานะ"
        )
        
        st.markdown("<hr style='margin: 0.8rem 0 0.6rem 0; border: none; border-top: 1px solid #E2E8F0;'/>", unsafe_allow_html=True)
        
        # Calculate Active Filters Count
        active_count = 0
        if len(selected_fiscal_years) < len(all_fiscal_years): active_count += 1
        if len(selected_months_th) < len(all_months_th): active_count += 1
        if len(selected_groups) < len(all_ward_groups): active_count += 1
        if len(selected_wards) < len(cascaded_wards): active_count += 1
        if len(selected_categories) < len(all_categories): active_count += 1
        if len(selected_root_causes) < len(cascaded_causes): active_count += 1
        if len(selected_specimens) < len(all_specimens): active_count += 1
        if len(selected_risks) < len(all_risks): active_count += 1
        if len(selected_resolutions) < len(all_resolutions): active_count += 1
        
        col_act1, col_act2 = st.columns([1, 1])
        with col_act1:
            if active_count > 0:
                st.markdown(f"<div style='font-size: 0.78rem; color: #6c5070; font-weight: 600; padding-top: 6px;'>Active filters: <b>{active_count}</b></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div style='font-size: 0.78rem; color: #94A3B8; padding-top: 6px;'>Active filters: 0</div>", unsafe_allow_html=True)
                
        with col_act2:
            if st.button("🔄 Reset Filters", width="stretch"):
                # Reset all session state filter sets to all
                st.session_state["sel_fiscal_years"] = set(all_fiscal_years)
                st.session_state["sel_months"] = set(all_months_th)
                st.session_state["sel_groups"] = set(all_ward_groups)
                st.session_state["sel_wards"] = set(cascaded_wards)
                st.session_state["sel_categories"] = set(all_categories)
                st.session_state["sel_root_causes"] = set(cascaded_causes)
                st.session_state["sel_specimens"] = set(all_specimens)
                st.session_state["sel_risks"] = set(all_risks)
                st.session_state["sel_resolutions"] = set(all_resolutions)
                # Clear all individual checkbox keys
                for k in list(st.session_state.keys()):
                    if k.startswith("chk_sel_"):
                        del st.session_state[k]
                st.rerun()

    filter_bundle = {
        'df_cases_all': df_cases_all,
        'df_causes_all': df_causes_all,
        'denominator': pd.DataFrame(df_cases_all.attrs.get('denominator_records', [])),
        'denominator_sheet_found': bool(df_cases_all.attrs.get('denominator_sheet_found', False)),
        'selected_fiscal_years': selected_fiscal_years,
        'selected_ym': selected_ym,
        'selected_months_th': selected_months_th,
        'selected_groups': selected_groups,
        'selected_wards': selected_wards,
        'selected_categories': selected_categories,
        'selected_root_causes': selected_root_causes,
        'selected_specimens': selected_specimens,
        'selected_risks': selected_risks,
        'selected_resolutions': selected_resolutions,
        'all_wards': sorted(df_cases_all['ward_standard'].dropna().unique().tolist()),
        'active_count': active_count
    }
    return filter_bundle


# ==============================================================================
# 5. FILTER APPLICATION & PREPARATION
# ==============================================================================

def apply_filters(bundle: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Applies all selected filter dimensions to Case-level and Cause-level DataFrames.
    """
    df_causes_all = bundle['df_causes_all']
    df_cases_all = bundle['df_cases_all']
    
    # Cause-level filter
    cause_mask = (
        df_causes_all['fiscal_year'].isin(bundle['selected_fiscal_years']) &
        df_causes_all['year_month'].isin(bundle['selected_ym']) &
        df_causes_all['ward_group'].isin(bundle['selected_groups']) &
        df_causes_all['ward_standard'].isin(bundle['selected_wards']) &
        df_causes_all['category'].isin(bundle['selected_categories']) &
        df_causes_all['reason'].isin(bundle['selected_root_causes']) &
        df_causes_all['specimen_type'].isin(bundle['selected_specimens']) &
        df_causes_all['risk_level'].isin(bundle['selected_risks']) &
        df_causes_all['resolution'].isin(bundle['selected_resolutions'])
    )
    df_causes = df_causes_all[cause_mask].copy()
    
    # Case-level filter (keep cases whose case_id matches filtered causes)
    valid_case_ids = set(df_causes['case_id'])
    df_cases = df_cases_all[df_cases_all['case_id'].isin(valid_case_ids)].copy()
    
    return df_cases, df_causes


# ==============================================================================
# 6. HEADER & QUICK FILTER SUMMARY BAR
# ==============================================================================

def render_header(df_cases: pd.DataFrame | None = None):
    """
    Renders a compact, clean hospital header bar.
    """
    fiscal_years = set()
    if df_cases is not None and not df_cases.empty and {'date'}.issubset(df_cases.columns):
        parsed_dates = pd.to_datetime(df_cases['date'], errors='coerce')
        for dt in parsed_dates.dropna():
            fiscal_years.add(int(dt.year + (1 if dt.month >= 10 else 0) + 543))
    if fiscal_years:
        ordered_fy = sorted(fiscal_years)
        fiscal_label = (
            f"ปีงบประมาณ {ordered_fy[0]}"
            if len(ordered_fy) == 1
            else f"ปีงบประมาณ {ordered_fy[0]}–{ordered_fy[-1]}"
        )
    else:
        fiscal_label = "ปีงบประมาณ -"

    logo_html = (
        f"<img src='{LOGO_DATA_URI}' alt='TUH logo' style='width:52px;height:52px;object-fit:contain;border-radius:12px;background:#FFFFFF;'>"
        if LOGO_DATA_URI else "🧪"
    )
    st.markdown("""
    <div class="compact-header">
        <div style="display:flex;align-items:center;gap:12px;">
            {logo_html}
            <div>
            <h1 class="compact-header-title">Specimen Rejection Dashboard</h1>
            <p class="compact-header-sub">ระบบติดตาม วิเคราะห์ และควบคุมคุณภาพการปฏิเสธสิ่งส่งตรวจทางห้องปฏิบัติการ โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ</p>
            </div>
        </div>
        <div>
            <span class="header-badge">{fiscal_label}</span>
        </div>
    </div>
    """.format(logo_html=logo_html, fiscal_label=fiscal_label), unsafe_allow_html=True)


def render_quick_filter_bar(df_cases: pd.DataFrame, bundle: dict):
    """
    Renders top overview summary bar indicating active query scope without cluttered tags.
    """
    months = bundle['selected_months_th']
    date_range_str = f"{months[0]} - {months[-1]}" if len(months) > 1 else (months[0] if months else "-")
    ward_count = df_cases['ward_standard'].nunique()
    cause_count = len(bundle['selected_root_causes'])
    total_cases = len(df_cases)
    
    col_bar, col_btn = st.columns([12, 1])
    with col_bar:
        st.markdown(f"""
        <div class="quick-filter-bar">
            <div>
                <span>📅 <b>ช่วงข้อมูล:</b> <span class="qf-tag">{date_range_str}</span></span>
                <span style="color: #E6C94A; margin: 0 10px;">|</span>
                <span>🏢 <b>กลุ่มแผนก:</b> <span class="qf-tag">{len(bundle['selected_groups'])} กลุ่ม</span></span>
                <span style="color: #E6C94A; margin: 0 10px;">|</span>
                <span>🚪 <b>Ward:</b> <span class="qf-tag">{ward_count} แห่ง</span></span>
                <span style="color: #E6C94A; margin: 0 10px;">|</span>
                <span>⚠️ <b>Root Cause:</b> <span class="qf-tag">{cause_count} รายการ</span></span>
                <span style="color: #E6C94A; margin: 0 10px;">|</span>
                <span>📊 <b>เคสปฏิเสธรวม:</b> <span style="background-color: #f7eef6; color: #6c5070; padding: 2px 8px; border-radius: 6px; font-weight: 700;">{total_cases:,} เคส</span></span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        if bundle['active_count'] > 0:
            if st.button("รีเซ็ต", key="qf_reset", help="รีเซ็ตตัวกรองทั้งหมดเป็นค่าเริ่มต้น"):
                for k in list(st.session_state.keys()):
                    if k.startswith("sel_") or k.startswith("chk_sel_"):
                        del st.session_state[k]
                st.rerun()


# ==============================================================================
# 7. KPI CARDS (RESPONSIVE GRID)
# ==============================================================================

def render_kpi_cards(df_cases: pd.DataFrame, df_causes: pd.DataFrame, num_months: int):
    """
    Renders 5 KPI cards in a sleek responsive layout.
    """
    kpis = cleaner.get_kpis(df_cases, df_causes)
    
    total = kpis['total_cases']
    top_w = kpis['top_ward']
    top_w_cases = kpis['top_ward_cases']
    top_w_pct = round((top_w_cases / max(1, total)) * 100, 1)
    
    top_c = kpis['top_cause']
    top_c_count = kpis['top_cause_count']
    
    res_rate = kpis['resolution_rate']
    res_color = "#16A34A" if res_rate >= 85 else "#F4C400"
    
    inc_count = kpis['incident_count']
    inc_color = "#DC2626" if inc_count > 0 else "#64748B"
    
    st.html(f"""
    <div class="kpi-container">
        <!-- Card 1 -->
        <div class="kpi-card" title="จำนวนสิ่งส่งตรวจที่ถูกปฏิเสธทั้งหมดในช่วงเวลาที่เลือก">
            <div class="kpi-header">
                <span class="kpi-label">สิ่งส่งตรวจปฏิเสธรวม</span>
                <span class="kpi-icon">🧪</span>
            </div>
            <div class="kpi-value" style="color: #6c5070;">{total:,}</div>
            <div class="kpi-sub">จาก {num_months} เดือนที่เลือก</div>
        </div>
        
        <!-- Card 2 -->
        <div class="kpi-card" title="{top_w}">
            <div class="kpi-header">
                <span class="kpi-label">Ward ที่พบปัญหาสูงสุด</span>
                <span class="kpi-icon">🏥</span>
            </div>
            <div class="kpi-value" style="color: #DC2626; font-size: 1.25rem;">{top_w}</div>
            <div class="kpi-sub">{top_w_cases:,} ครั้ง ({top_w_pct}%)</div>
        </div>
        
        <!-- Card 3 -->
        <div class="kpi-card" title="{top_c}">
            <div class="kpi-header">
                <span class="kpi-label">สาเหตุการปฏิเสธอันดับ 1</span>
                <span class="kpi-icon">⚠️</span>
            </div>
            <div class="kpi-value" style="color: #D97706; font-size: 1.25rem;">{top_c}</div>
            <div class="kpi-sub">{top_c_count:,} ครั้ง</div>
        </div>
        
        <!-- Card 4 -->
        <div class="kpi-card" title="สัดส่วนเคสที่มีการแก้ไขแล้ว หรือขอยกเลิกรายการ">
            <div class="kpi-header">
                <span class="kpi-label">อัตราการแก้ไขสำเร็จ</span>
                <span class="kpi-icon">🎯</span>
            </div>
            <div class="kpi-value" style="color: {res_color};">{res_rate}%</div>
            <div class="kpi-sub">สถานะแก้ไขแล้ว/ยกเลิก</div>
        </div>
        
        <!-- Card 5 -->
        <div class="kpi-card" title="เคสที่บันทึกเป็นอุบัติการณ์ความเสี่ยงที่ต้องติดตามคุณภาพ">
            <div class="kpi-header">
                <span class="kpi-label">เคสติดตามความเสี่ยง</span>
                <span class="kpi-icon">🚨</span>
            </div>
            <div class="kpi-value" style="color: {inc_color};">{inc_count:,} <span style="font-size: 0.95rem; font-weight: 500;">เคส</span></div>
            <div class="kpi-sub">เคสอุบัติการณ์ CQI</div>
        </div>
    </div>
    """)


# ==============================================================================
# 8. TAB 1: CHARTS & VISUALIZATIONS
# ==============================================================================

def render_monthly_trend(df_cases: pd.DataFrame):
    """
    Renders Monthly Rejection Trend (Bar + Trendline + Average line + MoM tooltip).
    """
    df_trend = cleaner.get_monthly_trend(df_cases)
    if df_trend.empty:
        st.info("ไม่มีข้อมูลรายเดือนตามเงื่อนไขที่เลือก")
        return

    # Calculate MoM (Month-over-Month) percentage change
    df_trend['prev_count'] = df_trend['count'].shift(1)
    df_trend['mom_pct'] = ((df_trend['count'] - df_trend['prev_count']) / df_trend['prev_count']) * 100
    df_trend['mom_str'] = df_trend['mom_pct'].apply(
        lambda x: "เริ่มต้น" if pd.isna(x) else (f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
    )
    
    avg_count = df_trend['count'].mean()

    fig = go.Figure()
    
    # Bar Chart
    fig.add_trace(go.Bar(
        x=df_trend['thai_month_year'],
        y=df_trend['count'],
        name='จำนวนเคสปฏิเสธ',
        marker=dict(color='#3B82F6', cornerradius=4),
        customdata=df_trend['mom_str'],
        hovertemplate="<b>%{x}</b><br>จำนวนเคสปฏิเสธ: <b>%{y:,} เคส</b><br>เทียบเดือนก่อนหน้า: <b>%{customdata}</b><extra></extra>",
        text=df_trend['count'] if len(df_trend) <= 12 else None,
        textposition='outside',
        textfont=dict(size=11, color='#1E293B')
    ))
    
    # Trendline
    fig.add_trace(go.Scatter(
        x=df_trend['thai_month_year'],
        y=df_trend['count'],
        mode='lines+markers',
        name='เส้นแนวโน้ม',
        line=dict(color='#1D4ED8', width=2.5),
        marker=dict(size=6, color='#1E3A8A'),
        hoverinfo='skip'
    ))
    
    # Average Reference Line
    fig.add_hline(
        y=avg_count,
        line_dash="dash",
        line_color="#EF4444",
        line_width=1.5,
        annotation_text=f"เฉลี่ย: {avg_count:.1f}",
        annotation_position="top right",
        annotation_font=dict(size=11, color="#EF4444")
    )
    
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=20, t=10, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color='#475569')),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', title=dict(text="จำนวนเคส", font=dict(size=12, color='#64748B'))),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, font_family="Noto Sans Thai")
    )
    st.plotly_chart(fig, width="stretch")


def render_category_donut(df_causes: pd.DataFrame):
    """
    Renders Donut Chart with total in center, clean bottom legend (Category, Cases, %).
    """
    df_cat = cleaner.get_category_distribution(df_causes)
    if df_cat.empty:
        st.info("ไม่มีข้อมูลสาเหตุตามเงื่อนไขที่เลือก")
        return

    total_causes = df_cat['count'].sum()
    
    color_map = {
        'ปัญหาด้านสิ่งส่งตรวจ': '#6c5070',
        'ปัญหาด้านใบส่งตรวจ': '#F4C400',
        'ปัญหาด้านระบบการเงิน': '#c2dbc1',
        'ปัญหาด้านระบบสารสนเทศ': '#C43B8A',
        'ปัญหาอื่นๆ / รายละเอียดเพิ่มเติม': '#E94B3C',
        'ไม่ระบุสาเหตุชัดเจน': '#D9CFE0'
    }
    colors = [color_map.get(c, '#94A3B8') for c in df_cat['category']]
    
    # Format labels with cases and pct for clean legend
    df_cat['legend_label'] = df_cat.apply(lambda r: f"{r['category']} ({r['count']:,} · {r['pct']}%)", axis=1)

    fig = go.Figure(data=[go.Pie(
        labels=df_cat['legend_label'],
        values=df_cat['count'],
        hole=0.62,
        marker=dict(colors=colors, line=dict(color='#FFFFFF', width=2)),
        textinfo='percent',
        textposition='inside',
        insidetextorientation='horizontal',
        hovertemplate="<b>%{label}</b><br>จำนวน: %{value:,} ครั้ง (%{percent})<extra></extra>"
    )])
    
    # Center text annotation
    fig.add_annotation(
        text=f"<b style='font-size:22px;color:#5B146F;'>{total_causes:,}</b><br><span style='font-size:11px;color:#6B5A70;'>สาเหตุทั้งหมด</span>",
        x=0.5, y=0.5,
        font_size=18,
        showarrow=False
    )
    
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=11, color='#334155')
        ),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, font_family="Noto Sans Thai")
    )
    st.plotly_chart(fig, width="stretch")


def render_top_wards_chart(df_cases: pd.DataFrame):
    """
    Renders Top 10 Wards horizontal bar chart sorted descending.
    """
    df_top_w = cleaner.get_top_wards(df_cases, top_n=10)
    if df_top_w.empty:
        st.info("ไม่มีข้อมูลหอผู้ป่วย")
        return

    # Sort ascending for plotly horizontal bar (renders top rank at the top)
    df_top_w = df_top_w.sort_values('count', ascending=True)
    
    fig = px.bar(
        df_top_w,
        x='count',
        y='ward_standard',
        orientation='h',
        color='ward_group',
        text='count',
        color_discrete_sequence=['#6c5070', '#df6a6a', '#c2dbc1', '#d8a6b5', '#bfa6c5', '#f1c7a5', '#867986']
    )
    fig.update_traces(
        textposition='outside',
        textfont=dict(size=11, color='#1E293B'),
        marker=dict(cornerradius=4),
        hovertemplate="<b>%{y}</b><br>กลุ่มแผนก: %{fullData.name}<br>จำนวนปฏิเสธ: <b>%{x:,} ครั้ง</b><extra></extra>"
    )
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=30, t=10, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="จำนวนเคสที่ปฏิเสธ", showgrid=True, gridcolor='#F1F5F9', tickfont=dict(size=11)),
        yaxis=dict(title="", showgrid=False, tickfont=dict(size=11, color='#1E293B')),
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, font_family="Noto Sans Thai")
    )
    st.plotly_chart(fig, width="stretch")


def render_top_root_causes_chart(df_causes: pd.DataFrame):
    """
    Renders Top 10 Root Causes horizontal bar chart sorted descending.
    """
    df_top_r = cleaner.get_top_reasons(df_causes, top_n=10)
    if df_top_r.empty:
        st.info("ไม่มีข้อมูลสาเหตุ")
        return

    df_top_r = df_top_r.sort_values('count', ascending=True)
    
    cat_colors = {
        'ปัญหาด้านสิ่งส่งตรวจ': '#6c5070',
        'ปัญหาด้านใบส่งตรวจ': '#F4C400',
        'ปัญหาด้านระบบการเงิน': '#c2dbc1',
        'ปัญหาด้านระบบสารสนเทศ': '#C43B8A',
        'ปัญหาอื่นๆ / รายละเอียดเพิ่มเติม': '#E94B3C'
    }
    
    fig = px.bar(
        df_top_r,
        x='count',
        y='reason',
        orientation='h',
        color='category',
        text='count',
        color_discrete_map=cat_colors
    )
    fig.update_traces(
        textposition='outside',
        textfont=dict(size=11, color='#1E293B'),
        marker=dict(cornerradius=4),
        hovertemplate="<b>%{y}</b><br>กลุ่มปัญหา: %{fullData.name}<br>ความถี่: <b>%{x:,} ครั้ง</b><extra></extra>"
    )
    fig.update_layout(
        height=380,
        margin=dict(l=10, r=30, t=10, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="ความถี่ที่พบ (ครั้ง)", showgrid=True, gridcolor='#F1F5F9', tickfont=dict(size=11)),
        yaxis=dict(title="", showgrid=False, tickfont=dict(size=11, color='#1E293B')),
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12, font_family="Noto Sans Thai")
    )
    st.plotly_chart(fig, width="stretch")


def render_fiscal_year_comparison(df_cases: pd.DataFrame):
    """Render a year-over-year comparison that expands automatically as new FY data arrives."""
    if 'fiscal_year' not in df_cases.columns or df_cases.empty:
        st.info("ยังไม่มีข้อมูลสำหรับเปรียบเทียบปีงบประมาณ")
        return

    df_fy = (
        df_cases.dropna(subset=['fiscal_year'])
        .groupby('fiscal_year', as_index=False)
        .agg(count=('case_id', 'size'), months=('year_month', 'nunique'))
    )
    if df_fy.empty:
        st.info("ยังไม่มีข้อมูลสำหรับเปรียบเทียบปีงบประมาณ")
        return

    # Keep the fiscal-year labels in chronological order while displaying the
    # Thai label used by the filters and header.
    df_fy['fy_order'] = df_fy['fiscal_year'].astype(str).str.extract(r'(\d+)')[0].astype(float)
    df_fy = df_fy.sort_values(['fy_order', 'fiscal_year'])
    coverage_text = ' · '.join(
        f"{row['fiscal_year']}: {int(row['months'])}/12 เดือน"
        for _, row in df_fy.iterrows()
    )
    st.caption(f"จำนวนเดือนที่มีข้อมูล — {coverage_text} (ใช้ประกอบการเทียบยอดรวม)")
    fig = px.bar(
        df_fy,
        x='fiscal_year',
        y='count',
        text='count',
        custom_data=['months'],
        color_discrete_sequence=['#df6a6a'],
    )
    fig.update_traces(
        textposition='outside',
        textfont=dict(size=12, color='#1E293B'),
        marker=dict(cornerradius=6),
        hovertemplate="<b>%{x}</b><br>จำนวนเคสปฏิเสธ: <b>%{y:,} เคส</b><br>เดือนที่มีข้อมูล: %{customdata[0]}/12<extra></extra>",
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=20, t=10, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title='', showgrid=False, tickfont=dict(size=11, color='#475569')),
        yaxis=dict(title='จำนวนเคส', showgrid=True, gridcolor='#F1F5F9', tickfont=dict(size=11)),
        showlegend=False,
        hoverlabel=dict(bgcolor='#FFFFFF', font_size=12, font_family='Noto Sans Thai'),
    )
    st.plotly_chart(fig, width="stretch")


def _quality_status(count: int, target: int) -> tuple[str, str, str]:
    """Return Thai status text plus foreground/background colors."""
    warning_limit = max(target + 1, int(round(target * 1.5)))
    if count <= target:
        return "ผ่านเป้าหมาย", "#166534", "#DCFCE7"
    if count <= warning_limit:
        return "เฝ้าระวัง", "#92400E", "#FEF3C7"
    return "เกินเป้าหมาย", "#991B1B", "#FEE2E2"


def render_quality_target(df_cases: pd.DataFrame):
    """Show monthly quality target with green/yellow/red status by month."""
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">🎯 เป้าหมายคุณภาพรายเดือน</div>
        <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 0.8rem;">
            สีเขียว = ไม่เกินเป้าหมาย · สีเหลือง = เฝ้าระวัง · สีแดง = สูงกว่าเกณฑ์เตือน
        </div>
    """, unsafe_allow_html=True)
    target = st.number_input(
        "เป้าหมายเคสปฏิเสธต่อเดือน (เคส)",
        min_value=1,
        max_value=1000,
        value=DEFAULT_MONTHLY_QUALITY_TARGET,
        step=1,
        key="quality_target_monthly",
        help="ค่าเริ่มต้น 30 เคส/เดือน; สีเหลืองเริ่มเมื่อเกินเป้าหมายถึง 1.5 เท่า และสีแดงเมื่อเกินเกณฑ์เตือน",
    )
    trend = cleaner.get_monthly_trend(df_cases)
    if trend.empty:
        st.info("ไม่มีข้อมูลสำหรับประเมินเป้าหมายรายเดือน")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    latest = trend.iloc[-1]
    latest_status, latest_fg, latest_bg = _quality_status(int(latest['count']), int(target))
    warning_limit = max(int(target) + 1, int(round(int(target) * 1.5)))
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:0.65rem;flex-wrap:wrap;margin-bottom:0.8rem;'>"
        f"<span style='font-weight:700;color:#334155;'>เดือนล่าสุด: {latest['thai_month_year']} · {int(latest['count']):,} เคส</span>"
        f"<span style='background:{latest_bg};color:{latest_fg};padding:0.25rem 0.7rem;border-radius:999px;font-weight:700;'>{latest_status}</span>"
        f"<span style='font-size:0.78rem;color:#64748B;'>สีแดงตั้งแต่ {warning_limit + 1:,} เคส</span></div>",
        unsafe_allow_html=True,
    )

    rows = []
    for _, row in trend.iterrows():
        status, fg, bg = _quality_status(int(row['count']), int(target))
        rows.append(
            f"<tr><td>{row['thai_month_year']}</td><td style='text-align:right;font-weight:700;'>{int(row['count']):,}</td>"
            f"<td><span style='background:{bg};color:{fg};padding:0.2rem 0.55rem;border-radius:999px;font-weight:700;'>{status}</span></td></tr>"
        )
    st.markdown(
        "<table style='width:100%;border-collapse:collapse;font-size:0.84rem;'>"
        "<thead><tr style='color:#64748B;border-bottom:1px solid #E2E8F0;'>"
        "<th style='text-align:left;padding:0.35rem;'>เดือน</th><th style='text-align:right;padding:0.35rem;'>เคส</th>"
        "<th style='text-align:left;padding:0.35rem;'>สถานะ</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _select_denominator(denominator: pd.DataFrame, selected_ym: list, selected_wards: list, all_wards: list, denominator_sheet_found: bool = False) -> tuple[float | None, str | None, pd.DataFrame]:
    """Select monthly totals for the current filters without double-counting."""
    if denominator is None or denominator.empty:
        return None, ('พบแท็บแล้ว แต่ยังไม่มีข้อมูลตัวหาร' if denominator_sheet_found else 'ยังไม่พบแท็บยอดตรวจทั้งหมด'), pd.DataFrame()
    selected = denominator[denominator['year_month'].isin(selected_ym)].copy()
    if selected.empty:
        return None, 'ยังไม่มีตัวหารของเดือนที่เลือก', pd.DataFrame()
    has_ward_rows = selected['ward_standard'].astype(str).str.strip().ne('').any()
    overall = selected[selected['ward_standard'].astype(str).str.strip().eq('')]
    if not has_ward_rows and len(selected_wards) < len(all_wards):
        return None, 'แท็บยอดตรวจทั้งหมดไม่มีข้อมูลแยกตาม Ward', pd.DataFrame()
    if has_ward_rows and len(selected_wards) < len(all_wards):
        selected = selected[selected['ward_standard'].isin(selected_wards)]
        if selected.empty:
            return None, 'แท็บยอดตรวจทั้งหมดไม่มีข้อมูลของ Ward ที่เลือก', pd.DataFrame()
    elif has_ward_rows and not overall.empty:
        # Prefer explicitly supplied monthly totals when viewing all Wards.
        selected = overall
    total = float(selected['total_specimens'].sum())
    return (total if total > 0 else None), None, selected


def render_rejection_rate(
    df_cases: pd.DataFrame,
    denominator: pd.DataFrame,
    selected_ym: list,
    selected_wards: list,
    all_wards: list,
    denominator_sheet_found: bool = False,
):
    """Show rejection rate using optional monthly totals from Google Sheets."""
    st.markdown("""
    <div class="chart-card">
        <div class="chart-title">📉 อัตราการปฏิเสธสิ่งส่งตรวจ (%)</div>
        <div style="font-size:0.82rem;color:#64748B;margin-bottom:0.8rem;">
            คำนวณจาก จำนวนเคสที่ปฏิเสธ ÷ จำนวนสิ่งส่งตรวจทั้งหมด × 100
        </div>
    """, unsafe_allow_html=True)
    total, reason, selected_denominator = _select_denominator(denominator, selected_ym, selected_wards, all_wards, denominator_sheet_found)
    if total is None:
        st.info("ยังคำนวณอัตราการปฏิเสธไม่ได้ เพราะยังไม่มีตัวหารจำนวนสิ่งส่งตรวจทั้งหมด")
        st.caption("กรอกข้อมูลรายเดือนในแท็บ “ยอดตรวจทั้งหมด” แล้วระบบจะซิงก์ให้อัตโนมัติ")
        if reason:
            st.caption(f"สถานะตัวหาร: {reason}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    numerator = int(len(df_cases))
    # A sheet built by counting the rejection tabs is not a valid denominator:
    # it would show a misleading 100% rejection rate. Require total specimens
    # to exceed rejected cases for every displayed month.
    month_den = selected_denominator.groupby(['year_month', 'thai_month_year'], as_index=False)['total_specimens'].sum()
    month_num = df_cases.groupby(['year_month', 'thai_month_year'], as_index=False).size().rename(columns={'size': 'rejected'})
    rate_table = month_den.merge(month_num, on=['year_month', 'thai_month_year'], how='left').fillna({'rejected': 0})
    missing_months = month_num.loc[~month_num['year_month'].isin(month_den['year_month'])]
    invalid_months = rate_table[
        (rate_table['rejected'] > 0) &
        (rate_table['total_specimens'] <= rate_table['rejected'])
    ]
    if not missing_months.empty or not invalid_months.empty or (numerator > 0 and total <= numerator):
        st.warning('ยังแสดงอัตราการปฏิเสธไม่ได้: ตัวหารต้องครอบคลุมทุกเดือนที่มีเคส และยอดตรวจทั้งหมดต้องมากกว่าเคสปฏิเสธ')
        st.caption('โปรดใช้จำนวนสิ่งส่งตรวจทั้งหมดจากระบบห้องปฏิบัติการเป็นตัวหาร; จำนวนแถวในชีทบันทึกการปฏิเสธเป็นเพียงยอดเคสที่ปฏิเสธ')
        st.markdown('</div>', unsafe_allow_html=True)
        return

    rate = numerator / total * 100
    rate_color = '#16A34A' if rate <= 1 else ('#D97706' if rate <= 3 else '#DC2626')
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric('อัตราการปฏิเสธ', f'{rate:.2f}%')
    with c2:
        st.metric('เคสที่ปฏิเสธ', f'{numerator:,}')
    with c3:
        st.metric('สิ่งส่งตรวจทั้งหมด', f'{total:,.0f}')
    st.markdown(f"<div style='color:{rate_color};font-weight:700;margin-top:-0.35rem;'>สถานะ: {'ต่ำ' if rate <= 1 else ('เฝ้าระวัง' if rate <= 3 else 'สูง')} · ตัวหารมาจากแท็บยอดตรวจทั้งหมด</div>", unsafe_allow_html=True)

    # Show monthly rate trend when monthly totals are available.
    rate_table['rate_pct'] = rate_table['rejected'] / rate_table['total_specimens'] * 100
    if not rate_table.empty:
        display_rate = rate_table[['thai_month_year', 'rejected', 'total_specimens', 'rate_pct']].rename(columns={
            'thai_month_year': 'เดือน', 'rejected': 'เคสปฏิเสธ',
            'total_specimens': 'สิ่งส่งตรวจทั้งหมด', 'rate_pct': 'อัตราการปฏิเสธ (%)'
        })
        display_rate['อัตราการปฏิเสธ (%)'] = display_rate['อัตราการปฏิเสธ (%)'].round(2)
        st.dataframe(display_rate, width='stretch', hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_data_quality_check(df_cases: pd.DataFrame, df_causes: pd.DataFrame):
    """Audit dates, duplicate records, Ward mappings, and cause grouping."""
    cases = df_cases.copy()
    causes = df_causes.copy()

    if 'date_valid' in cases.columns:
        invalid_date_mask = ~cases['date_valid'].fillna(False).astype(bool)
    else:
        parsed_dates = pd.to_datetime(cases.get('date'), errors='coerce')
        raw_days = pd.to_numeric(cases.get('day'), errors='coerce')
        max_days = parsed_dates.dt.days_in_month
        invalid_date_mask = parsed_dates.isna() | raw_days.isna() | (raw_days < 1) | (raw_days > max_days) | raw_days.mod(1).ne(0)

    if 'possible_duplicate' in cases.columns:
        duplicate_mask = cases['possible_duplicate'].fillna(False).astype(bool)
    else:
        duplicate_columns = [
            c for c in ['date', 'time', 'hn', 'ward_raw', 'specimen_issue', 'request_issue', 'payment_issue', 'it_issue', 'other_issue']
            if c in cases.columns
        ]
        duplicate_mask = cases.duplicated(subset=duplicate_columns, keep=False) if duplicate_columns else pd.Series(False, index=cases.index)

    unmapped = cleaner.get_unmapped_wards(cases)
    known_categories = set(cleaner.CATEGORY_LABELS.values()) | {'ไม่ระบุสาเหตุชัดเจน'}
    uncategorized_mask = ((~causes['category'].isin(known_categories))
                          | causes['category'].isin(['ไม่ระบุสาเหตุชัดเจน', 'ปัญหาอื่นๆ / รายละเอียดเพิ่มเติม'])
                          | causes['reason'].eq('ไม่ระบุสาเหตุ'))

    quality_items = [
        ('📅 วันที่ผิด/ไม่ครบ', int(invalid_date_mask.sum())),
        ('🧬 ข้อมูลที่อาจซ้ำ', int(duplicate_mask.sum())),
        ('🏥 Ward ใหม่/รอเพิ่ม mapping', int(len(unmapped))),
        ('🧩 สาเหตุยังไม่จัดกลุ่ม', int(uncategorized_mask.sum())),
    ]
    cards = []
    for label, count in quality_items:
        fg, bg, status = ('#166534', '#DCFCE7', 'ผ่าน') if count == 0 else ('#991B1B', '#FEE2E2', 'ต้องตรวจสอบ')
        cards.append(
            f"<div style='border:1px solid #E2E8F0;border-radius:12px;padding:0.75rem;background:#FFFFFF;'>"
            f"<div style='font-size:0.78rem;color:#64748B;'>{label}</div>"
            f"<div style='font-size:1.45rem;font-weight:800;color:{fg};'>{count:,}</div>"
            f"<span style='background:{bg};color:{fg};padding:0.15rem 0.5rem;border-radius:999px;font-size:0.75rem;font-weight:700;'>{status}</span></div>"
        )
    st.markdown("<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:0.7rem;margin:0.7rem 0 1rem;'>" + ''.join(cards) + "</div>", unsafe_allow_html=True)

    if invalid_date_mask.any():
        st.markdown("**📅 รายการวันที่ผิดหรือไม่ครบ**")
        date_cols = [c for c in ['date', 'day', 'time', 'ward_standard', 'source_sheet'] if c in cases.columns]
        st.dataframe(cases.loc[invalid_date_mask, date_cols].head(100), width="stretch", hide_index=True)
    if duplicate_mask.any():
        st.markdown("**🧬 รายการที่อาจซ้ำกัน**")
        dup_cols = [c for c in ['date', 'time', 'ward_standard', 'specimen_issue', 'request_issue', 'other_issue'] if c in cases.columns]
        st.dataframe(cases.loc[duplicate_mask, dup_cols].head(100), width="stretch", hide_index=True)
    if not unmapped.empty:
        st.markdown("**🏥 Ward ที่ควรตรวจและเพิ่มใน mapping**")
        st.dataframe(unmapped, width="stretch", hide_index=True)
    if uncategorized_mask.any():
        st.markdown("**🧩 สาเหตุที่ยังไม่ถูกจัดกลุ่ม**")
        cause_cols = [c for c in ['date', 'ward_standard', 'category', 'reason', 'notes'] if c in causes.columns]
        st.dataframe(causes.loc[uncategorized_mask, cause_cols].head(100), width="stretch", hide_index=True)
    if not any(count > 0 for _, count in quality_items):
        st.success("✅ ไม่พบรายการที่ต้องแก้ไขจากการตรวจคุณภาพข้อมูลรอบนี้")


@st.fragment(run_every="15m")
def refresh_google_data_while_open():
    """Trigger a full refresh for an open dashboard every fifteen minutes."""
    now = time.monotonic()
    next_refresh = st.session_state.setdefault("_next_google_refresh", now + 900)
    if now >= next_refresh:
        st.session_state["_next_google_refresh"] = now + 900
        load_data.clear()
        st.rerun()


# ==============================================================================
# 9. MAIN APPLICATION CONTROLLER
# ==============================================================================

def main():
    # 1. Render Sidebar & retrieve filters
    bundle = render_sidebar()
    
    # 2. Apply filters to dataframes
    df_cases, df_causes = apply_filters(bundle)
    
    # 3. Render Header
    render_header(bundle['df_cases_all'])
    
    # 4. Render Quick Filter Summary Bar
    render_quick_filter_bar(df_cases, bundle)
    
    # 5. Render Top KPI Cards
    render_kpi_cards(df_cases, df_causes, num_months=len(bundle['selected_months_th']))
    
    # 6. Tab Navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 ภาพรวม & แนวโน้ม",
        "🔍 วิเคราะห์สาเหตุเชิงลึก",
        "🏥 เจาะลึกหอผู้ป่วย",
        "📋 ตารางข้อมูล & ส่งออก",
        "🩺 Data Quality Check"
    ])
    
    # --------------------------------------------------------------------------
    # TAB 1: ภาพรวม & แนวโน้ม
    # --------------------------------------------------------------------------
    with tab1:
        # ROW 1: Monthly Trend (65%) + Category Donut (35%)
        col_trend, col_donut = st.columns([13, 7])
        with col_trend:
            st.markdown("""
            <div class="chart-card">
                <div class="chart-title">📈 แนวโน้มจำนวนสิ่งส่งตรวจที่ถูกปฏิเสธรายเดือน (Monthly Trend)</div>
            """, unsafe_allow_html=True)
            render_monthly_trend(df_cases)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_donut:
            st.markdown("""
            <div class="chart-card">
                <div class="chart-title">🍩 สัดส่วนกลุ่มสาเหตุการปฏิเสธ (Categories)</div>
            """, unsafe_allow_html=True)
            render_category_donut(df_causes)
            st.markdown("</div>", unsafe_allow_html=True)

        # ROW 2: Fiscal-year comparison
        st.markdown("""
        <div class="chart-card">
            <div class="chart-title">📅 เปรียบเทียบจำนวนเคสตามปีงบประมาณ</div>
            <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 0.8rem;">
                ใช้ดูภาพรวมระหว่างปีงบประมาณที่เลือก และจะเพิ่มปีใหม่ให้อัตโนมัติเมื่อมีข้อมูลเข้ามา
            </div>
        """, unsafe_allow_html=True)
        render_fiscal_year_comparison(df_cases)
        st.markdown("</div>", unsafe_allow_html=True)

        render_quality_target(df_cases)
        render_rejection_rate(
            df_cases,
            bundle['denominator'],
            bundle['selected_ym'],
            bundle['selected_wards'],
            bundle['all_wards'],
            bundle['denominator_sheet_found'],
        )
            
        # ROW 4: Top 10 Wards (50%) + Top 10 Root Causes (50%)
        col_w, col_r = st.columns([1, 1])
        with col_w:
            st.markdown("""
            <div class="chart-card">
                <div class="chart-title">🏆 Top 10 หอผู้ป่วยที่มีการปฏิเสธสิ่งส่งตรวจสูงสุด</div>
            """, unsafe_allow_html=True)
            render_top_wards_chart(df_cases)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_r:
            st.markdown("""
            <div class="chart-card">
                <div class="chart-title">⚠️ Top 10 สาเหตุย่อยที่มีการปฏิเสธสูงสุด (Root Causes)</div>
            """, unsafe_allow_html=True)
            render_top_root_causes_chart(df_causes)
            st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB 2: วิเคราะห์สาเหตุเชิงลึก
    # --------------------------------------------------------------------------
    with tab2:
        st.markdown("""
        <div class="chart-card">
            <div class="chart-title">📊 Pareto สาเหตุการปฏิเสธ (80/20)</div>
            <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 0.8rem;">
                เรียงสาเหตุจากพบบ่อยที่สุด พร้อมเส้นเปอร์เซ็นต์สะสมเพื่อช่วยจัดลำดับการแก้ไข
            </div>
        """, unsafe_allow_html=True)
        if not df_causes.empty:
            pareto_all = (
                df_causes.groupby('reason').size().reset_index(name='count')
                .sort_values('count', ascending=False)
            )
            all_cumulative = pareto_all['count'].cumsum() / pareto_all['count'].sum()
            causes_to_80 = int((all_cumulative < 0.8).sum() + 1)
            pareto = pareto_all.head(max(15, causes_to_80)).copy()
            pareto['cumulative_pct'] = pareto['count'].cumsum() / pareto_all['count'].sum() * 100
            st.caption(f"สาเหตุ {causes_to_80:,} อันดับแรกคิดเป็นอย่างน้อย 80% ของทั้งหมด")
            fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
            fig_pareto.add_trace(
                go.Bar(x=pareto['reason'], y=pareto['count'], name='จำนวนครั้ง', marker_color='#6c5070'),
                secondary_y=False,
            )
            fig_pareto.add_trace(
                go.Scatter(x=pareto['reason'], y=pareto['cumulative_pct'], name='% สะสม', mode='lines+markers', line=dict(color='#df6a6a', width=3)),
                secondary_y=True,
            )
            fig_pareto.update_yaxes(title_text='จำนวนครั้ง', secondary_y=False, gridcolor='#F1F5F9')
            fig_pareto.update_yaxes(title_text='เปอร์เซ็นต์สะสม', range=[0, 105], secondary_y=True, ticksuffix='%')
            fig_pareto.add_hline(y=80, line_dash='dash', line_color='#94A3B8', secondary_y=True)
            fig_pareto.update_layout(height=500, margin=dict(l=20, r=20, t=20, b=170), plot_bgcolor='rgba(0,0,0,0)', font=dict(family='Noto Sans Thai', size=11), xaxis=dict(tickangle=-50, title='', automargin=True))
            st.plotly_chart(fig_pareto, width="stretch")
        else:
            st.info("ไม่มีข้อมูลสำหรับสร้าง Pareto")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""
        <div class="chart-card">
            <div class="chart-title">🧩 ความสัมพันธ์ระหว่าง หอผู้ป่วย (Ward) x กลุ่มสาเหตุการปฏิเสธ (Heatmap Matrix)</div>
            <div style="font-size: 0.82rem; color: #64748B; margin-bottom: 0.8rem;">
                วิเคราะห์ Cross-tabulation เพื่อค้นหาจุดบกพร่องเฉพาะของแต่ละหอผู้ป่วย ช่วยให้ทีมควบคุมคุณภาพ (CQI) เจาะจงแก้ปัญหาได้ตรงจุด
            </div>
        """, unsafe_allow_html=True)
        
        top_n_matrix = st.slider("จำนวนหอผู้ป่วยใน Matrix:", min_value=5, max_value=25, value=12, step=1)
        ct_matrix = cleaner.get_ward_cause_crosstab(df_causes, top_wards_n=top_n_matrix)
        
        if not ct_matrix.empty:
            fig_hm = px.imshow(
                ct_matrix,
                labels=dict(x="กลุ่มสาเหตุการปฏิเสธ", y="หอผู้ป่วย (Ward)", color="จำนวนครั้ง"),
                x=ct_matrix.columns,
                y=ct_matrix.index,
                text_auto=True,
                color_continuous_scale="Blues",
                aspect="auto"
            )
            fig_hm.update_layout(
                height=440,
                margin=dict(l=20, r=20, t=20, b=20),
                font=dict(family="Noto Sans Thai", size=11)
            )
            st.plotly_chart(fig_hm, width="stretch")
        else:
            st.info("ไม่มีข้อมูลสำหรับสร้าง Matrix")
        st.markdown("</div>", unsafe_allow_html=True)
        
        col_tree, col_inc = st.columns([13, 11])
        with col_tree:
            st.markdown("""
            <div class="chart-card">
                <div class="chart-title">🌳 ลำดับชั้นสาเหตุการปฏิเสธ (Treemap: กลุ่มปัญหา ➔ สาเหตุย่อย)</div>
            """, unsafe_allow_html=True)
            if not df_causes.empty:
                df_tree = df_causes.groupby(['category', 'reason']).size().reset_index(name='count')
                fig_tree = px.treemap(
                    df_tree,
                    path=['category', 'reason'],
                    values='count',
                    color='category',
                    color_discrete_map={
                        'ปัญหาด้านสิ่งส่งตรวจ': '#6c5070',
                        'ปัญหาด้านใบส่งตรวจ': '#F4C400',
                        'ปัญหาด้านระบบการเงิน': '#c2dbc1',
                        'ปัญหาด้านระบบสารสนเทศ': '#C43B8A',
                        'ปัญหาอื่นๆ / รายละเอียดเพิ่มเติม': '#E94B3C'
                    }
                )
                fig_tree.update_layout(height=360, margin=dict(l=5, r=5, t=5, b=5), font=dict(family="Noto Sans Thai"))
                st.plotly_chart(fig_tree, width="stretch")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_inc:
            st.markdown("""
            <div class="chart-card">
                <div class="chart-title">🚨 เคสอุบัติการณ์ความเสี่ยง (Incident Monitoring)</div>
            """, unsafe_allow_html=True)
            df_incidents = df_cases[df_cases['is_incident']].copy()
            st.markdown(f"<div style='font-size: 0.85rem; color: #DC2626; font-weight: 600; margin-bottom: 0.5rem;'>พบทั้งหมด {len(df_incidents)} เคสความเสี่ยงสูง</div>", unsafe_allow_html=True)
            if not df_incidents.empty:
                inc_show = df_incidents[['date', 'hn', 'ward_standard', 'specimen_issue', 'request_issue', 'other_issue', 'resolution']].rename(columns={
                    'date': 'วันที่', 'hn': 'HN', 'ward_standard': 'Ward', 'specimen_issue': 'สิ่งส่งตรวจ',
                    'request_issue': 'ใบส่งตรวจ', 'other_issue': 'หมายเหตุ', 'resolution': 'การแก้ไข'
                })
                st.dataframe(inc_show, height=270, width="stretch", hide_index=True)
            else:
                st.success("🎉 ไม่พบเคสอุบัติการณ์ความเสี่ยงในช่วงตัวกรองนี้")
            st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB 3: เจาะลึกหอผู้ป่วย
    # --------------------------------------------------------------------------
    with tab3:
        unique_wards = sorted(df_cases['ward_standard'].unique().tolist())
        if unique_wards:
            sel_target_ward = st.selectbox(
                "🏥 เลือกหอผู้ป่วยเพื่อเจาะลึกการวิเคราะห์:",
                options=unique_wards,
                index=0
            )
            
            w_cases = df_cases[df_cases['ward_standard'] == sel_target_ward]
            w_causes = df_causes[df_causes['ward_standard'] == sel_target_ward]
            
            all_ward_ranks = df_cases['ward_standard'].value_counts()
            rank_idx = list(all_ward_ranks.index).index(sel_target_ward) + 1 if sel_target_ward in all_ward_ranks.index else '-'
            top_w_cause = w_causes['reason'].value_counts().index[0] if not w_causes.empty else '-'
            w_res_count = w_cases['resolution'].str.contains('แก้ไขแล้ว|ยกเลิก', na=False).sum()
            w_res_rate = round((w_res_count / max(1, len(w_cases))) * 100, 1)
            
            # Ward mini KPIs
            wk1, wk2, wk3, wk4 = st.columns(4)
            with wk1:
                st.metric("จำนวนเคสที่ปฏิเสธ", f"{len(w_cases)} ครั้ง")
            with wk2:
                st.metric("อันดับในโรงพยาบาล", f"อันดับที่ {rank_idx}", help=f"จากทั้งหมด {len(all_ward_ranks)} หอผู้ป่วย")
            with wk3:
                st.metric("สาเหตุอันดับ 1", top_w_cause[:20] + ('...' if len(top_w_cause) > 20 else ''))
            with wk4:
                st.metric("อัตราการแก้ไขสำเร็จ", f"{w_res_rate}%")
                
            col_wm1, col_wm2 = st.columns(2)
            with col_wm1:
                st.markdown(f"<div class='chart-card'><div class='chart-title'>📊 แนวโน้มรายเดือน: {sel_target_ward}</div>", unsafe_allow_html=True)
                w_trend = cleaner.get_monthly_trend(w_cases)
                if not w_trend.empty:
                    fig_wt = px.bar(w_trend, x='thai_month_year', y='count', text='count', color_discrete_sequence=['#6c5070'])
                    fig_wt.update_traces(textposition='outside', marker=dict(cornerradius=4))
                    fig_wt.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(title=""), yaxis=dict(title="จำนวนเคส", gridcolor='#F1F5F9'))
                    st.plotly_chart(fig_wt, width="stretch")
                else:
                    st.info("ไม่มีข้อมูลแนวโน้ม")
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col_wm2:
                st.markdown(f"<div class='chart-card'><div class='chart-title'>⚠️ สาเหตุหลักที่พบใน {sel_target_ward}</div>", unsafe_allow_html=True)
                w_top_causes = cleaner.get_top_reasons(w_causes, top_n=6)
                if not w_top_causes.empty:
                    fig_wc = px.bar(w_top_causes.sort_values('count', ascending=True), x='count', y='reason', orientation='h', text='count', color='category', color_discrete_sequence=['#6c5070', '#df6a6a', '#c2dbc1', '#d8a6b5'])
                    fig_wc.update_traces(textposition='outside', marker=dict(cornerradius=4))
                    fig_wc.update_layout(height=260, margin=dict(l=10, r=20, t=10, b=10), plot_bgcolor='rgba(0,0,0,0)', showlegend=False, xaxis=dict(title="ความถี่"), yaxis=dict(title=""))
                    st.plotly_chart(fig_wc, width="stretch")
                else:
                    st.info("ไม่มีข้อมูลสาเหตุ")
                st.markdown("</div>", unsafe_allow_html=True)
                
            st.markdown(f"**📝 รายการบันทึกของ {sel_target_ward}**")
            w_disp = w_cases[['date', 'time', 'hn', 'specimen_issue', 'request_issue', 'payment_issue', 'other_issue', 'resolution', 'supervisor']].rename(columns={
                'date': 'วันที่', 'time': 'เวลา', 'hn': 'HN', 'specimen_issue': 'สิ่งส่งตรวจ',
                'request_issue': 'ใบส่งตรวจ', 'payment_issue': 'การเงิน', 'other_issue': 'รายละเอียด',
                'resolution': 'การแก้ไข', 'supervisor': 'หัวหน้างาน'
            })
            st.dataframe(w_disp, width="stretch", hide_index=True)
        else:
            st.info("ไม่มีข้อมูลหอผู้ป่วยตามตัวกรอง")

    # --------------------------------------------------------------------------
    # TAB 4: ตารางข้อมูล & ส่งออก
    # --------------------------------------------------------------------------
    with tab4:
        st.markdown("<div class='chart-card'><div class='chart-title'>📋 ตารางข้อมูลรายงานการปฏิเสธสิ่งส่งตรวจ (Cleaned Dataset)</div>", unsafe_allow_html=True)
        
        tc1, tc2 = st.columns([3, 2])
        with tc1:
            q_search = st.text_input("🔍 ค้นหา (HN, Ward, หรือสาเหตุ):", "", placeholder="พิมพ์เพื่อค้นหาข้อมูลในตาราง...")
        with tc2:
            tbl_view = st.radio("มุมมองตาราง:", ["ระดับเคสผู้ป่วย (Case-Level)", "ระดับสาเหตุ (Tidy / Cause-Level)"], horizontal=True)
            
        if tbl_view == "ระดับเคสผู้ป่วย (Case-Level)":
            df_export = df_cases.copy()
            if q_search:
                q = q_search.lower()
                m = (
                    df_export['hn'].astype(str).str.lower().str.contains(q) |
                    df_export['ward_standard'].astype(str).str.lower().str.contains(q) |
                    df_export['specimen_issue'].astype(str).str.lower().str.contains(q) |
                    df_export['request_issue'].astype(str).str.lower().str.contains(q) |
                    df_export['other_issue'].astype(str).str.lower().str.contains(q)
                )
                df_export = df_export[m]
                
            st.caption(f"แสดงข้อมูลทั้งหมด **{len(df_export):,}** เคส")
            cols_show = ['case_id', 'date', 'time', 'hn', 'ward_standard', 'ward_group', 'specimen_type', 'specimen_issue', 'request_issue', 'payment_issue', 'other_issue', 'resolution', 'supervisor']
            rename_c = {
                'case_id': 'รหัสเคส', 'date': 'วันที่', 'time': 'เวลา', 'hn': 'HN',
                'ward_standard': 'Ward มาตรฐาน', 'ward_group': 'กลุ่มแผนก',
                'specimen_type': 'สิ่งส่งตรวจ', 'specimen_issue': 'ปัญหาด้านสิ่งส่งตรวจ',
                'request_issue': 'ปัญหาด้านใบส่งตรวจ', 'payment_issue': 'ปัญหาการเงิน',
                'other_issue': 'รายละเอียด', 'resolution': 'การแก้ไข', 'supervisor': 'หัวหน้างาน'
            }
            st.dataframe(df_export[cols_show].rename(columns=rename_c), height=420, width="stretch", hide_index=True)
        else:
            df_export = df_causes.copy()
            if q_search:
                q = q_search.lower()
                m = (
                    df_export['hn'].astype(str).str.lower().str.contains(q) |
                    df_export['ward_standard'].astype(str).str.lower().str.contains(q) |
                    df_export['category'].astype(str).str.lower().str.contains(q) |
                    df_export['reason'].astype(str).str.lower().str.contains(q)
                )
                df_export = df_export[m]
                
            st.caption(f"แสดงข้อมูลสาเหตุทั้งหมด **{len(df_export):,}** รายการ (Tidy Format)")
            cols_show = ['case_id', 'date', 'hn', 'ward_standard', 'ward_group', 'specimen_type', 'category', 'reason', 'notes', 'resolution']
            rename_c = {
                'case_id': 'รหัสเคส', 'date': 'วันที่', 'hn': 'HN',
                'ward_standard': 'Ward มาตรฐาน', 'ward_group': 'กลุ่มแผนก',
                'specimen_type': 'สิ่งส่งตรวจ', 'category': 'กลุ่มปัญหา',
                'reason': 'รายละเอียดสาเหตุ', 'notes': 'หมายเหตุ', 'resolution': 'การแก้ไข'
            }
            st.dataframe(df_export[cols_show].rename(columns=rename_c), height=420, width="stretch", hide_index=True)

        col_b1, col_b2, _ = st.columns([1, 1, 2])
        with col_b1:
            csv_bytes = df_export.to_csv(index=False, encoding='utf-8-sig')
            st.download_button("📥 ดาวน์โหลด CSV (.csv)", data=csv_bytes, file_name="specimen_rejections_cleaned.csv", mime="text/csv", width="stretch")
        with col_b2:
            xl_buf = io.BytesIO()
            with pd.ExcelWriter(xl_buf, engine='openpyxl') as wr:
                df_export.to_excel(wr, index=False, sheet_name='Cleaned')
            st.download_button("📥 ดาวน์โหลด Excel (.xlsx)", data=xl_buf.getvalue(), file_name="specimen_rejections_cleaned.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
            
        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # TAB 5: ตรวจสอบคุณภาพข้อมูล
    # --------------------------------------------------------------------------
    with tab5:
        st.markdown("<div class='chart-card'><div class='chart-title'>🩺 Data Quality Check · ตรวจสอบคุณภาพข้อมูล</div>", unsafe_allow_html=True)
        st.caption("ตรวจชื่อ Ward ใหม่ วันที่ผิด ข้อมูลที่อาจซ้ำ และสาเหตุที่ยังไม่ชัดเจนหรืออยู่ในกลุ่มอื่น ๆ จากข้อมูลทั้งหมดที่เชื่อมอยู่")
        render_data_quality_check(bundle['df_cases_all'], bundle['df_causes_all'])

        st.markdown("<hr style='margin:1.2rem 0;border:none;border-top:1px solid #E2E8F0;'>", unsafe_allow_html=True)
        st.markdown("**🩺 ตรวจสอบความถูกต้องของชื่อหอผู้ป่วย (Ward Mapping Audit)**")
        unmapped = cleaner.get_unmapped_wards(bundle['df_cases_all'])
        raw_ward_count = bundle['df_cases_all']['ward_raw'].nunique()
        mapping_coverage = (raw_ward_count - len(unmapped)) / raw_ward_count * 100 if raw_ward_count else 100.0
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("จำนวนชื่อ Ward ดิบทั้งหมดในไฟล์", f"{raw_ward_count:,} รูปแบบ")
        with m2:
            st.metric("อัตราการจับคู่ชื่อมาตรฐาน (Coverage)", f"{mapping_coverage:.1f}%", help="สัดส่วนชื่อ Ward ที่พบตรงในพจนานุกรมชื่อมาตรฐาน")
        with m3:
            st.metric("ชื่อที่ไม่รู้จัก (Unmapped)", f"{len(unmapped)} รายการ")
            
        if len(unmapped) == 0:
            st.success("✅ สมบูรณ์แบบ 100%! ชื่อหอผู้ป่วยทุกรูปแบบในไฟล์ถูกจับคู่เข้าสู่ชื่อทางการของโรงพยาบาลเรียบร้อยแล้ว")
        else:
            st.warning(f"ตรวจพบ {len(unmapped)} รายการที่ใช้ heuristic fallback")
            st.dataframe(unmapped, width="stretch", hide_index=True)
            
        with st.expander("📖 เปิดดูพจนานุกรมชื่อมาตรฐานของหอผู้ป่วยทั้งหมด (Ward Standardization Reference Dictionary)"):
            ref_rows = []
            for raw_w, std_w in sorted(cleaner.WARD_MAPPING.items()):
                grp = cleaner.WARD_GROUPS.get(std_w, 'อื่น ๆ')
                ref_rows.append({'ชื่อเดิม / ตัวย่อ': raw_w, 'ชื่อมาตรฐาน': std_w, 'กลุ่มแผนกหลัก': grp})
            st.dataframe(pd.DataFrame(ref_rows), width="stretch", height=350, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
    refresh_google_data_while_open()
