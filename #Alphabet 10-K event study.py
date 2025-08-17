#Alphabet 10-K event study

import pandas as pd
import numpy as np
import requests
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.stats import ttest_ind

# -------------------------
# 1) Yahoo Finance
# -------------------------
def fetch_yahoo_prices(ticker, range_period="120mo", interval="1d"):
    # 120mo to cover many 10-Ks
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_period}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=30)
    if res.status_code != 200:
        raise Exception(f"Yahoo Finance API error for {ticker}: {res.status_code}")

    data = res.json()
    try:
        timestamps = data['chart']['result'][0]['timestamp']
        prices = data['chart']['result'][0]['indicators']['quote'][0]['close']
        volumes = data['chart']['result'][0]['indicators']['quote'][0]['volume']
        df = pd.DataFrame({
            'Date': [datetime.fromtimestamp(ts) for ts in timestamps],
            'Close': prices,
            'Volume': volumes
        }).set_index('Date')
        return df
    except Exception as e:
        raise ValueError(f"Invalid data format for {ticker}: {e}")

# -------------------------
# 2) SEC EDGAR
# -------------------------
SEC_UA = {"User-Agent": "hbirring@seattleu.edu"}  

def get_filing_dates(cik, form_type="10-K"):
    """Return list of (filingDate, accessionNumber) for the given form type."""
    url = f"https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json"
    r = requests.get(url, headers=SEC_UA, timeout=30)
    r.raise_for_status()
    j = r.json()
    forms = j['filings']['recent']['form']
    dates = j['filings']['recent']['filingDate']
    accessions = j['filings']['recent']['accessionNumber']
    out = []
    for f, d, a in zip(forms, dates, accessions):
        if f == form_type:
            out.append((pd.to_datetime(d), a))
    return sorted(out, key=lambda x: x[0])

def get_company_facts(cik):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
    r = requests.get(url, headers=SEC_UA, timeout=30)
    r.raise_for_status()
    return r.json()

def _pull_tag(facts, tag, unit="USD", form_whitelist={"10-K","10-Q"}):
    """Return DataFrame [end, val, form] for a us-gaap tag."""
    try:
        rows = facts["facts"]["us-gaap"][tag]["units"][unit]
    except KeyError:
        return pd.DataFrame(columns=["end","val","form"])
    data = []
    for x in rows:
        f = x.get("form")
        if f in form_whitelist:
            data.append({
                "end": pd.to_datetime(x.get("end")),
                "val": x.get("val"),
                "form": f
            })
    df = pd.DataFrame(data).dropna(subset=["end"]).sort_values("end")
    if not df.empty:
        df = df.drop_duplicates(subset=["end","form"], keep="last")
    return df

def compute_10k_ratios(facts):
    """
    Ratios (10-K only, absolute values):
      - current_ratio     = CurrentAssets / CurrentLiabilities
      - quick_ratio       = (CurrentAssets - Inventory) / Current Liabilities
      - debt_to_equity    = Liabilities / Equity
      - roe               = NetIncome / Equity
      - roa               = NetIncome / Assets
    Returns DataFrame indexed by fiscal year-end 'end'.
    """
    forms = {"10-K"}
    def _pull(tag, unit="USD"):
        return _pull_tag(facts, tag, unit=unit, form_whitelist=forms).set_index("end")

    assets_cur  = _pull("AssetsCurrent")
    liab_cur    = _pull("LiabilitiesCurrent")
    liab_total  = _pull("Liabilities")
    eq1         = _pull("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")
    eq2         = _pull("StockholdersEquity")
    equity      = eq1 if not eq1.empty else eq2
    netinc      = _pull("NetIncomeLoss")
    inventory   = _pull("Inventory")
    assets_tot  = _pull("Assets")

    idx = sorted(set().union(
        assets_cur.index, liab_cur.index, liab_total.index, equity.index,
        netinc.index, inventory.index, assets_tot.index
    ))
    df = pd.DataFrame(index=idx)

    for name, src in [
        ("AssetsCurrent", assets_cur), ("LiabilitiesCurrent", liab_cur),
        ("Liabilities", liab_total), ("Equity", equity),
        ("NetIncome", netinc), ("Inventory", inventory),
        ("Assets", assets_tot)
    ]:
        if not src.empty:
            df[name] = src["val"]

    def safe_div(a, b):
        a = pd.to_numeric(a, errors='coerce')
        b = pd.to_numeric(b, errors='coerce')
        out = a.divide(b)
        return out.where(b != 0)

    inv_series = df["Inventory"].fillna(0.0) if "Inventory" in df.columns else pd.Series(0.0, index=df.index)

    df["current_ratio"]   = safe_div(df.get("AssetsCurrent"), df.get("LiabilitiesCurrent"))
    df["quick_ratio"]     = safe_div(df.get("AssetsCurrent") - inv_series, df.get("LiabilitiesCurrent"))
    df["debt_to_equity"]  = safe_div(df.get("Liabilities"), df.get("Equity"))
    df["roe"]             = safe_div(df.get("NetIncome"), df.get("Equity"))
    df["roa"]             = safe_div(df.get("NetIncome"), df.get("Assets"))

    return df

