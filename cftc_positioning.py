"""CFTC positioning and SGX FX activity. Run: streamlit run cftc_positioning.py

Dependencies: streamlit>=1.49, pandas>=2.1, plotly, scipy, requests.
Single-file app: the SGX monthly snapshot is included below, so no extra files
or packages are needed. CFTC reports download on demand. SGX data is a dated
June-August 2026 snapshot, NOT an automatically updating SGX feed.
"""

from datetime import date
from io import BytesIO
from zipfile import BadZipFile, ZipFile
import logging

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from scipy.stats import percentileofscore
import streamlit as st

MARKETS_COMMODITIES = {
    "SOYBEANS": ["SOYBEANS - CHICAGO BOARD OF TRADE"],
    "SOYBEAN OIL": ["SOYBEAN OIL - CHICAGO BOARD OF TRADE"],
    "SOYBEAN MEAL": ["SOYBEAN MEAL - CHICAGO BOARD OF TRADE"],
    "CANOLA": ["CANOLA - ICE FUTURES U.S."],
    "GOLD": ["GOLD - COMMODITY EXCHANGE INC."],
    "SILVER": ["SILVER - COMMODITY EXCHANGE INC."],
    "PLATINUM": ["PLATINUM - NEW YORK MERCANTILE EXCHANGE"],
    "COPPER": ["COPPER- #1 - COMMODITY EXCHANGE INC."],
    "COBALT": ["COBALT - COMMODITY EXCHANGE INC."],
    "CORN": ["CORN - CHICAGO BOARD OF TRADE"],
    "COTTON": ["COTTON NO. 2 - ICE FUTURES U.S.", "COTTON - ICE FUTURES U.S."],
    "SUGAR": ["SUGAR NO. 11 - ICE FUTURES U.S."],
    "COFFEE C": ["COFFEE C - ICE FUTURES U.S."],
    "COCOA": ["COCOA - ICE FUTURES U.S."],
    "WHEAT-SRW": ["WHEAT-SRW - CHICAGO BOARD OF TRADE"],
    "WHEAT-HRW": ["WHEAT-HRW - CHICAGO BOARD OF TRADE"],
    'USGC HSFO (PLATTS)': ['USGC HSFO (PLATTS) - ICE FUTURES ENERGY DIV '],
    'FUEL OIL-3% USGC/3.5': ['FUEL OIL-3% USGC/3.5% FOB RDAM - ICE FUTURES ENERGY DIV'],
    'USGC HSFO-PLATTS/BRENT 1ST LN': ['USGC HSFO-PLATTS/BRENT 1ST LN  - ICE FUTURES ENERGY DIV'],
    'NY HARBOR ULSD': ['NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE'],
    'UP DOWN GC ULSD VS HO SPR': ['UP DOWN GC ULSD VS HO SPR - NEW YORK MERCANTILE EXCHANGE'],
    'ETHANOL T2 FOB INCL DUTY': ['ETHANOL T2 FOB INCL DUTY - NEW YORK MERCANTILE EXCHANGE'],
    'ETHANOL': ['ETHANOL - NEW YORK MERCANTILE EXCHANGE'],
    'CRUDE DIFF-WCS HOUSTON/WTI 1ST': ['CRUDE DIFF-WCS HOUSTON/WTI 1ST - ICE FUTURES ENERGY DIV'],
    'CRUDE OIL, LIGHT SWEET-WTI': ['CRUDE OIL, LIGHT SWEET-WTI - ICE FUTURES EUROPE'],
    'CRUDE DIFF-TMX WCS 1A INDEX': ['CRUDE DIFF-TMX WCS 1A INDEX - ICE FUTURES ENERGY DIV'],
    'CRUDE DIFF-TMX SW 1A INDEX': ['CRUDE DIFF-TMX SW 1A INDEX - ICE FUTURES ENERGY DIV'],
    'CONDENSATE DIF-TMX C5 1A INDEX': ['CONDENSATE DIF-TMX C5 1A INDEX - ICE FUTURES ENERGY DIV'],
    'WTI-PHYSICAL': ['WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE'],
    'WTI FINANCIAL CRUDE OIL': ['WTI FINANCIAL CRUDE OIL - NEW YORK MERCANTILE EXCHANGE'],
    'BRENT LAST DAY': ['BRENT LAST DAY - NEW YORK MERCANTILE EXCHANGE'],
    'WTI  HOUSTON ARGUS/WTI TR MO': ['WTI  HOUSTON ARGUS/WTI TR MO - NEW YORK MERCANTILE EXCHANGE'],
    'WTI MIDLAND ARGUS VS WTI TRADE': ['WTI MIDLAND ARGUS VS WTI TRADE - NEW YORK MERCANTILE EXCHANGE'],
    'GASOLINE RBOB': ['GASOLINE RBOB - NEW YORK MERCANTILE EXCHANGE'],
    'GULF COAST CBOB GAS A2 PL RBOB': ['GULF COAST CBOB GAS A2 PL RBOB - NEW YORK MERCANTILE EXCHANGE'],
    'GULF JET NY HEAT OIL SPR': ['GULF JET NY HEAT OIL SPR - NEW YORK MERCANTILE EXCHANGE'],
    'MARINE .5% FOB USGC/BRENT 1st': ['MARINE .5% FOB USGC/BRENT 1st - ICE FUTURES ENERGY DIV'],
    'GULF # 6 FUEL OIL CRACK': ['GULF # 6 FUEL OIL CRACK - NEW YORK MERCANTILE EXCHANGE']
}  

