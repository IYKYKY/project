import streamlit as st
st.set_page_config(page_title="CFTC Positioning", layout="wide")
import cot_reports as cot
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import percentileofscore

# ----------------------------
# Asset and participant mappings
# ----------------------------

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
    "COTTON": ["COTTON - ICE FUTURES U.S."],
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

MARKETS_FX = {
    "EURO FX": ["EURO FX - CHICAGO MERCANTILE EXCHANGE"],
    "JAPANESE YEN": ["JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"],
    "BRITISH POUND STERLING": ["BRITISH POUND - CHICAGO MERCANTILE EXCHANGE"],
    "SWISS FRANC": ["SWISS FRANC - CHICAGO MERCANTILE EXCHANGE"],
    "CANADIAN DOLLAR": ["CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"],
    "AUSTRALIAN DOLLAR": ["AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"],
    "MEXICAN PESO": ["MEXICAN PESO - CHICAGO MERCANTILE EXCHANGE"],
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

def _strip_names(df):
    if "Market_and_Exchange_Names" in df.columns:
        df["Market_and_Exchange_Names"] = df["Market_and_Exchange_Names"].str.strip()
    return df

def _ensure_columns(df, cols):
    for c in cols:
        if c not in df.columns:
            df[c] = 0
    return df

# ----------------------------
# Fetch data
# ----------------------------
@st.cache_data
def fetch_cot_data():
    fin_df = cot.cot_all(cot_report_type="traders_in_financial_futures_futopt")
    com_df = cot.cot_all(cot_report_type="disaggregated_futopt")

    fin_df = _strip_names(fin_df)
    com_df = _strip_names(com_df)

    fin_assets = {**MARKETS_FX, **MARKETS_RATE, **MARKETS_CRYPTO, **MARKETS_INDICES}
    asset_dfs_fin, asset_dfs_com = {}, {}

    # financial
    for asset, exact_names in fin_assets.items():
        target = [n.strip() for n in exact_names]
        matches = fin_df[fin_df["Market_and_Exchange_Names"].isin(target)]
        if not matches.empty:
            asset_dfs_fin[asset] = matches.copy()

    # commodities
    for asset, exact_names in MARKETS_COMMODITIES.items():
        target = [n.strip() for n in exact_names]
        matches = com_df[com_df["Market_and_Exchange_Names"].isin(target)]
        if not matches.empty:
            # ensure the 4 columns exist even if missing in this market/week
            need = []
            for a,b in PARTICIPANTS_COM.values():
                need += [a,b]
            matches = _ensure_columns(matches.copy(), need)
            asset_dfs_com[asset] = matches

    return asset_dfs_fin, asset_dfs_com



# ----------------------------
# Compute percentiles
# ----------------------------
def compute_latest_percentiles(asset_dfs, months_list=[12, 18], cot_type="financial"):
    summary_list = []
    participants_map = PARTICIPANTS_FIN if cot_type == "financial" else PARTICIPANTS_COM

    for asset, df in asset_dfs.items():
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Report_Date_as_YYYY-MM-DD"], errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date")
        latest_row = df.iloc[-1]

        total_long = sum(latest_row[cols[0]] for cols in participants_map.values())
        total_short = sum(latest_row[cols[1]] for cols in participants_map.values())
        total_net = total_long - total_short

        asset_summary = {
            "asset": asset,
            "total_long": int(total_long),
            "total_short": int(total_short),
            "total_net": int(total_net)
        }

        for months in months_list:
            cutoff = pd.Timestamp.today() - pd.DateOffset(months=months)
            df_hist = df[df["Date"] >= cutoff]

            for p_name, (long_col, short_col) in participants_map.items():
                long_val = latest_row.get(long_col, 0)
                short_val = latest_row.get(short_col, 0)
                net_val = long_val - short_val

                long_pct = percentileofscore(df_hist[long_col].dropna(), long_val)
                short_pct = percentileofscore(df_hist[short_col].dropna(), short_val)
                net_pct = percentileofscore((df_hist[long_col]-df_hist[short_col]).dropna(), net_val)

                asset_summary[f"{p_name} Long Percentile {months}m"] = round(long_pct, 2)
                asset_summary[f"{p_name} Short Percentile {months}m"] = round(short_pct, 2)
                asset_summary[f"{p_name} Net Percentile {months}m"] = round(net_pct, 2)

        summary_list.append(asset_summary)
    return pd.DataFrame(summary_list)