# -------------------------
# 3) (GOOGL, 10-K)
# -------------------------
CIK_ALPHABET = "0001652044"
TICKER = "GOOGL"

ten_ks = get_filing_dates(CIK_ALPHABET, form_type="10-K")
print("Alphabet 10-K filings (most recent 10 shown):", ten_ks[-10:])
if len(ten_ks) == 0:
    raise SystemExit("No 10-K filings found.")
latest_filing_date = ten_ks[-1][0]  # most recent 10-K filing date

# -------------------------
# 4) Fetch price data for stock + S&P 500
# -------------------------
googl = fetch_yahoo_prices(TICKER, range_period="120mo")
sp500 = fetch_yahoo_prices("^GSPC", range_period="120mo")

# Compute forward returns for multiple horizons
for h in [5, 20, 30]:
    googl[f'Return_{h}d'] = googl['Close'].pct_change(periods=-h)
    sp500[f'Market_return_{h}d'] = sp500['Close'].pct_change(periods=-h)

googl['Volume_avg_30'] = googl['Volume'].rolling(window=30).mean()
googl['Volume_change'] = (googl['Volume'] - googl['Volume_avg_30']) / googl['Volume_avg_30']

# ---------- Map filing date to the NEXT trading day ----------
def next_trading_day(dti, dt):
    pos = dti.searchsorted(pd.Timestamp(dt), side="left")
    if pos >= len(dti):
        return None
    return dti[pos]

googl['K10_filed'] = 0
event_dt = next_trading_day(googl.index, latest_filing_date)
if event_dt is not None:
    googl.at[event_dt, 'K10_filed'] = 1

# -------------------------
# 5) Pull ratios from SEC and align to events
# -------------------------
facts = get_company_facts(CIK_ALPHABET)
ratios_10k = compute_10k_ratios(facts).sort_index()

abs_ratio_cols = ["current_ratio","quick_ratio","debt_to_equity","roe","roa"]
for c in abs_ratio_cols:
    googl[c] = np.nan

def closest_period_end_on_or_before(date_idx, dt):
    pos = date_idx.searchsorted(pd.Timestamp(dt), side="right") - 1
    if pos >= 0:
        return date_idx[pos]
    return None

# choose the fiscal year-end immediately prior to (or equal to) the filing date
ratio_date_latest = closest_period_end_on_or_before(ratios_10k.index, latest_filing_date)
if ratio_date_latest is not None and event_dt is not None:
    googl.loc[event_dt, abs_ratio_cols] = ratios_10k.loc[ratio_date_latest, abs_ratio_cols].values