SGX_MONTHLY_SOURCE = (
    "https://links.sgx.com/FileOpen/SGX%20Monthly%20Statistics%20Report%20Update_Aug%202026.ashx"
    "?App=Announcement&FileID=903915"
)
SGX_SNAPSHOT_MONTH = "2026-08"
SGX_SNAPSHOT_MONTHS = ("2026-06-30", "2026-07-31", "2026-08-31")

# Exact rows in SGX's August 2026 Monthly Market Statistics, pages 20-21
# (volume) and 32-34 (month-end open interest). Each tuple is June, July, August.
# Keep contract sizes separate. An absent options row is unknown, not zero.
SGX_MONTHLY_SNAPSHOT = {
    "USD_CNH FX Futures": {
        "volume": (4989060, 4154962, 4138080), "oi": (200932, 214113, 247261),
        "options_row": "USD_CNH FX Options",
        "options_volume": (10919, 5032, 11756), "options_oi": (10998, 10568, 18902),
    },
    "INR_USD FX Futures": {
        "volume": (3916421, 3720012, 3091812), "oi": (245722, 232700, 200546),
        "options_row": "INR_USD FX Options",
        "options_volume": (0, 0, 0), "options_oi": (0, 0, 0),
    },
    "KRW_USD FX Futures (Mini)": {
        "volume": (1164513, 1197969, 748352), "oi": (29684, 35598, 39482),
    },
    "USD/SGD (Full-Sized) Futures": {
        "volume": (405, 535, 310), "oi": (169, 189, 182),
    },
    "USD_SGD FX Futures": {
        "volume": (1171, 1214, 1235), "oi": (796, 605, 607),
    },
    "THB_USD FX Futures": {
        "volume": (2916, 1246, 911), "oi": (263, 277, 192),
    },
    "SGD_CNH FX Futures": {
        "volume": (0, 0, 0), "oi": (0, 0, 0),
    },
    "TWD/USD Futures (Full Sized)": {
        "volume": (42707, 45929, 44078), "oi": (259, 378, 407),
    },
}
SGX_FX_ASSETS = {
    "USD/CNH (SGX)": "USD_CNH FX Futures",
    "INR/USD (SGX)": "INR_USD FX Futures",
    "KRW/USD Mini (SGX)": "KRW_USD FX Futures (Mini)",
    "USD/SGD (SGX)": "USD/SGD (Full-Sized) Futures",
    "USD/THB (SGX reports THB/USD)": "THB_USD FX Futures",
    "SGD/CNH (SGX)": "SGD_CNH FX Futures",
    "TWD/USD Full-size (SGX)": "TWD/USD Futures (Full Sized)",
}

