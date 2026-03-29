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
ASSET_TYPES = {"us_stock":"📈 מניה אמריקאית","tase_stock":"🇮🇱 מניה ישראלית","israeli_fund":"📊 קרן נאמנות","cash_ils":"💵 מזומן שקלים","cash_usd":"💵 מזומן דולרים","manual":"✏️ ידני"}
MONTH_NAMES = {1:"ינואר",2:"פברואר",3:"מרץ",4:"אפריל",5:"מאי",6:"יוני",7:"יולי",8:"אוגוסט",9:"ספטמבר",10:"אוקטובר",11:"נובמבר",12:"דצמבר"}

# ── SHARED: DataManager (JSONBin.io) ─────────────────────────────────────────
import json, uuid, os, requests
from datetime import datetime
import streamlit as st

JSONBIN_BASE = "https://api.jsonbin.io/v3"

def _key():
    return st.secrets.get("JSONBIN_KEY", os.environ.get("JSONBIN_KEY",""))

def _headers():
    return {
        "X-Master-Key": _key(),
        "Content-Type": "application/json",
        "X-Bin-Versioning": "false",
    }

def _get_or_create_bin(name: str) -> str:
    # bin_id stored in session_state across reruns within same session
    sid = f"bid_{name}"
    if sid in st.session_state and st.session_state[sid]:
        return st.session_state[sid]
    # Also check if user stored it in secrets
    secret_key = f"JSONBIN_{name.upper()}_ID"
    stored = st.secrets.get(secret_key, "")
    if stored:
        st.session_state[sid] = stored
        return stored
    # Create new bin
    try:
        r = requests.post(
            f"{JSONBIN_BASE}/b",
            headers={**_headers(), "X-Bin-Name": f"familybudget_{name}", "X-Bin-Private": "true"},
            json={"data": []},
            timeout=15
        )
        if r.ok:
            bid = r.json()["metadata"]["id"]
            st.session_state[sid] = bid
            # Show user the ID to save in secrets
            st.info(f"📌 **שמור ב-Streamlit Secrets:**\n`{secret_key} = \"{bid}\"`")
            return bid
    except Exception as e:
        st.error(f"שגיאת JSONBin: {e}")
    return None

def _read(name: str) -> list:
    bid = _get_or_create_bin(name)
    if not bid: return []
    try:
        r = requests.get(f"{JSONBIN_BASE}/b/{bid}/latest", headers=_headers(), timeout=15)
        if r.ok:
            return r.json().get("record", {}).get("data", [])
    except Exception:
        pass
    return []

def _write(name: str, data: list):
    bid = _get_or_create_bin(name)
    if not bid: return
    try:
        r = requests.put(f"{JSONBIN_BASE}/b/{bid}", headers=_headers(),
                         json={"data": data}, timeout=15)
        if not r.ok:
            st.error(f"שגיאת שמירה ({name}): {r.status_code}")
    except Exception as e:
        st.error(f"שגיאת שמירה: {e}")

def get_investments():    return _read("investments")
def add_investment(inv):
    inv["id"] = str(uuid.uuid4()); inv["added_date"] = datetime.now().isoformat()
    d = _read("investments"); d.append(inv); _write("investments", d)
def remove_investment(iid):
    _write("investments", [i for i in _read("investments") if i["id"] != iid])

def get_income(year=None, month=None):
    e = _read("income")
    if year:  e = [x for x in e if x.get("year")  == year]
    if month: e = [x for x in e if x.get("month") == month]
    return e
def add_income(entry):
    entry["id"] = str(uuid.uuid4())
    d = _read("income"); d.append(entry); _write("income", d)
def remove_income(eid):
    _write("income", [e for e in _read("income") if e.get("id") != eid])

def get_expenses(year=None, month=None):
    e = _read("expenses")
    if year:  e = [x for x in e if x.get("year")  == year]
    if month: e = [x for x in e if x.get("month") == month]
    return e
def add_expense(entry):
    entry["id"] = str(uuid.uuid4())
    d = _read("expenses"); d.append(entry); _write("expenses", d)
def remove_expense(eid):
    _write("expenses", [e for e in _read("expenses") if e.get("id") != eid])

def get_all_years_months():
    ym = set()
    for e in _read("income") + _read("expenses"):
        if "year" in e and "month" in e: ym.add((e["year"], e["month"]))
    return sorted(ym, reverse=True)

