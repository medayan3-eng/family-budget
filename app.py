# ── SHARED: constants ────────────────────────────────────────────────────────
EXPENSE_CATEGORIES = {
    "🏠 דיור": ["שכר דירה","ארנונה","חשמל","מים","גז","ועד בית","אינטרנט","כבלים/OTT","תיקונים","ריהוט"],
    "🛒 מזון": ["סופרמרקט","מסעדות","בתי קפה","משלוחים","שוק/ירקן"],
    "👶 תינוקת": ["חיתולים","ביגוד לתינוקת","צעצועים","רפואה לתינוקת","מטפלת/מעון","שונות"],
    "🚗 תחבורה": ["דלק","ביטוח רכב","טיפול רכב","חניה ודוחות","תחבורה ציבורית","מוניות"],
    "👕 ביגוד": ["ביגוד - אישה","ביגוד - גבר","נעליים","אביזרים"],
    "💊 בריאות": ["תרופות","רופא/מרפאה","ביטוח משלים","אופטיקה","דנטיסט","פיזיותרפיה"],
    "🎬 פנאי": ["בילויים","נסיעות","ספורט","קולנוע","מנויים"],
    "📚 חינוך": ["קורסים","ספרים","לימודים"],
    "🎁 מתנות": ["מתנות","אירועים","תרומות"],
    "📦 שונות": ["ניקיון","היגיינה","קניות כלליות","אחר"],
}
INCOME_CATEGORIES = ["💼 משכורת","🤱 דמי לידה / ביטוח לאומי","🎯 בונוס","📈 הכנסה פסיבית","🏠 הכנסה מנכס","💰 אחר"]
ASSET_TYPES = {"us_stock":"📈 מניה אמריקאית","tase_stock":"🇮🇱 מניה ישראלית","israeli_fund":"📊 קרן נאמנות","manual":"✏️ ידני"}
MONTH_NAMES = {1:"ינואר",2:"פברואר",3:"מרץ",4:"אפריל",5:"מאי",6:"יוני",7:"יולי",8:"אוגוסט",9:"ספטמבר",10:"אוקטובר",11:"נובמבר",12:"דצמבר"}

# ── SHARED: DataManager ───────────────────────────────────────────────────────
import json, uuid, os
from pathlib import Path
from datetime import datetime
from typing import Optional, List

def _get_data_dir():
    # Try writable locations in order
    for candidate in [
        Path(os.environ.get("HOME", "/tmp")) / "family_budget_data",
        Path("/tmp/family_budget_data"),
    ]:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test = candidate / ".test"
            test.write_text("ok"); test.unlink()
            return candidate
        except Exception:
            continue
    return Path("/tmp/family_budget_data")

_DATA_DIR = _get_data_dir()