MARKETS_FX = {
    "EURO FX": ["EURO FX - CHICAGO MERCANTILE EXCHANGE"],
    "JAPANESE YEN": ["JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"],
    "BRITISH POUND STERLING": ["BRITISH POUND - CHICAGO MERCANTILE EXCHANGE"],
    "SWISS FRANC": ["SWISS FRANC - CHICAGO MERCANTILE EXCHANGE"],
    "CANADIAN DOLLAR": ["CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"],
    "AUSTRALIAN DOLLAR": ["AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"],
    "MEXICAN PESO (MXN)": ["MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE"],
    "BRAZILIAN REAL (BRL)": ["BRAZILIAN REAL - CHICAGO MERCANTILE EXCHANGE"],
    # SGX entries route to their own activity view before any CFTC lookup.
    **{label: [report_row] for label, report_row in SGX_FX_ASSETS.items()},
    "NEW ZEALAND DOLLAR": ["NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE"],
    'SOUTH AFRICAN RAND': ['SO AFRICAN RAND - CHICAGO MERCANTILE EXCHANGE'],
    "US DOLLAR INDEX": ["USD INDEX - ICE FUTURES U.S."]
} 

MARKETS_RATE = {
    "SOFR-1M": ["SOFR-1M - CHICAGO MERCANTILE EXCHANGE"],
    "SOFR-3M": ["SOFR-3M - CHICAGO MERCANTILE EXCHANGE"],
    "EURO SHORT TERM RATE": ["EURO SHORT TERM RATE - CHICAGO MERCANTILE EXCHANGE"],
    "ULTRA UST BOND": ["ULTRA UST BOND - CHICAGO BOARD OF TRADE"],
    "UST BOND": ["UST BOND - CHICAGO BOARD OF TRADE"],
    "UST 2Y NOTE": ["UST 2Y NOTE - CHICAGO BOARD OF TRADE"],
    "UST 5Y NOTE": ["UST 5Y NOTE - CHICAGO BOARD OF TRADE"],
    "UST 10Y NOTE": ["UST 10Y NOTE - CHICAGO BOARD OF TRADE"],
    "ULTRA UST 10Y": ["ULTRA UST 10Y - CHICAGO BOARD OF TRADE"],
    "MICRO 10 YEAR YIELD": ["MICRO 10 YEAR YIELD - CHICAGO BOARD OF TRADE"],
    "FED FUNDS": ["FED FUNDS - CHICAGO BOARD OF TRADE"]
} 

MARKETS_CRYPTO = {
    'BTC': ['BITCOIN - CHICAGO MERCANTILE EXCHANGE'],
    'MICRO BTC': ['MICRO BITCOIN - CHICAGO MERCANTILE EXCHANGE '],
    'ETH': ['ETHER CASH SETTLED - CHICAGO MERCANTILE EXCHANGE'],
    'XRP': ['XRP - CHICAGO MERCANTILE EXCHANGE '],
    'SOL': ['SOL - CHICAGO MERCANTILE EXCHANGE'],
    'DOGECOIN': ['DOGECOIN - COINBASE DERIVATIVES, LLC'],
    'CHAINLINK': ['CHAINLINK - COINBASE DERIVATIVES, LLC '],
    'AVAX': ['AVALANCHE - COINBASE DERIVATIVES, LLC']
}  

MARKETS_INDICES = {
    'VIX FUTURES': ['VIX FUTURES - CBOE FUTURES EXCHANGE'],
    'S&P 500 Consolidated': ['S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE'],
    'MICRO E-MINI S&P 500 INDEX': ['MICRO E-MINI S&P 500 INDEX - CHICAGO MERCANTILE EXCHANGE'],
    'NASDAQ MINI': ['NASDAQ MINI - CHICAGO MERCANTILE EXCHANGE'],
    'E-MINI S&P 500': ['E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE'],
    'MSCI EAFE': ['MSCI EAFE  - ICE FUTURES U.S.'],
    'MSCI EM INDEX': ['MSCI EM INDEX - ICE FUTURES U.S.'],
    'NIKKEI STOCK AVERAGE YEN DENOM': ['NIKKEI STOCK AVERAGE YEN DENOM - CHICAGO MERCANTILE EXCHANGE'],
    'BBG COMMODITY INDEX': ['BBG COMMODITY - CHICAGO BOARD OF TRADE']
}  