def is_price_fresh(key):
    for r in _read("prices_cache"):
        if r.get("key") == key:
            return r.get("date") == datetime.now().strftime("%Y-%m-%d")
    return False
def get_cached_price(key):
    for r in _read("prices_cache"):
        if r.get("key") == key: return r
    return None
def set_cached_price(key, price_data):
    cache = [r for r in _read("prices_cache") if r.get("key") != key]
    price_data["key"] = key; cache.append(price_data)
    _write("prices_cache", cache)
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
    if t == "cash_ils":
        return {"price":float(inv.get("manual_price",0)),"change":0.0,"change_pct":0.0,
                "currency":"ILS","name":inv.get("name","מזומן שקלים"),
                "source":"cash","date":datetime.now().strftime("%Y-%m-%d")}
    if t == "cash_usd":
        return {"price":float(inv.get("manual_price",0)),"change":0.0,"change_pct":0.0,
                "currency":"USD","name":inv.get("name","מזומן דולרים"),
                "source":"cash","date":datetime.now().strftime("%Y-%m-%d")}
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
</style>"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

st.set_page_config(page_title="תוכנית חיסכון משפחתית", page_icon="💰", layout="centered")

st.markdown("""<style>
html,body,[class*="css"]{direction:rtl;}
.stApp,.block-container{direction:rtl;}
input,textarea,select{direction:rtl!important;text-align:right!important;}
#MainMenu,footer,header{visibility:hidden;}
section[data-testid="stSidebar"]{display:none!important;}
[data-testid="collapsedControl"]{display:none!important;}
.stTabs [data-baseweb="tab-list"]{gap:4px;flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{font-size:1rem;padding:8px 12px;border-radius:8px;}
</style>""", unsafe_allow_html=True)

now = datetime.now()
MONTH_NAMES_LIST = list(MONTH_NAMES.values())

st.title("💰 תוכנית חיסכון משפחתית")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 סיכום", "💵 הכנסות", "🧾 הוצאות", "📈 השקעות", "📊 ניתוח"])