def _load_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_file(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _init(path: Path, default: dict):
    if not path.exists():
        _save_file(path, default)

_PORTFOLIO = _DATA_DIR / "portfolio.json"
_INCOME    = _DATA_DIR / "income.json"
_EXPENSES  = _DATA_DIR / "expenses.json"
_CACHE     = _DATA_DIR / "prices_cache.json"
for _f, _d in [(_PORTFOLIO,{"investments":[]}),(_INCOME,{"entries":[]}),(_EXPENSES,{"entries":[]}),(_CACHE,{"prices":{},"updated":{}})]:
    _init(_f, _d)

def get_investments():
    return _load_file(_PORTFOLIO).get("investments", [])

def add_investment(inv: dict):
    data = _load_file(_PORTFOLIO)
    inv["id"] = str(uuid.uuid4()); inv["added_date"] = datetime.now().isoformat()
    data.setdefault("investments",[]).append(inv)
    _save_file(_PORTFOLIO, data)

def remove_investment(inv_id: str):
    data = _load_file(_PORTFOLIO)
    data["investments"] = [i for i in data.get("investments",[]) if i["id"] != inv_id]
    _save_file(_PORTFOLIO, data)

def get_income(year=None, month=None):
    e = _load_file(_INCOME).get("entries", [])
    if year:  e = [x for x in e if x.get("year")  == year]
    if month: e = [x for x in e if x.get("month") == month]
    return e

def add_income(entry: dict):
    data = _load_file(_INCOME); entry["id"] = str(uuid.uuid4())
    data.setdefault("entries",[]).append(entry); _save_file(_INCOME, data)

def remove_income(eid: str):
    data = _load_file(_INCOME)
    data["entries"] = [e for e in data.get("entries",[]) if e.get("id") != eid]
    _save_file(_INCOME, data)

def get_expenses(year=None, month=None):
    e = _load_file(_EXPENSES).get("entries", [])
    if year:  e = [x for x in e if x.get("year")  == year]
    if month: e = [x for x in e if x.get("month") == month]
    return e

def add_expense(entry: dict):
    data = _load_file(_EXPENSES); entry["id"] = str(uuid.uuid4())
    data.setdefault("entries",[]).append(entry); _save_file(_EXPENSES, data)

def remove_expense(eid: str):
    data = _load_file(_EXPENSES)
    data["entries"] = [e for e in data.get("entries",[]) if e.get("id") != eid]
    _save_file(_EXPENSES, data)

def get_all_years_months():
    inc = _load_file(_INCOME).get("entries",[])
    exp = _load_file(_EXPENSES).get("entries",[])
    ym = set()
    for e in inc + exp:
        if "year" in e and "month" in e: ym.add((e["year"], e["month"]))
    return sorted(ym, reverse=True)

def is_price_fresh(key: str) -> bool:
    cache = _load_file(_CACHE)
    p = cache.get("prices",{}).get(key)
    return bool(p and p.get("date") == datetime.now().strftime("%Y-%m-%d"))

def get_cached_price(key: str):
    return _load_file(_CACHE).get("prices",{}).get(key)

def set_cached_price(key: str, price_data: dict):
    cache = _load_file(_CACHE)
    cache.setdefault("prices",{})[key] = price_data
    cache.setdefault("updated",{})[key] = datetime.now().isoformat()
    _save_file(_CACHE, cache)

# ── SHARED: Price fetcher ─────────────────────────────────────────────────────
def get_usd_ils_rate() -> float:
    try:
        import yfinance as yf
        h = yf.Ticker("USDILS=X").history(period="2d")
        if not h.empty: return float(h["Close"].iloc[-1])
    except Exception: pass
    return 3.72

def _yf_price(ticker: str):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker); h = t.history(period="5d")
        if h.empty: return None
        px = float(h["Close"].iloc[-1]); prev = float(h["Close"].iloc[-2]) if len(h)>1 else px
        ch = px - prev; chp = (ch/prev*100) if prev else 0
        info = t.info
        return {"price":round(px,4),"change":round(ch,4),"change_pct":round(chp,2),
                "currency":info.get("currency","USD"),
                "name":info.get("longName") or info.get("shortName") or ticker,
                "source":"yfinance","date":h.index[-1].strftime("%Y-%m-%d")}
    except Exception: return None

def fetch_price(inv: dict):
    t = inv.get("type","us_stock")
    if t == "us_stock":   return _yf_price(inv["ticker"])
    if t == "tase_stock": return _yf_price(inv["ticker"].upper().replace(".TA","") + ".TA")
    if t == "israeli_fund":
        r = _yf_price(inv.get("fund_id","") + ".TA")
        if r: r["currency"] = "ILS"; return r
        return None
    return {"price":float(inv.get("manual_price",0)),"change":0.0,"change_pct":0.0,
            "currency":inv.get("currency","ILS"),"name":inv.get("name","ידני"),
            "source":"manual","date":datetime.now().strftime("%Y-%m-%d")}