PARTICIPANTS_FIN = {
    "Dealers": ("Dealer_Positions_Long_All", "Dealer_Positions_Short_All"),
    "AM/FI": ("Asset_Mgr_Positions_Long_All", "Asset_Mgr_Positions_Short_All"),
    "Lev Funds": ("Lev_Money_Positions_Long_All", "Lev_Money_Positions_Short_All"),
    "Non-Rept": ("NonRept_Positions_Long_All", "NonRept_Positions_Short_All")
}

PARTICIPANTS_COM = {
    "Commercials (Prod/Merc/Proc)": ("Prod_Merc_Positions_Long_All", "Prod_Merc_Positions_Short_All"),
    "Managed Money": ("M_Money_Positions_Long_All", "M_Money_Positions_Short_All"),
    "Other Rept": ("Other_Rept_Positions_Long_All", "Other_Rept_Positions_Short_All"),
    "Non-Rept": ("NonRept_Positions_Long_All", "NonRept_Positions_Short_All")
}

PARTICIPANTS_FIN_OI = {
    "Dealers": ("Pct_of_OI_Dealer_Long_All", "Pct_of_OI_Dealer_Short_All"),
    "AM/FI": ("Pct_of_OI_Asset_Mgr_Long_All", "Pct_of_OI_Asset_Mgr_Short_All"),
    "Lev Funds": ("Pct_of_OI_Lev_Money_Long_All", "Pct_of_OI_Lev_Money_Short_All"),
    "Non-Rept": ("Pct_of_OI_NonRept_Long_All", "Pct_of_OI_NonRept_Short_All")
}

PARTICIPANTS_COM_OI = {
    "Commercials (Prod/Merc/Proc)": ("Pct_of_OI_Prod_Merc_Long_All", "Pct_of_OI_Prod_Merc_Short_All"),
    "Managed Money": ("Pct_of_OI_M_Money_Long_All", "Pct_of_OI_M_Money_Short_All"),
    "Other Rept": ("Pct_of_OI_Other_Rept_Long_All", "Pct_of_OI_Other_Rept_Short_All"),
    "Non-Rept": ("Pct_of_OI_NonRept_Long_All", "Pct_of_OI_NonRept_Short_All")
}

# Verified against the CFTC annual TFF files; codes avoid name/spacing changes.
FX_CONTRACT_CODES = {
    "MEXICAN PESO (MXN)": "095741",
    "BRAZILIAN REAL (BRL)": "102741",
}
REPORT_PREFIXES = {
    ("financial", "combined"): "com_fin_txt_",
    ("financial", "futures"): "fut_fin_txt_",
    ("commodity", "combined"): "com_disagg_txt_",
    ("commodity", "futures"): "fut_disagg_txt_",
}
DATE_COLUMN = "Report_Date_as_YYYY-MM-DD"
NAME_COLUMN = "Market_and_Exchange_Names"
CODE_COLUMN = "CFTC_Contract_Market_Code"
LOOKBACKS = (12, 18)


class DataLoadError(RuntimeError):
    """The source could not supply a usable report."""


def normalize_names(values):
    return values.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)


def prepare_report(df):
    """Keep missing positions missing, normalize names, and remove duplicate weeks."""
    required = {DATE_COLUMN, NAME_COLUMN, CODE_COLUMN}
    missing = required.difference(df.columns)
    if missing:
        raise DataLoadError(f"CFTC report is missing columns: {', '.join(sorted(missing))}")
    df = df.copy()
    df["Date"] = pd.to_datetime(df[DATE_COLUMN], errors="coerce")
    df = df.dropna(subset=["Date"])
    df[NAME_COLUMN] = normalize_names(df[NAME_COLUMN])
    df[CODE_COLUMN] = df[CODE_COLUMN].astype("string").str.strip().str.zfill(6)
    numeric_columns = {"Open_Interest_All"}
    for mapping in (PARTICIPANTS_FIN, PARTICIPANTS_COM, PARTICIPANTS_FIN_OI, PARTICIPANTS_COM_OI):
        for columns in mapping.values():
            numeric_columns.update(columns)
    for column in numeric_columns:
        if column in df:
            values = df[column].astype("string").str.replace(",", "", regex=False)
            df[column] = pd.to_numeric(values, errors="coerce")
    return df.sort_values("Date").drop_duplicates([CODE_COLUMN, "Date"], keep="last")


