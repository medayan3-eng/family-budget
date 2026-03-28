# app.py  –  לוח בקרה ראשי
import sys, os
from pathlib import Path

# --- Robust path fix for Streamlit Cloud + local ---
def _add_root():
    candidates = [
        Path(__file__).resolve().parent,           # standard
        Path(os.path.abspath(__file__)).parent,     # fallback abs
        Path("/mount/src/family-budget"),           # Streamlit Cloud explicit
        Path.cwd(),                                 # current working dir
    ]
    for p in candidates:
        if (p / "utils" / "data_manager.py").exists():
            s = str(p)
            if s not in sys.path:
                sys.path.insert(0, s)
            os.chdir(p)
            return
_add_root()

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from utils.data_manager import DataManager
from utils.price_fetcher import fetch_all_prices, get_usd_ils_rate
from utils.constants import EXPENSE_CATEGORIES

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="תוכנית חיסכון משפחתית",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

RTL_CSS = """
<style>
    /* RTL global */
    html, body, [class*="css"] { direction: rtl; }
    .stApp { direction: rtl; }
    .block-container { direction: rtl; }
    section[data-testid="stSidebar"] { direction: rtl; }
    /* Metric deltas */
    [data-testid="stMetricDelta"] svg { display: none; }
    /* Inputs */
    input, textarea, select { direction: rtl !important; text-align: right !important; }
    /* DataFrames */
    .stDataFrame { direction: rtl; }
    /* Hide streamlit branding */
    #MainMenu, footer { visibility: hidden; }
    /* Sidebar nav labels */
    .css-1d391kg, [data-testid="stSidebarNav"] a span { direction: rtl; }
    /* Card style */
    .summary-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
        border-radius: 16px;
        padding: 20px 24px;
        color: white;
        margin-bottom: 8px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }
    .summary-card .label { font-size: 0.85rem; opacity: 0.75; margin-bottom: 4px; }
    .summary-card .value { font-size: 1.9rem; font-weight: 700; letter-spacing: -0.5px; }
    .summary-card .delta { font-size: 0.82rem; margin-top: 4px; opacity: 0.85; }
    .positive { color: #4ade80; }
    .negative { color: #f87171; }
    .neutral  { color: #93c5fd; }
</style>
"""
st.markdown(RTL_CSS, unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_resource
def get_dm():
    return DataManager()

def ils(amount: float) -> str:
    return f"₪{amount:,.0f}"

def pct(p: float) -> str:
    sign = "+" if p >= 0 else ""
    return f"{sign}{p:.1f}%"

def card(label, value, delta="", delta_class="neutral"):
    return f"""
    <div class="summary-card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        {"<div class='delta " + delta_class + "'>" + delta + "</div>" if delta else ""}
    </div>"""


# ── Main ──────────────────────────────────────────────────────────────────────

dm = get_dm()
now = datetime.now()
year, month = now.year, now.month
month_names = {1:"ינואר",2:"פברואר",3:"מרץ",4:"אפריל",5:"מאי",6:"יוני",
               7:"יולי",8:"אוגוסט",9:"ספטמבר",10:"אוקטובר",11:"נובמבר",12:"דצמבר"}

st.title("💰 תוכנית חיסכון משפחתית")
st.caption(f"לוח בקרה | {month_names[month]} {year}")

# ── Sidebar month selector ────────────────────────────────────────────────────
with st.sidebar:
    st.header("📅 בחר חודש")
    all_ym = dm.get_all_years_months()
    if (year, month) not in all_ym:
        all_ym.insert(0, (year, month))

    ym_options = [f"{month_names[m]} {y}" for y, m in all_ym]
    ym_label   = f"{month_names[month]} {year}"
    sel_idx    = ym_options.index(ym_label) if ym_label in ym_options else 0
    selected   = st.selectbox("חודש", ym_options, index=sel_idx, label_visibility="collapsed")
    sel_y, sel_m = all_ym[ym_options.index(selected)]

    st.divider()
    st.info("📌 עדכון מחירים פעם ביום בפתיחה ראשונה")

# ── Data loading ──────────────────────────────────────────────────────────────
with st.spinner("טוען נתונים ומחירים..."):
    investments  = dm.get_investments()
    usd_ils      = get_usd_ils_rate()
    prices       = fetch_all_prices(investments, dm)
    income_list  = dm.get_income(year=sel_y, month=sel_m)
    expense_list = dm.get_expenses(year=sel_y, month=sel_m)

# ── Portfolio calculations ────────────────────────────────────────────────────
total_value_ils = 0.0
total_cost_ils  = 0.0

for inv in investments:
    pd_  = prices.get(inv["id"])
    if not pd_:
        continue
    units  = float(inv.get("units", 0))
    cur_px = float(pd_.get("price", 0))
    ccy    = pd_.get("currency", "ILS")
    mul    = usd_ils if ccy == "USD" else 1.0
    total_value_ils += cur_px * units * mul

    avg_px = float(inv.get("purchase_price", 0))
    total_cost_ils  += avg_px * units * mul

gain_ils = total_value_ils - total_cost_ils
gain_pct = (gain_ils / total_cost_ils * 100) if total_cost_ils > 0 else 0.0

# ── Income / Expense calculations ────────────────────────────────────────────
total_income   = sum(e["amount"] for e in income_list)
total_expenses = sum(e["amount"] for e in expense_list)
monthly_saving = total_income - total_expenses
saving_rate    = (monthly_saving / total_income * 100) if total_income > 0 else 0.0

# ── Top metric cards ──────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

with c1:
    delta_cls = "positive" if gain_ils >= 0 else "negative"
    st.markdown(card(
        "💼 שווי תיק השקעות",
        ils(total_value_ils),
        f"רווח/הפסד: {ils(gain_ils)} ({pct(gain_pct)})",
        delta_cls,
    ), unsafe_allow_html=True)

with c2:
    st.markdown(card(
        "📥 הכנסות חודשיות",
        ils(total_income),
        f"{month_names[sel_m]} {sel_y}",
    ), unsafe_allow_html=True)

with c3:
    st.markdown(card(
        "📤 הוצאות חודשיות",
        ils(total_expenses),
        f"מתוך הכנסה: {pct(total_expenses/total_income*100) if total_income else '—'}",
        "negative" if total_expenses > total_income else "neutral",
    ), unsafe_allow_html=True)

with c4:
    cls = "positive" if monthly_saving >= 0 else "negative"
    st.markdown(card(
        "💰 חיסכון חודשי",
        ils(monthly_saving),
        f"שיעור חיסכון: {pct(saving_rate)}" if total_income else "הוסף נתונים",
        cls,
    ), unsafe_allow_html=True)

st.divider()

# ── Charts row ────────────────────────────────────────────────────────────────
col_l, col_r = st.columns([1, 1])

with col_l:
    st.subheader("📊 הרכב תיק ההשקעות")
    if investments and prices:
        pie_rows = []
        for inv in investments:
            pd_ = prices.get(inv["id"])
            if not pd_:
                continue
            units  = float(inv.get("units", 0))
            cur_px = float(pd_.get("price", 0))
            ccy    = pd_.get("currency", "ILS")
            mul    = usd_ils if ccy == "USD" else 1.0
            val    = cur_px * units * mul
            pie_rows.append({
                "שם": inv.get("name") or inv.get("ticker") or inv.get("fund_id", "—"),
                "שווי": val,
            })
        if pie_rows:
            df_pie = pd.DataFrame(pie_rows)
            fig = px.pie(
                df_pie, values="שווי", names="שם",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Blues_r,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                margin=dict(t=20, b=20, l=10, r=10),
                legend=dict(orientation="h", y=-0.15),
                height=340,
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("הוסף השקעות בדף 'השקעות' כדי לראות פיצול")

with col_r:
    st.subheader("🧾 הוצאות לפי קטגוריה")
    if expense_list:
        cat_totals: dict = {}
        for e in expense_list:
            cat = e.get("category", "📦 שונות")
            cat_totals[cat] = cat_totals.get(cat, 0) + e["amount"]
        df_cat = pd.DataFrame(
            sorted(cat_totals.items(), key=lambda x: x[1], reverse=True),
            columns=["קטגוריה", "סכום"]
        )
        fig2 = px.bar(
            df_cat, y="קטגוריה", x="סכום", orientation="h",
            color="סכום",
            color_continuous_scale="Blues",
            text="סכום",
        )
        fig2.update_traces(texttemplate="₪%{text:,.0f}", textposition="outside")
        fig2.update_layout(
            margin=dict(t=20, b=20, l=10, r=60),
            coloraxis_showscale=False,
            height=340,
            xaxis_title="",
            yaxis_title="",
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("הוסף הוצאות בדף 'הוצאות' כדי לראות פיצול")

# ── Historical savings chart ──────────────────────────────────────────────────
all_ym_data = dm.get_all_years_months()
if len(all_ym_data) > 1:
    st.subheader("📈 היסטוריית חיסכון חודשית")
    rows = []
    for y, m in sorted(all_ym_data):
        inc = sum(e["amount"] for e in dm.get_income(year=y, month=m))
        exp = sum(e["amount"] for e in dm.get_expenses(year=y, month=m))
        rows.append({"חודש": f"{month_names[m][:3]} {y}", "הכנסות": inc,
                     "הוצאות": exp, "חיסכון": inc - exp})
    df_hist = pd.DataFrame(rows)
    fig3 = go.Figure()
    fig3.add_bar(x=df_hist["חודש"], y=df_hist["הכנסות"], name="הכנסות",
                 marker_color="#3b82f6")
    fig3.add_bar(x=df_hist["חודש"], y=df_hist["הוצאות"], name="הוצאות",
                 marker_color="#ef4444")
    fig3.add_scatter(x=df_hist["חודש"], y=df_hist["חיסכון"], name="חיסכון",
                     mode="lines+markers", line=dict(color="#22c55e", width=2.5),
                     marker=dict(size=7))
    fig3.update_layout(barmode="group", height=320,
                       legend=dict(orientation="h", y=1.1),
                       margin=dict(t=20, b=20))
    st.plotly_chart(fig3, use_container_width=True)

# ── Recent transactions ───────────────────────────────────────────────────────
st.subheader("📋 פעולות אחרונות")
recent = []
for e in expense_list:
    recent.append({"סוג": "📤 הוצאה", "תיאור": e.get("description", ""),
                   "קטגוריה": e.get("category", ""), "סכום": e["amount"],
                   "תאריך": e.get("date", "")})
for e in income_list:
    recent.append({"סוג": "📥 הכנסה", "תיאור": e.get("description", ""),
                   "קטגוריה": e.get("category", ""), "סכום": e["amount"],
                   "תאריך": e.get("date", "")})

if recent:
    df_recent = (
        pd.DataFrame(recent)
        .sort_values("תאריך", ascending=False)
        .head(15)
        .reset_index(drop=True)
    )
    df_recent["סכום"] = df_recent["סכום"].apply(lambda x: f"₪{x:,.0f}")
    st.dataframe(df_recent, use_container_width=True, hide_index=True)
else:
    st.info("עדיין אין פעולות לחודש זה. עבור לדפים 'הכנסות' ו-'הוצאות' כדי להתחיל.")