def fetch_all_prices(investments: list) -> dict:
    prices = {}
    for inv in investments:
        key = inv.get("ticker") or inv.get("fund_id") or inv["id"]
        if is_price_fresh(key):
            prices[inv["id"]] = get_cached_price(key); continue
        pd_ = fetch_price(inv)
        if pd_: set_cached_price(key, pd_); prices[inv["id"]] = pd_
        else:
            stale = get_cached_price(key)
            if stale: stale["stale"] = True; prices[inv["id"]] = stale
    return prices

RTL = """<style>
html,body,[class*="css"]{direction:rtl;}
.stApp,.block-container,section[data-testid="stSidebar"]{direction:rtl;}
input,textarea,select{direction:rtl!important;text-align:right!important;}
#MainMenu,footer{visibility:hidden;}
section[data-testid="stSidebar"]{display:none!important;}
[data-testid="collapsedControl"]{display:none!important;}
</style>"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="תוכנית חיסכון משפחתית", page_icon="💰", layout="wide")
st.markdown(RTL, unsafe_allow_html=True)

now = datetime.now()
year, month = now.year, now.month

with st.sidebar:
    st.header("📅 בחר חודש")
    all_ym = get_all_years_months()
    if (year, month) not in all_ym:
        all_ym.insert(0, (year, month))
    ym_labels = [f"{MONTH_NAMES[m]} {y}" for y,m in all_ym]
    default_lbl = f"{MONTH_NAMES[month]} {year}"
    idx = ym_labels.index(default_lbl) if default_lbl in ym_labels else 0
    sel = st.selectbox("חודש", ym_labels, index=idx, label_visibility="collapsed")
    sy, sm = all_ym[ym_labels.index(sel)]
    st.divider()
    st.info("📌 מחירים מתעדכנים פעם ביום")

st.title("💰 תוכנית חיסכון משפחתית")
st.caption(f"לוח בקרה | {MONTH_NAMES[month]} {year}")

# ── Mobile navigation ─────────────────────────────────────────────────────────
st.markdown("""
<style>
.nav-btn a {
    display:block; text-align:center; background:#1e3a5f; color:white!important;
    padding:14px 8px; border-radius:12px; font-size:1.1rem; font-weight:600;
    text-decoration:none; margin:4px 0;
}
.nav-btn a:hover { background:#2d5a9e; }
</style>""", unsafe_allow_html=True)

nav1, nav2, nav3, nav4 = st.columns(4)
with nav1: st.page_link("pages/1_Investments.py", label="📈 השקעות", use_container_width=True)
with nav2: st.page_link("pages/2_Income.py",      label="💵 הכנסות",  use_container_width=True)
with nav3: st.page_link("pages/3_Expenses.py",    label="🧾 הוצאות",  use_container_width=True)
with nav4: st.page_link("pages/4_Analysis.py",    label="📊 ניתוח",   use_container_width=True)
st.divider()

with st.spinner("טוען..."):
    investments = get_investments()
    usd_ils = get_usd_ils_rate()
    prices = fetch_all_prices(investments)
    income_list = get_income(year=sy, month=sm)
    expense_list = get_expenses(year=sy, month=sm)

total_val = total_cost = 0.0
for inv in investments:
    pd_ = prices.get(inv["id"])
    if not pd_: continue
    units = float(inv.get("units",0)); mul = usd_ils if pd_.get("currency")=="USD" else 1.0
    total_val  += float(pd_["price"]) * units * mul
    total_cost += float(inv.get("purchase_price",0)) * units * mul
gain = total_val - total_cost
gain_pct = (gain/total_cost*100) if total_cost else 0

total_inc = sum(e["amount"] for e in income_list)
total_exp = sum(e["amount"] for e in expense_list)
saving = total_inc - total_exp
save_rate = (saving/total_inc*100) if total_inc else 0

c1,c2,c3,c4 = st.columns(4)
c1.metric("💼 שווי תיק", f"₪{total_val:,.0f}", f"רווח: ₪{gain:,.0f} ({gain_pct:+.1f}%)")
c2.metric("📥 הכנסות", f"₪{total_inc:,.0f}")
c3.metric("📤 הוצאות", f"₪{total_exp:,.0f}")
c4.metric("💰 חיסכון", f"₪{saving:,.0f}", f"שיעור: {save_rate:.1f}%")

st.divider()
col_l, col_r = st.columns(2)

with col_l:
    st.subheader("📊 הרכב תיק")
    if investments and prices:
        rows = []
        for inv in investments:
            pd_ = prices.get(inv["id"])
            if not pd_: continue
            mul = usd_ils if pd_.get("currency")=="USD" else 1.0
            val = float(pd_["price"]) * float(inv.get("units",0)) * mul
            rows.append({"שם": inv.get("name") or inv.get("ticker") or "—", "שווי": val})
        if rows:
            fig = px.pie(pd.DataFrame(rows), values="שווי", names="שם", hole=0.45,
                         color_discrete_sequence=px.colors.sequential.Blues_r)
            fig.update_traces(textinfo="percent+label")
            fig.update_layout(height=300, margin=dict(t=10,b=10,l=10,r=10))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("הוסף השקעות בדף 'השקעות'")

with col_r:
    st.subheader("🧾 הוצאות לפי קטגוריה")
    if expense_list:
        cat_t = {}
        for e in expense_list: cat_t[e.get("category","אחר")] = cat_t.get(e.get("category","אחר"),0)+e["amount"]
        df = pd.DataFrame(sorted(cat_t.items(), key=lambda x:x[1], reverse=True), columns=["קטגוריה","סכום"])
        fig2 = px.bar(df, y="קטגוריה", x="סכום", orientation="h", color="סכום",
                      color_continuous_scale="Blues", text="סכום")
        fig2.update_traces(texttemplate="₪%{text:,.0f}", textposition="outside")
        fig2.update_layout(height=300, coloraxis_showscale=False, margin=dict(t=10,b=10,r=80),
                           yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("הוסף הוצאות בדף 'הוצאות'")

all_ym2 = get_all_years_months()
if len(all_ym2) > 1:
    st.subheader("📈 היסטוריה")
    rows2 = []
    for y,m in sorted(all_ym2):
        inc = sum(e["amount"] for e in get_income(year=y,month=m))
        exp = sum(e["amount"] for e in get_expenses(year=y,month=m))
        rows2.append({"חודש":f"{MONTH_NAMES[m][:3]} {y}","הכנסות":inc,"הוצאות":exp,"חיסכון":inc-exp})
    dh = pd.DataFrame(rows2)
    fig3 = go.Figure()
    fig3.add_bar(x=dh["חודש"],y=dh["הכנסות"],name="הכנסות",marker_color="#3b82f6")
    fig3.add_bar(x=dh["חודש"],y=dh["הוצאות"],name="הוצאות",marker_color="#ef4444")
    fig3.add_scatter(x=dh["חודש"],y=dh["חיסכון"],name="חיסכון",mode="lines+markers",
                     line=dict(color="#22c55e",width=2.5))
    fig3.update_layout(barmode="group",height=300,legend=dict(orientation="h",y=1.1))
    st.plotly_chart(fig3, use_container_width=True)

st.subheader("📋 פעולות אחרונות")
recent = []
for e in expense_list: recent.append({"סוג":"📤","תיאור":e.get("description",""),"קטגוריה":e.get("category",""),"סכום":e["amount"],"תאריך":e.get("date","")})
for e in income_list:  recent.append({"סוג":"📥","תיאור":e.get("description",""),"קטגוריה":e.get("category",""),"סכום":e["amount"],"תאריך":e.get("date","")})
if recent:
    df_r = pd.DataFrame(recent).sort_values("תאריך",ascending=False).head(15).reset_index(drop=True)
    df_r["סכום"] = df_r["סכום"].apply(lambda x:f"₪{x:,.0f}")
    st.dataframe(df_r, use_container_width=True, hide_index=True)
else:
    st.info("עדיין אין פעולות לחודש זה.")