@st.cache_data(ttl=6 * 60 * 60, max_entries=24, show_spinner=False)
def fetch_year(year, cot_type="financial", basis="combined"):
    """Read official CFTC ZIPs in memory; no shared extracted files between users."""
    prefix = REPORT_PREFIXES[(cot_type, basis)]
    url = f"https://www.cftc.gov/files/dea/history/{prefix}{year}.zip"
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))
    try:
        with requests.Session() as session:
            session.mount("https://", HTTPAdapter(max_retries=retry))
            response = session.get(url, timeout=(10, 40))
            response.raise_for_status()
        with ZipFile(BytesIO(response.content)) as archive:
            files = [name for name in archive.namelist() if name.lower().endswith(".txt")]
            if len(files) != 1:
                raise DataLoadError(f"Unexpected contents in the CFTC archive for {year}.")
            with archive.open(files[0]) as report:
                df = pd.read_csv(report, dtype={CODE_COLUMN: "string"}, low_memory=False)
        return prepare_report(df)
    except (requests.RequestException, BadZipFile, pd.errors.ParserError) as exc:
        raise DataLoadError(f"Could not load the CFTC {year} report. Please retry later.") from exc


def fetch_cot_data(cot_type="financial", basis="combined", today=None):
    today = pd.Timestamp(today if today is not None else date.today())
    # One extra prior year covers the 18-month window around delayed reports.
    years = range(today.year - 2, today.year + 1)
    frames = [fetch_year(year, cot_type, basis) for year in years]
    return prepare_report(pd.concat(frames, ignore_index=True))


def select_market(report, asset, names):
    if asset in FX_CONTRACT_CODES:
        matches = report.loc[report[CODE_COLUMN].eq(FX_CONTRACT_CODES[asset])].copy()
    else:
        aliases = normalize_names(pd.Series(names, dtype="string"))
        matches = report.loc[report[NAME_COLUMN].isin(aliases)].copy()
    if matches[CODE_COLUMN].nunique() > 1:
        raise DataLoadError("Multiple CFTC contract codes match this label; select a specific contract code before combining them.")
    return matches.sort_values("Date")