# -------------------------
# 6) Build main 'data' frame 
# -------------------------
# Keep 5d as the "default" for volume/plotting, but t-test all horizons 
data = googl[[f'Return_{h}d' for h in [5,20,30]] + ['Volume_change', 'K10_filed']].copy()
for h in [5,20,30]:
    data[f'Market_return_{h}d'] = sp500[f'Market_return_{h}d']
for c in abs_ratio_cols:
    data[c] = googl[c]

# keep rows where we have returns for each horizon separately during testing
print("\nEvent row with ratios (should show K10_filed==1):")
print(data.loc[[event_dt]] if event_dt in data.index else "Event date not in data window.")

# -------------------------
# 7) Event study t-tests for 5d, 20d, 30d to see the differences
# -------------------------
df = data.copy()
df.index = pd.to_datetime(df.index)

for w in [5, 20, 30]:
    # drop rows that don't have the return for this horizon
    dfw = df.dropna(subset=[f'Return_{w}d', f'Market_return_{w}d'])
    before = dfw.loc[dfw.index < event_dt, f'Return_{w}d'].tail(w)
    after  = dfw.loc[dfw.index > event_dt, f'Return_{w}d'].head(w)

    t_stat, p_val = ttest_ind(before, after, equal_var=False, nan_policy='omit')

    print(f"\nT-Test Results ({w}-day window, latest 10-K):")
    print(f"Event day used: {event_dt}")
    print(f"Before mean return: {before.mean():.6f}")
    print(f"After mean return:  {after.mean():.6f}")
    print(f"T-statistic:        {t_stat:.4f}")
    print(f"P-value:            {p_val:.4f}")
    if p_val < 0.05:
        print("Statistically significant difference.")
    else:
        print("No statistically significant difference.")

# -------------------------
# 8) Multi-10K event correlation using ABSOLUTE ratios 
# -------------------------
def forward_return(px_series, when, days=5):
    # generic forward return from the next trading day
    idx = px_series.index
    d = next_trading_day(idx, when)
    if d is None:
        return np.nan
    pos = idx.get_loc(d)
    if pos + days >= len(idx):
        return np.nan
    p0 = px_series.iloc[pos]
    pN = px_series.iloc[pos + days]
    return (pN / p0) - 1.0

events = []
for d, _acc in ten_ks[-20:]:  # up to last 20 annual filings
    per_end = closest_period_end_on_or_before(ratios_10k.index, d)
    if per_end is None:
        continue
    row = {
        "filingDate": pd.to_datetime(d),
        "ret_5d":  forward_return(googl["Close"], d, 5),
        "ret_20d": forward_return(googl["Close"], d, 20),
        "ret_30d": forward_return(googl["Close"], d, 30),
    }
    for c in abs_ratio_cols:
        row[c] = ratios_10k.loc[per_end, c] if c in ratios_10k.columns else np.nan
    events.append(row)

event_df = pd.DataFrame(events)
print("\nEvent-level dataset (tail):")
print(event_df.tail())

valid_cols = ["ret_5d","ret_20d","ret_30d"] + abs_ratio_cols
corr_ev = event_df[valid_cols].dropna()
if not corr_ev.empty and len(corr_ev) > 2:
    cmat = corr_ev.corr().round(3)
    print("\nCorrelation: forward event returns vs ABSOLUTE ratios (multi-10K):")
    print(cmat.loc[["ret_5d","ret_20d","ret_30d"], abs_ratio_cols])
else:
    print("\n(Info) Not enough multi-10K data for correlation (after dropping NaNs).")

# -------------------------
# 9) Plot around latest 10-K (using mapped event_dt)
# -------------------------
plt.figure(figsize=(12,6))
plt.plot(googl.index, googl['Close'], label='GOOGL Close')
if event_dt is not None:
    plt.axvline(event_dt, color='red', linestyle='--', label='10-K Event (next trading day)')
plt.title('GOOGL Stock Price vs. 10-K Filing (latest)')
plt.xlabel('Date'); plt.ylabel('Price (USD)')
plt.grid(True); plt.legend(); plt.show()