# ═══════════════════════════════════════════════════════════
# TAB 1 – DASHBOARD
# ═══════════════════════════════════════════════════════════
with tab1:
    cy, cm = st.columns(2)
    with cy: sel_year  = st.selectbox("שנה", list(range(now.year, now.year-4, -1)), key="t1y")
    with cm: sel_month = st.selectbox("חודש", list(range(1,13)), format_func=lambda m:MONTH_NAMES[m], index=now.month-1, key="t1m")

    with st.spinner("טוען..."):
        investments  = get_investments()
        usd_ils      = get_usd_ils_rate()
        prices       = fetch_all_prices(investments)
        income_list  = get_income(year=sel_year, month=sel_month)
        expense_list = get_expenses(year=sel_year, month=sel_month)

    total_val = total_cost = 0.0
    for inv in investments:
        pd_ = prices.get(inv["id"])
        if not pd_: continue
        mul = usd_ils if pd_.get("currency")=="USD" else 1.0
        total_val  += float(pd_["price"]) * float(inv.get("units",0)) * mul
        total_cost += float(inv.get("purchase_price",0)) * float(inv.get("units",0)) * mul
    gain = total_val - total_cost
    gain_pct = (gain/total_cost*100) if total_cost else 0

    total_inc = sum(e["amount"] for e in income_list)
    total_exp = sum(e["amount"] for e in expense_list)
    saving    = total_inc - total_exp
    save_rate = (saving/total_inc*100) if total_inc else 0

    c1,c2 = st.columns(2)
    c1.metric("💼 שווי תיק", f"₪{total_val:,.0f}", f"₪{gain:,.0f} ({gain_pct:+.1f}%)", delta_color="normal")
    c2.metric("💰 חיסכון חודשי", f"₪{saving:,.0f}", f"שיעור: {save_rate:.1f}%")
    c3,c4 = st.columns(2)
    c3.metric("📥 הכנסות", f"₪{total_inc:,.0f}")
    c4.metric("📤 הוצאות", f"₪{total_exp:,.0f}")
    st.divider()

    if expense_list:
        cat_t = {}
        for e in expense_list: cat_t[e.get("category","אחר")] = cat_t.get(e.get("category","אחר"),0)+e["amount"]
        df_cat = pd.DataFrame(sorted(cat_t.items(),key=lambda x:x[1],reverse=True),columns=["קטגוריה","סכום"])
        fig = px.bar(df_cat, y="קטגוריה", x="סכום", orientation="h",
                     color="סכום", color_continuous_scale="Blues", text="סכום",
                     title="הוצאות לפי קטגוריה")
        fig.update_traces(texttemplate="₪%{text:,.0f}", textposition="outside")
        fig.update_layout(height=320, coloraxis_showscale=False,
                          margin=dict(t=40,b=10,r=80), yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    if income_list or expense_list:
        st.subheader("📋 פעולות אחרונות")
        recent = []
        for e in expense_list: recent.append({"סוג":"📤 הוצאה","תיאור":e.get("description",""),"קטגוריה":e.get("category",""),"סכום":f"₪{e['amount']:,.0f}","תאריך":e.get("date","")})
        for e in income_list:  recent.append({"סוג":"📥 הכנסה","תיאור":e.get("description",""),"קטגוריה":e.get("category",""),"סכום":f"₪{e['amount']:,.0f}","תאריך":e.get("date","")})
        df_r = pd.DataFrame(recent).sort_values("תאריך",ascending=False).head(10).reset_index(drop=True)
        st.dataframe(df_r, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════
# TAB 2 – INCOME
# ═══════════════════════════════════════════════════════════
with tab2:
    st.subheader("💵 ניהול הכנסות")
    cy2, cm2 = st.columns(2)
    with cy2: iy = st.selectbox("שנה", list(range(now.year, now.year-4,-1)), key="t2y")
    with cm2: im = st.selectbox("חודש", list(range(1,13)), format_func=lambda m:MONTH_NAMES[m], index=now.month-1, key="t2m")

    inc_entries = get_income(year=iy, month=im)
    st.metric(f"סה\"כ הכנסות — {MONTH_NAMES[im]} {iy}", f"₪{sum(e['amount'] for e in inc_entries):,.0f}")

    # Quick add buttons
    st.markdown("**⚡ הוספה מהירה:**")
    qa, qb = st.columns(2)
    with qa:
        if st.button("💼 משכורת שלי ₪13,500", use_container_width=True):
            add_income({"description":"משכורת חודשית","amount":13500,"category":"💼 משכורת",
                        "date":date(iy,im,1).strftime("%Y-%m-%d"),"year":iy,"month":im,"note":""})
            st.success("נוסף ✅"); st.rerun()
    with qb:
        if st.button("💼 משכורת אישתי ₪16,000", use_container_width=True):
            add_income({"description":"משכורת אישתי","amount":16000,"category":"💼 משכורת",
                        "date":date(iy,im,1).strftime("%Y-%m-%d"),"year":iy,"month":im,"note":""})
            st.success("נוסף ✅"); st.rerun()

    st.markdown("**➕ הוספה ידנית:**")
    with st.form("add_income", clear_on_submit=True):
        i_desc   = st.text_input("תיאור", placeholder="למשל: דמי לידה ינואר")
        i_amount = st.number_input("סכום (₪)", min_value=0.0, step=100.0, format="%.0f")
        i_cat    = st.selectbox("קטגוריה", INCOME_CATEGORIES)
        i_date   = st.date_input("תאריך", value=date(iy, im, 1))
        if st.form_submit_button("הוסף הכנסה ✅", type="primary", use_container_width=True):
            if i_amount > 0:
                add_income({"description":i_desc,"amount":i_amount,"category":i_cat,
                            "date":i_date.strftime("%Y-%m-%d"),"year":iy,"month":im,"note":""})
                st.success(f"נוסף: ₪{i_amount:,.0f}"); st.rerun()
            else:
                st.error("הכנס סכום חיובי")

    if inc_entries:
        st.markdown("**📋 רשומות קיימות:**")
        for e in sorted(inc_entries, key=lambda x:x.get("date",""), reverse=True):
            col_a, col_b = st.columns([4,1])
            with col_a: st.write(f"**{e.get('description','')}** — ₪{e['amount']:,.0f} | {e.get('category','')} | {e.get('date','')}")
            with col_b:
                if st.button("🗑️", key=f"di_{e['id']}"):
                    remove_income(e["id"]); st.rerun()

# ═══════════════════════════════════════════════════════════
# TAB 3 – EXPENSES
# ═══════════════════════════════════════════════════════════
with tab3:
    st.subheader("🧾 ניהול הוצאות")
    cy3, cm3 = st.columns(2)
    with cy3: ey = st.selectbox("שנה", list(range(now.year, now.year-4,-1)), key="t3y")
    with cm3: em = st.selectbox("חודש", list(range(1,13)), format_func=lambda m:MONTH_NAMES[m], index=now.month-1, key="t3m")

    exp_entries = get_expenses(year=ey, month=em)
    total_e = sum(e["amount"] for e in exp_entries)
    st.metric(f"סה\"כ הוצאות — {MONTH_NAMES[em]} {ey}", f"₪{total_e:,.0f}")

    # Quick fixed expenses
    st.markdown("**⚡ הוצאות קבועות מהירות:**")
    qe1,qe2,qe3 = st.columns(3)
    FIXED = [("🏠 שכר דירה","🏠 דיור","שכר דירה"),
             ("⚡ חשמל","🏠 דיור","חשמל"),
             ("💧 מים","🏠 דיור","מים")]
    for col, (label,cat,sub) in zip([qe1,qe2,qe3], FIXED):
        with col:
            with st.expander(label):
                qa = st.number_input("סכום:", min_value=0, step=50, key=f"qf_{label}")
                if st.button("הוסף", key=f"qfb_{label}") and qa > 0:
                    add_expense({"description":label,"amount":qa,"category":cat,"sub_category":sub,
                                 "date":date(ey,em,1).strftime("%Y-%m-%d"),"year":ey,"month":em,"note":""})
                    st.success("נוסף!"); st.rerun()

    st.markdown("**➕ הוספת הוצאה:**")
    with st.form("add_expense", clear_on_submit=True):
        e_desc   = st.text_input("תיאור", placeholder="למשל: קניות שופרסל")
        e_amount = st.number_input("סכום (₪)", min_value=0.0, step=10.0, format="%.0f")
        e_cat    = st.selectbox("קטגוריה", list(EXPENSE_CATEGORIES.keys()))
        e_subcat = st.selectbox("תת-קטגוריה", EXPENSE_CATEGORIES[e_cat])
        e_date   = st.date_input("תאריך", value=date.today())
        if st.form_submit_button("הוסף הוצאה ✅", type="primary", use_container_width=True):
            if e_amount > 0:
                add_expense({"description":e_desc,"amount":e_amount,"category":e_cat,
                             "sub_category":e_subcat,"date":e_date.strftime("%Y-%m-%d"),
                             "year":e_date.year,"month":e_date.month,"note":""})
                st.success(f"נוסף: ₪{e_amount:,.0f}"); st.rerun()
            else:
                st.error("הכנס סכום חיובי")

    if exp_entries:
        st.markdown("**📋 רשומות קיימות:**")
        cat_groups = {}
        for e in exp_entries: cat_groups.setdefault(e.get("category","אחר"),[]).append(e)
        for cat, ces in sorted(cat_groups.items(), key=lambda x:sum(e["amount"] for e in x[1]), reverse=True):
            cat_sum = sum(e["amount"] for e in ces)
            with st.expander(f"{cat} — ₪{cat_sum:,.0f}"):
                for e in sorted(ces, key=lambda x:x.get("date",""), reverse=True):
                    ca, cb = st.columns([4,1])
                    with ca: st.write(f"**{e.get('description','')}** — ₪{e['amount']:,.0f} | {e.get('date','')}")
                    with cb:
                        if st.button("🗑️", key=f"de_{e['id']}"):
                            remove_expense(e["id"]); st.rerun()

# ═══════════════════════════════════════════════════════════
# TAB 4 – INVESTMENTS
# ═══════════════════════════════════════════════════════════
with tab4:
    st.subheader("📈 ניהול השקעות")
    with st.spinner("מושך מחירים..."):
        usd2 = get_usd_ils_rate()
        invs = get_investments()
        prc  = fetch_all_prices(invs)

    st.info(f"שער דולר: ₪{usd2:.3f}")

    if invs:
        tv2 = tc2 = 0.0
        rows = []
        for inv in invs:
            pd_ = prc.get(inv["id"])
            units=float(inv.get("units",0)); avg=float(inv.get("purchase_price",0))
            cur=float(pd_["price"]) if pd_ else 0.0
            ccy=pd_.get("currency","ILS") if pd_ else "ILS"
            mul=usd2 if ccy=="USD" else 1.0
            val=cur*units*mul; cost=avg*units*mul; gain2=val-cost
            gp2=(gain2/cost*100) if cost else 0
            tv2+=val; tc2+=cost
            sym="$" if ccy=="USD" else "₪"
            # For USD assets show both USD price and ILS value
            if ccy=="USD":
                price_str=f"${cur:,.3f} (₪{cur*usd2:,.2f})"
                val_str=f"${cur*units:,.2f} / ₪{val:,.0f}"
            else:
                price_str=f"₪{cur:,.3f}"
                val_str=f"₪{val:,.0f}"
            gain_arrow = "▲" if gain2 >= 0 else "▼"
            rows.append({"שם":inv.get("name") or inv.get("ticker") or "—",
                         "מחיר":price_str,"שווי":val_str,
                         "רווח/הפסד":f"{gain_arrow} {sym}{abs(gain2/mul if ccy=='USD' else gain2):,.2f} ({gp2:+.1f}%)",
                         "_id":inv["id"]})
        tg2=tv2-tc2; tgp2=(tg2/tc2*100) if tc2 else 0
        st.metric("שווי תיק כולל", f"₪{tv2:,.0f}", f"₪{tg2:,.0f} ({tgp2:+.1f}%)", delta_color="normal")
        df_inv = pd.DataFrame(rows).drop(columns=["_id"])
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
        st.markdown("**🗑️ מחק נכס:**")
        opts = {inv["id"]: inv.get("name") or inv.get("ticker") or "—" for inv in invs}
        del_id = st.selectbox("בחר נכס למחיקה", list(opts.keys()), format_func=lambda x:opts[x])
        if st.button("מחק נכס", type="secondary"):
            remove_investment(del_id); st.success("נמחק!"); st.rerun()
    else:
        st.info("עדיין אין נכסים בתיק.")

    st.divider()
    st.markdown("**➕ הוספת נכס:**")
    with st.form("add_inv", clear_on_submit=True):
        at = st.selectbox("סוג", list(ASSET_TYPES.keys()), format_func=lambda x:ASSET_TYPES[x])
        is_cash = at in ("cash_ils","cash_usd")
        tk=""; fi=""; mp=0.0; mc="ILS"; un=1; pp=0.0

        if at in ("us_stock","tase_stock"):
            tk = st.text_input("טיקר", placeholder="AAPL, SPY, TEVA")
        elif at == "israeli_fund":
            fi = st.text_input("מספר קרן (7 ספרות)", placeholder="5113335")
        elif at == "cash_ils":
            mp = st.number_input("סכום מזומן (₪)", min_value=0.0, step=100.0, format="%.0f")
            mc = "ILS"
        elif at == "cash_usd":
            mp = st.number_input("סכום מזומן ($)", min_value=0.0, step=100.0, format="%.0f")
            mc = "USD"
        else:  # manual
            mp = st.number_input("מחיר נוכחי", min_value=0.0, step=0.01)
            mc = st.selectbox("מטבע", ["ILS","USD"])

        if not is_cash:
            un  = st.number_input("כמות מניות (שלמות)", min_value=0, step=1, format="%d")
            pp  = st.number_input("מחיר קנייה ממוצע ($)" if at=="us_stock" else "מחיר קנייה ממוצע",
                                  min_value=0.0, step=0.01, format="%.2f")

        if st.form_submit_button("הוסף ✅", type="primary", use_container_width=True):
            if is_cash and mp <= 0:
                st.error("הכנס סכום חיובי")
            elif not is_cash and un <= 0:
                st.error("הכנס כמות חיובית")
            elif at in ("us_stock","tase_stock") and not tk.strip():
                st.error("הכנס טיקר")
            else:
                nm = tk.upper().strip() if at in ("us_stock","tase_stock") else                      fi.strip() if at=="israeli_fund" else                      "מזומן שקלים" if at=="cash_ils" else                      "מזומן דולרים" if at=="cash_usd" else "ידני"
                new_inv = {"type":at, "name":nm, "units":float(un), "purchase_price":float(pp)}
                if at in ("us_stock","tase_stock"): new_inv["ticker"] = tk.upper().strip()
                elif at == "israeli_fund":           new_inv["fund_id"] = fi.strip()
                elif is_cash:
                    new_inv["manual_price"] = mp
                    new_inv["currency"]     = mc
                    new_inv["units"]        = 1.0
                    new_inv["purchase_price"] = mp
                else:
                    new_inv["manual_price"] = mp
                    new_inv["currency"]     = mc
                add_investment(new_inv)
                st.success(f"נוסף: {nm}"); st.rerun()

    st.divider()
    st.markdown("**✏️ עדכון מחיר ידני:**")
    invs2 = get_investments()
    if invs2:
        opts2={i["id"]:i.get("name") or i.get("ticker") or "—" for i in invs2}
        uid=st.selectbox("נכס",list(opts2.keys()),format_func=lambda x:opts2[x],key="uid")
        upx=st.number_input("מחיר",min_value=0.0,step=0.0001,format="%.4f",key="upx")
        if st.button("עדכן מחיר"):
            s=next(i for i in invs2 if i["id"]==uid)
            k=s.get("ticker") or s.get("fund_id") or uid
            set_cached_price(k,{"price":upx,"change":0,"change_pct":0,"currency":s.get("currency","ILS"),
                                 "name":s.get("name",""),"source":"manual","date":datetime.now().strftime("%Y-%m-%d")})
            st.success(f"עודכן ל-₪{upx:,.4f}"); st.rerun()

# ═══════════════════════════════════════════════════════════
# TAB 5 – ANALYSIS
# ═══════════════════════════════════════════════════════════
with tab5:
    st.subheader("📊 ניתוח וסיכום")
    all_ym = get_all_years_months()
    if not all_ym:
        st.info("אין עדיין נתונים לניתוח. הוסף הכנסות והוצאות תחילה.")
    else:
        hist = []
        for y,m in sorted(all_ym):
            inc=sum(e["amount"] for e in get_income(year=y,month=m))
            exp=sum(e["amount"] for e in get_expenses(year=y,month=m))
            sav=inc-exp
            hist.append({"label":f"{MONTH_NAMES[m][:3]} {y}","הכנסות":inc,"הוצאות":exp,"חיסכון":sav,
                          "שיעור חיסכון":round((sav/inc*100) if inc else 0,1)})
        df_h=pd.DataFrame(hist)
        c1,c2,c3 = st.columns(3)
        c1.metric("סה\"כ הכנסות",  f"₪{df_h['הכנסות'].sum():,.0f}")
        c2.metric("סה\"כ הוצאות",  f"₪{df_h['הוצאות'].sum():,.0f}")
        c3.metric("שיעור חיסכון ממוצע", f"{df_h['שיעור חיסכון'].mean():.1f}%")

        fig2=go.Figure()
        fig2.add_bar(x=df_h["label"],y=df_h["הכנסות"],name="הכנסות",marker_color="#3b82f6")
        fig2.add_bar(x=df_h["label"],y=df_h["הוצאות"],name="הוצאות",marker_color="#ef4444")
        fig2.add_scatter(x=df_h["label"],y=df_h["חיסכון"],name="חיסכון",
                         mode="lines+markers",line=dict(color="#22c55e",width=2))
        fig2.update_layout(barmode="group",height=320,legend=dict(orientation="h",y=1.1))
        st.plotly_chart(fig2, use_container_width=True)

        fig3=px.area(df_h,x="label",y="שיעור חיסכון",color_discrete_sequence=["#22c55e"],
                     title="שיעור חיסכון %")
        fig3.add_hline(y=20,line_dash="dash",line_color="#f59e0b",annotation_text="יעד 20%")
        fig3.update_layout(height=220)
        st.plotly_chart(fig3, use_container_width=True)

        all_exp2=get_expenses()
        if all_exp2:
            ce=pd.DataFrame([{"קטגוריה":e.get("category","אחר"),"סכום":e["amount"]} for e in all_exp2])
            ct=ce.groupby("קטגוריה")["סכום"].sum().reset_index().sort_values("סכום",ascending=False)
            st.markdown(f"**📌 קטגוריה גדולה ביותר:** {ct.iloc[0]['קטגוריה']} — ₪{ct.iloc[0]['סכום']:,.0f}")

        st.divider()
        st.markdown("**📥 ייצוא נתונים:**")
        xa,xb=st.columns(2)
        with xa:
            all_exp3=get_expenses()
            if all_exp3:
                csv=pd.DataFrame(all_exp3).drop(columns=["id"],errors="ignore").to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ הוצאות CSV",csv,file_name="expenses.csv",mime="text/csv")
        with xb:
            all_inc3=get_income()
            if all_inc3:
                csv2=pd.DataFrame(all_inc3).drop(columns=["id"],errors="ignore").to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ הכנסות CSV",csv2,file_name="income.csv",mime="text/csv")