def numeric_series(df, column):
    if column not in df:
        return pd.Series(float("nan"), index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce").astype("float64")


def participant_map(cot_type, percentage=False):
    if percentage:
        return PARTICIPANTS_FIN_OI if cot_type == "financial" else PARTICIPANTS_COM_OI
    return PARTICIPANTS_FIN if cot_type == "financial" else PARTICIPANTS_COM


def compute_percentiles(df, cot_type="financial", months_list=LOOKBACKS):
    """Rank the latest report against its own trailing window, including that report.

    Ties use scipy's 'rank' convention (average of matching ranks).
    Each metric has its own non-missing observation count.
    """
    columns = ["Participant", "Lookback", "Metric", "Value", "Percentile", "Observations", "Partial history"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    df = df.sort_values("Date")
    as_of = df["Date"].iloc[-1]
    rows = []
    for participant, (long_col, short_col) in participant_map(cot_type).items():
        long = numeric_series(df, long_col)
        short = numeric_series(df, short_col)
        for months in months_list:
            cutoff = as_of - pd.DateOffset(months=months)
            in_window = df["Date"].between(cutoff, as_of)
            for metric, values in {"Long": long, "Short": short, "Net": long - short}.items():
                history = values.loc[in_window].dropna()
                latest = values.iloc[-1]
                rank = float("nan")
                if pd.notna(latest) and not history.empty:
                    rank = float(percentileofscore(history, latest, kind="rank"))
                first_valid = df.loc[in_window & values.notna(), "Date"].min()
                partial = pd.isna(first_valid) or first_valid > cutoff + pd.Timedelta(days=7)
                rows.append({"Participant": participant, "Lookback": f"{months}m", "Metric": metric,
                             "Value": latest, "Percentile": rank, "Observations": len(history),
                             "Partial history": bool(partial)})
    return pd.DataFrame(rows, columns=columns)


def color_percentiles(value):
    if pd.isna(value):
        return ""
    value = max(0.0, min(100.0, float(value)))
    red = int(255 * (100 - value) / 100)
    green = int(255 * value / 100)
    return f"background-color: rgb({red},{green},0); color: #111111"


def style_percentiles(table):
    # Styler.applymap was removed in pandas 3.0. map works in pandas >= 2.1.
    return table.style.map(color_percentiles).format("{:.2f}", na_rep="—")


def plot_positions(asset, df, cot_type="financial", months_back=18, percentage=False):
    as_of = df["Date"].max()
    frame = df.loc[df["Date"] >= as_of - pd.DateOffset(months=months_back)]
    mapping = participant_map(cot_type, percentage)
    fig = make_subplots(rows=len(mapping), cols=1, shared_xaxes=True, subplot_titles=list(mapping))
    for row, (participant, (long_col, short_col)) in enumerate(mapping.items(), start=1):
        long, short = numeric_series(frame, long_col), numeric_series(frame, short_col)
        fig.add_trace(go.Bar(x=frame["Date"], y=long, name="Long", marker_color="#31b79a",
                             legendgroup="long", showlegend=row == 1), row=row, col=1)
        fig.add_trace(go.Bar(x=frame["Date"], y=-short, name="Short", marker_color="#ed7680",
                             legendgroup="short", showlegend=row == 1), row=row, col=1)
        fig.add_trace(go.Scatter(x=frame["Date"], y=long - short, name="Net", mode="lines",
                                 line_color="#e2b95b", connectgaps=False, legendgroup="net",
                                 showlegend=row == 1), row=row, col=1)
        fig.update_yaxes(title_text="% of OI" if percentage else "Contracts", row=row, col=1)
    fig.update_layout(height=250 * len(mapping), barmode="relative", hovermode="x unified",
                      title=f"{asset} · {months_back} months through {as_of:%Y-%m-%d}")
    return fig


def latest_positions(df, cot_type):
    rows = []
    for participant, (long_col, short_col) in participant_map(cot_type).items():
        long = numeric_series(df, long_col).iloc[-1]
        short = numeric_series(df, short_col).iloc[-1]
        long_pct_col, short_pct_col = participant_map(cot_type, True)[participant]
        long_pct = numeric_series(df, long_pct_col).iloc[-1]
        short_pct = numeric_series(df, short_pct_col).iloc[-1]
        rows.append({"Participant": participant, "Long": long, "Short": short, "Net": long - short,
                     "Long % of OI": long_pct, "Short % of OI": short_pct,
                     "Net % of OI": long_pct - short_pct})
    return pd.DataFrame(rows).set_index("Participant")


def sgx_activity_frame(report_row, basis="futures"):
    """Return published raw contract counts; never derive participant positions.

    Futures and options counts stay separate even when 'combined' is selected.
    Raw options OI cannot be converted to futures-equivalent OI without deltas.
    """
    if basis not in {"futures", "combined"}:
        raise ValueError("Unsupported report basis")
    values = SGX_MONTHLY_SNAPSHOT[report_row]
    frame = pd.DataFrame({
        "Month": pd.to_datetime(SGX_SNAPSHOT_MONTHS),
        "Futures volume": values["volume"],
        "Futures month-end OI": values["oi"],
    })
    if basis == "combined":
        frame["Options volume"] = values.get("options_volume", float("nan"))
        frame["Options month-end OI"] = values.get("options_oi", float("nan"))
    return frame


def render_sgx_fx(asset, basis):
    """SGX activity view within the existing FX Futures market page."""
    report_row = SGX_FX_ASSETS[asset]
    if asset == "USD/SGD (SGX)":
        variant = st.sidebar.selectbox("USD/SGD contract size", ["Full-sized", "Mini"])
        if variant == "Mini":
            report_row = "USD_SGD FX Futures"
    frame = sgx_activity_frame(report_row, basis)
    values = SGX_MONTHLY_SNAPSHOT[report_row]
    as_of = frame["Month"].max()
    st.subheader(f"{asset} · Monthly market activity")
    st.caption(f"SGX report row: {report_row}")
    st.markdown(f"Source: [SGX Monthly Market Statistics — August 2026]({SGX_MONTHLY_SOURCE}) · pages 20–21 and 32–34.")
    st.caption("Bundled snapshot: June–August 2026. These figures are included in this Python file and do not update automatically.")
    st.info("A public SGX FX participant long/short dataset has not been verified. This view shows trading volume and total open interest. Dealer, fund and other participant positions, net positions and positioning percentiles are unavailable.")
    if report_row == "THB_USD FX Futures":
        st.caption("Your USD/THB entry uses SGX's THB/USD contract. The published contract counts are shown unchanged; this is not an inverse price or position series.")
    if report_row == "SGD_CNH FX Futures":
        st.caption("SGX reports zero volume and zero open interest for all three displayed months. These are published zeros, not missing values.")

    if basis == "combined":
        if "options_row" in values:
            st.caption(f"Futures + options selected: the separately published options row is {values['options_row']}. Raw futures and options counts are shown separately; they are not a futures-equivalent combined positioning report.")
        else:
            st.warning("Combined data unavailable: no matching options row was verified in this monthly report. The futures component is shown; options are blank, not assumed to be zero.")
    else:
        st.caption("Report basis: Futures only · Volume and open interest are raw contract counts.")

    latest = frame.iloc[-1]
    left, right = st.columns(2)
    left.metric(f"Futures volume · {as_of:%b %Y}", f"{latest['Futures volume']:,.0f}")
    right.metric(f"Futures open interest · {as_of:%d %b %Y}", f"{latest['Futures month-end OI']:,.0f}")
    if basis == "combined" and "options_row" in values:
        left, right = st.columns(2)
        left.metric("Options volume", f"{latest['Options volume']:,.0f}")
        right.metric("Options month-end open interest", f"{latest['Options month-end OI']:,.0f}")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=["Monthly trading volume", "Month-end open interest"])
    for label, color in (("Futures", "#31b79a"), ("Options", "#e2b95b")):
        volume, oi = f"{label} volume", f"{label} month-end OI"
        if volume not in frame or frame[volume].isna().all():
            continue
        fig.add_trace(go.Bar(x=frame["Month"], y=frame[volume], name=label,
                             marker_color=color, legendgroup=label), row=1, col=1)
        fig.add_trace(go.Scatter(x=frame["Month"], y=frame[oi], name=label,
                                 mode="lines+markers", line_color=color, connectgaps=False,
                                 legendgroup=label, showlegend=False), row=2, col=1)
    fig.update_yaxes(title_text="Contracts", rangemode="tozero")
    fig.update_xaxes(tickvals=frame["Month"], tickformat="%b %Y")
    fig.update_layout(height=580, barmode="group", hovermode="x unified")
    st.plotly_chart(fig, width="stretch")
    st.caption("Volume counts contracts traded during each month; open interest is outstanding contracts at month end. Neither reveals who is long or short. The snapshot has three monthly observations, so 12/18-month percentiles are not calculated.")
    display = frame.copy()
    display["Month"] = display["Month"].dt.strftime("%Y-%m")
    formats = {column: "{:,.0f}" for column in display.columns if column != "Month"}
    st.dataframe(display.style.format(formats, na_rep="—"), hide_index=True, width="stretch")
    export = display.assign(Exchange="SGX", Contract=report_row,
                            Data_type="Monthly activity; not participant positioning",
                            Selected_basis=basis, Source_report=SGX_SNAPSHOT_MONTH,
                            Source_url=SGX_MONTHLY_SOURCE)
    safe_name = report_row.lower().replace(" ", "_").replace("/", "_")
    st.download_button("Download SGX monthly activity", export.to_csv(index=False).encode("utf-8"),
                       file_name=f"sgx_{safe_name}_{basis}_{SGX_SNAPSHOT_MONTH}.csv", mime="text/csv")


def main():
    st.set_page_config(page_title="Futures Positioning & Activity", layout="wide")
    st.title("Futures Positioning & Market Activity")
    pages = {"FX Futures": MARKETS_FX, "Rate Futures": MARKETS_RATE, "Crypto Futures": MARKETS_CRYPTO,
             "Equity Index Futures": MARKETS_INDICES, "Commodity Futures": MARKETS_COMMODITIES}
    page = st.sidebar.selectbox("Select Market Page", list(pages))
    asset = st.sidebar.selectbox(f"Select Asset ({page})", list(pages[page]))
    basis_label = st.sidebar.selectbox("Report basis", ["Futures + options combined", "Futures only"])
    basis = "combined" if basis_label == "Futures + options combined" else "futures"
    cot_type = "commodity" if page == "Commodity Futures" else "financial"
    is_sgx = asset in SGX_FX_ASSETS
    if st.sidebar.button("Refresh data", disabled=is_sgx,
                         help="SGX uses the dated snapshot embedded in this file." if is_sgx else "Download fresh CFTC reports."):
        fetch_year.clear()
    if is_sgx:
        render_sgx_fx(asset, basis)
        return
    st.caption(f"Source: CFTC · {basis_label} · Weekly report dates, not publication dates.")
    if basis == "combined":
        st.caption("Options are converted to futures-equivalent positions in the combined report.")
    try:
        with st.spinner("Loading CFTC reports…"):
            report = fetch_cot_data(cot_type, basis)
        df = select_market(report, asset, pages[page][asset])
    except DataLoadError as exc:
        logging.getLogger(__name__).exception("CFTC report load failed")
        st.error(str(exc))
        return
    if df.empty:
        st.warning(f"No matching data was found for {asset} in the loaded {basis_label.lower()} reports.")
        st.caption("The contract may be absent from this report, discontinued, or listed under a different name.")
        return
    as_of = df["Date"].max()
    source_latest = report["Date"].max()
    if as_of < source_latest:
        st.warning(f"This market's last report is {as_of:%Y-%m-%d}; the latest loaded report is {source_latest:%Y-%m-%d}. Its history may have stopped.")
    elif pd.Timestamp(date.today()) - as_of > pd.Timedelta(days=14):
        st.warning(f"The latest available report is {as_of:%Y-%m-%d}. The source may be delayed; try Refresh data.")
    expected = [column for pair in participant_map(cot_type).values() for column in pair]
    missing_columns = [column for column in expected if column not in df]
    if missing_columns:
        st.warning("Some participant fields are unavailable. Missing values are shown as blank, not zero.")
    st.subheader(f"{asset} · Latest report: {as_of:%Y-%m-%d}")
    st.caption(f"CFTC contract code: {df[CODE_COLUMN].iloc[-1]} · {df[NAME_COLUMN].iloc[-1]}")
    st.plotly_chart(plot_positions(asset, df, cot_type), width="stretch")
    st.subheader("Positions as a percentage of total open interest")
    st.plotly_chart(plot_positions(asset, df, cot_type, percentage=True), width="stretch")
    st.caption("Short bars are drawn below zero for readability. Net % of OI = long % minus short %.")
    st.subheader("Positioning percentiles")
    st.caption("Each rank compares the latest value with the preceding 12 or 18 calendar months, including the latest report. Ties use average ranks. Green means a higher percentile, including for short positions; it is not a bullish signal.")
    percentiles = compute_percentiles(df, cot_type)
    if percentiles["Partial history"].any():
        st.warning("Some metrics have less than the requested history. Their percentiles use only available observations; see counts below.")
    for participant in participant_map(cot_type):
        st.markdown(f"**{participant}**")
        subset = percentiles.loc[percentiles["Participant"] == participant]
        table = subset.pivot(index="Metric", columns="Lookback", values="Percentile").reindex(["Long", "Short", "Net"])
        table = table.reindex(columns=[f"{months}m" for months in LOOKBACKS])
        st.dataframe(style_percentiles(table), width="stretch")
    with st.expander("Observation counts and history coverage"):
        st.dataframe(percentiles[["Participant", "Lookback", "Metric", "Observations", "Partial history"]], hide_index=True)
    st.subheader("Latest participant positions")
    current = latest_positions(df, cot_type)
    formats = {column: "{:,.0f}" if column in ("Long", "Short", "Net") else "{:.2f}" for column in current.columns}
    st.dataframe(current.style.format(formats, na_rep="—"), width="stretch")
    st.caption("The four displayed participant groups are retained from the original dashboard. Financial charts omit Other Reportables; commodity charts omit Swap Dealers. They are not a complete breakdown of total open interest.")
    safe_name = asset.lower().replace(" ", "_").replace("/", "_")
    st.download_button("Download selected market history", df.to_csv(index=False).encode("utf-8"),
                       file_name=f"{safe_name}_{basis}.csv", mime="text/csv")
    st.download_button("Download percentiles", percentiles.to_csv(index=False).encode("utf-8"),
                       file_name=f"{safe_name}_{basis}_percentiles.csv", mime="text/csv")


if __name__ == "__main__":
    main()