# ----------------------------
# Plot 4 stacked charts
# ----------------------------
def plot_4rows(asset, asset_dfs, cot_type="financial", months_back=18):
    df = asset_dfs[asset].copy()
    df["Date"] = pd.to_datetime(df["Report_Date_as_YYYY-MM-DD"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")
    df = df[df["Date"] >= pd.Timestamp.today() - pd.DateOffset(months=months_back)]

    participants_map = PARTICIPANTS_FIN if cot_type == "financial" else PARTICIPANTS_COM
    fig = make_subplots(rows=len(participants_map), cols=1,
                        subplot_titles=list(participants_map.keys()))
    row = 1
    for p_name, (long_col, short_col) in participants_map.items():
        fig.add_trace(go.Bar(x=df["Date"], y=df.get(long_col, 0),   name=f"{p_name} Long"),  row=row, col=1)
        fig.add_trace(go.Bar(x=df["Date"], y=-df.get(short_col, 0), name=f"{p_name} Short"), row=row, col=1)
        net_val = df.get(long_col, 0) - df.get(short_col, 0)
        fig.add_trace(go.Scatter(x=df["Date"], y=net_val, mode="lines", name=f"{p_name} Net"), row=row, col=1)
        row += 1

    fig.update_layout(height=280*len(participants_map), barmode="relative",
                      title=dict(text=f"{asset} Positions (Last {months_back} Months)", x=0.5))
    return fig

def plot_oi_4rows(asset, asset_dfs, cot_type="financial", months_back=18):
    df = asset_dfs[asset].copy()
    df["Date"] = pd.to_datetime(df["Report_Date_as_YYYY-MM-DD"], errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")
    df = df[df["Date"] >= pd.Timestamp.today() - pd.DateOffset(months=months_back)]

    participants_map = PARTICIPANTS_FIN_OI if cot_type == "financial" else PARTICIPANTS_COM_OI
    fig = make_subplots(rows=len(participants_map), cols=1,
                        subplot_titles=list(participants_map.keys()))
    row = 1
    for p_name, (long_col, short_col) in participants_map.items():
        fig.add_trace(go.Bar(x=df["Date"], y=df.get(long_col, 0),   name=f"{p_name} Long OI"),  row=row, col=1)
        fig.add_trace(go.Bar(x=df["Date"], y=-df.get(short_col, 0), name=f"{p_name} Short OI"), row=row, col=1)
        net_oi = df.get(long_col, 0) - df.get(short_col, 0)
        fig.add_trace(go.Scatter(x=df["Date"], y=net_oi, mode="lines", name=f"{p_name} Net OI"), row=row, col=1)
        row += 1

    fig.update_layout(height=280*len(participants_map), barmode="relative",
                      title=dict(text=f"{asset} Open Interest (Last {months_back} Months)", x=0.5))
    return fig






# ----------------------------
# Streamlit App
# ----------------------------
st.title("CFTC Markets Participants Positioning")

asset_dfs_fin, asset_dfs_com = fetch_cot_data()
percentiles_fin = compute_latest_percentiles(asset_dfs_fin, cot_type="financial")
percentiles_com = compute_latest_percentiles(asset_dfs_com, cot_type="commodity")

pages = {
    "FX Futures": MARKETS_FX,
    "Rate Futures": MARKETS_RATE,
    "Crypto Futures": MARKETS_CRYPTO,
    "Equity Index Futures": MARKETS_INDICES,
    "Commodity Futures": MARKETS_COMMODITIES
}

page = st.sidebar.selectbox("Select Market Page", list(pages.keys()))
assets = list(pages[page].keys())
selected_asset = st.sidebar.selectbox(f"Select Asset ({page})", assets)

# Choose which asset_dfs and percentiles_df to use
if page == "Commodity Futures":
    df_dict = asset_dfs_com
    pct_df = percentiles_com
    cot_type = "commodity"
else:
    df_dict = asset_dfs_fin
    pct_df = percentiles_fin
    cot_type = "financial"

# Get latest available date for this asset
latest_date = None
if selected_asset in df_dict:
    df_temp = df_dict[selected_asset].copy()
    df_temp["Date"] = pd.to_datetime(df_temp["Report_Date_as_YYYY-MM-DD"], errors="coerce")
    df_temp = df_temp.dropna(subset=["Date"])
    if not df_temp.empty:
        latest_date = df_temp["Date"].max().strftime("%Y-%m-%d")

# ----------------------------
# Show Charts
# ----------------------------
st.subheader(f"{selected_asset} Positioning" + (f" (Latest: {latest_date})" if latest_date else ""))
st.plotly_chart(plot_4rows(selected_asset, df_dict, cot_type=cot_type, months_back=18))

# ----------------------------
# Show Open Interest Charts
# ----------------------------
st.subheader(f"{selected_asset} OI Percentages" + (f" (Latest: {latest_date})" if latest_date else ""))
st.plotly_chart(plot_oi_4rows(selected_asset, df_dict, cot_type=cot_type, months_back=18))


# ----------------------------
# Show Percentiles
# ----------------------------
st.subheader(f"{selected_asset} Positioning Percentiles" + (f" (Latest: {latest_date})" if latest_date else ""))
participants_map = PARTICIPANTS_FIN if cot_type == "financial" else PARTICIPANTS_COM

def color_percentiles(val):
    """Red (0%) → Green (100%)"""
    if pd.isna(val):
        return ''
    red = int(255 * (100 - val) / 100)
    green = int(255 * val / 100)
    return f'background-color: rgb({red},{green},0)'

for p_name, _ in participants_map.items():
    st.markdown(f"**{p_name}**")
    # Get all participant columns, exclude 'asset'
    cols = [col for col in pct_df.columns if col.startswith(p_name)]
    df_show = pct_df[pct_df["asset"] == selected_asset][cols].copy()
    
    # Apply color styling
    styled_df = df_show.style.applymap(color_percentiles).format("{:.2f}")
    
    # Render without index
    st.markdown(styled_df.hide(axis="index").to_html(), unsafe_allow_html=True)

# ----------------------------
# Show Open Interest Section
# ----------------------------
if latest_date:
    st.subheader(f"{selected_asset} OI (Latest: {latest_date})")
else:
    st.subheader(f"{selected_asset} OI")

if selected_asset in df_dict:
    df_temp = df_dict[selected_asset].copy()
    df_temp["Date"] = pd.to_datetime(df_temp["Report_Date_as_YYYY-MM-DD"], errors="coerce")
    df_temp = df_temp.dropna(subset=["Date"]).sort_values("Date")

    if not df_temp.empty:
        latest_row = df_temp.iloc[-1]

        # Map participants
        participants_map = PARTICIPANTS_FIN if cot_type == "financial" else PARTICIPANTS_COM

        for p_name, (long_col, short_col) in participants_map.items():
            st.markdown(f"**{p_name}**")

            # Construct dictionary for OI + Pct of OI
            oi_data = {
                "Long OI": latest_row.get(long_col, 0),
                "Short OI": latest_row.get(short_col, 0),
                "Net OI": latest_row.get(long_col, 0) - latest_row.get(short_col, 0),
                "% Long OI": latest_row.get(f"Pct_of_OI_{long_col.replace('_Positions_', '_')}", 0),
                "% Short OI": latest_row.get(f"Pct_of_OI_{short_col.replace('_Positions_', '_')}", 0),
                "% Net OI": (latest_row.get(f"Pct_of_OI_{long_col.replace('_Positions_', '_')}", 0)
                             - latest_row.get(f"Pct_of_OI_{short_col.replace('_Positions_', '_')}", 0))
            }

            st.dataframe(pd.DataFrame([oi_data]), use_container_width=True, hide_index=True)

    else:
        st.info("No open interest data available for this asset.")
