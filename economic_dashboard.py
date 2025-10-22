"""
📊 Economic Indicators Dashboard
Interactive Streamlit dashboard for monitoring key economic indicators
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from fredapi import Fred
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Economic Indicators Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Visualization settings
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# ==================== DATA COLLECTION FUNCTIONS ====================

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_shiller_cape():
    """Collect Shiller CAPE data from web"""
    try:
        url = 'https://www.multpl.com/shiller-pe/table/by-year'
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table')
        
        if not table:
            return None
        
        data = []
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else table.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                try:
                    date = pd.to_datetime(cells[0].text.strip())
                    value = float(cells[1].text.strip())
                    data.append({'Date': date, 'CAPE': value})
                except:
                    continue
        
        df = pd.DataFrame(data).sort_values('Date').set_index('Date')
        return df['CAPE']
    except Exception as e:
        st.error(f"Failed to fetch Shiller CAPE: {e}")
        return None

@st.cache_data(ttl=3600)
def load_finra_margin_online():
    """Download FINRA Margin Debt data"""
    try:
        url = 'https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx'
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        excel_file = BytesIO(response.content)
        df = pd.read_excel(excel_file, sheet_name='Customer Margin Balances')
        
        df['Date'] = pd.to_datetime(df['Year-Month'] + '-01', format='%Y-%m-%d')
        df['Margin_Debt'] = df["Debit Balances in Customers' Securities Margin Accounts"]
        df = df.set_index('Date')[['Margin_Debt']].sort_index()
        df['Margin_Debt_YoY'] = df['Margin_Debt'].pct_change(12) * 100
        
        return df
    except Exception as e:
        st.error(f"Failed to fetch FINRA Margin data: {e}")
        return None

@st.cache_data(ttl=3600)
def get_fred_data(api_key):
    """Collect economic indicators from FRED"""
    try:
        fred = Fred(api_key=api_key)
        
        indicators = {
            'NFCI': 'Chicago Fed National Financial Conditions Index',
            'USSLIND': 'Leading Index for the United States',
            'SAHMREALTIME': 'Sahm Rule Recession Indicator',
            'T10Y3M': '10-Year Treasury minus 3-Month Treasury',
            'T10Y2Y': '10-Year Treasury minus 2-Year Treasury',
            'BAMLH0A0HYM2': 'ICE BofA US High Yield Index Option-Adjusted Spread'
        }
        
        data = {}
        for series_id, name in indicators.items():
            try:
                data[series_id] = fred.get_series(series_id, observation_start='1990-01-01')
            except:
                data[series_id] = None
        
        return data
    except Exception as e:
        st.error(f"Failed to fetch FRED data: {e}")
        return None

# ==================== VISUALIZATION FUNCTIONS ====================

def plot_cape(cape_data):
    """Plot Shiller CAPE"""
    fig, ax = plt.subplots(figsize=(15, 6))
    
    cape_clean = cape_data.dropna()
    ax.plot(cape_clean.index, cape_clean, linewidth=2, color='darkblue', label='CAPE')
    
    mean_val = cape_clean.mean()
    ax.axhline(y=mean_val, color='green', linestyle='--', alpha=0.7, 
               label=f'Historical Avg ({mean_val:.1f})')
    ax.axhline(y=25, color='orange', linestyle='--', alpha=0.5, label='Moderate (25)')
    ax.axhline(y=30, color='red', linestyle='--', alpha=0.5, label='High (30)')
    
    ax.set_title('Shiller CAPE Ratio', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('CAPE', fontsize=12)
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_margin_debt(margin_df):
    """Plot FINRA Margin Debt"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
    
    # Absolute values
    margin_clean = margin_df['Margin_Debt'].dropna()
    ax1.plot(margin_clean.index, margin_clean, linewidth=2, color='darkgreen')
    ax1.set_title('FINRA Margin Debt (Absolute)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Million USD', fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # YoY %
    margin_yoy = margin_df['Margin_Debt_YoY'].dropna()
    ax2.plot(margin_yoy.index, margin_yoy, linewidth=2, color='darkgreen')
    ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax2.axhline(y=20, color='orange', linestyle='--', alpha=0.3, label='Caution (20%)')
    ax2.set_title('Margin Debt YoY %', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Date', fontsize=12)
    ax2.set_ylabel('YoY %', fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_fred_indicator(data, title, ylabel, threshold=None):
    """Generic plot for FRED indicators"""
    fig, ax = plt.subplots(figsize=(15, 6))
    
    data_clean = data.dropna()
    ax.plot(data_clean.index, data_clean, linewidth=2, color='navy')
    
    if threshold is not None:
        ax.axhline(y=threshold, color='red', linestyle='--', alpha=0.7, 
                   label=f'Threshold ({threshold})')
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    if threshold is not None:
        ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_hy_oas(hy_data):
    """Plot HY OAS"""
    fig, ax = plt.subplots(figsize=(15, 6))
    
    hy_clean = hy_data.dropna()
    ax.plot(hy_clean.index, hy_clean, linewidth=2, color='darkred', label='HY OAS')
    ax.axhline(y=5, color='orange', linestyle='--', alpha=0.7, label='Caution (5%)')
    ax.axhline(y=10, color='red', linestyle='--', alpha=0.7, label='Danger (10%)')
    
    ax.fill_between(hy_clean.index, 5, hy_clean, 
                     where=(hy_clean>=5), alpha=0.2, color='orange')
    ax.fill_between(hy_clean.index, 10, hy_clean, 
                     where=(hy_clean>=10), alpha=0.2, color='red')
    
    ax.set_title('ICE BofA US High Yield OAS (Credit Spread)', 
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Spread (%)', fontsize=12)
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_comprehensive_dashboard(df):
    """Create comprehensive dashboard"""
    fig = plt.figure(figsize=(20, 16))
    gs = fig.add_gridspec(4, 2, hspace=0.4, wspace=0.3)
    
    # 1. CAPE
    if 'CAPE' in df.columns and df['CAPE'].notna().sum() > 0:
        ax1 = fig.add_subplot(gs[0, 0])
        cape_data = df['CAPE'].dropna()
        ax1.plot(cape_data.index, cape_data, linewidth=2, color='darkblue')
        ax1.axhline(y=cape_data.mean(), color='green', linestyle='--', alpha=0.5)
        ax1.set_title('Shiller CAPE', fontweight='bold')
        ax1.grid(True, alpha=0.3)
    
    # 2. Margin Debt YoY
    if 'Margin_Debt_YoY' in df.columns and df['Margin_Debt_YoY'].notna().sum() > 0:
        ax2 = fig.add_subplot(gs[0, 1])
        margin_yoy = df['Margin_Debt_YoY'].dropna()
        ax2.plot(margin_yoy.index, margin_yoy, linewidth=2, color='darkgreen')
        ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(y=20, color='orange', linestyle='--', alpha=0.3)
        ax2.set_title('Margin Debt YoY %', fontweight='bold')
        ax2.grid(True, alpha=0.3)
    
    # 3. NFCI
    if 'NFCI' in df.columns:
        ax3 = fig.add_subplot(gs[1, 0])
        nfci_data = df['NFCI'].dropna()
        ax3.plot(nfci_data.index, nfci_data, linewidth=2, color='navy')
        ax3.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax3.set_title('NFCI (Financial Conditions)', fontweight='bold')
        ax3.grid(True, alpha=0.3)
    
    # 4. LEI YoY
    if 'LEI' in df.columns:
        ax4 = fig.add_subplot(gs[1, 1])
        lei_data = df['LEI'].dropna()
        lei_yoy = lei_data.pct_change(12) * 100
        ax4.plot(lei_yoy.index, lei_yoy, linewidth=2, color='darkgreen')
        ax4.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax4.set_title('LEI YoY % (Leading Index)', fontweight='bold')
        ax4.grid(True, alpha=0.3)
    
    # 5. Sahm Rule
    if 'Sahm_Rule' in df.columns:
        ax5 = fig.add_subplot(gs[2, 0])
        sahm_data = df['Sahm_Rule'].dropna()
        ax5.plot(sahm_data.index, sahm_data, linewidth=2, color='darkred')
        ax5.axhline(y=0.5, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax5.set_title('Sahm Rule (Recession Indicator)', fontweight='bold')
        ax5.grid(True, alpha=0.3)
    
    # 6. Yield Curve
    if 'T10Y3M' in df.columns or 'T10Y2Y' in df.columns:
        ax6 = fig.add_subplot(gs[2, 1])
        if 'T10Y3M' in df.columns:
            t10y3m = df['T10Y3M'].dropna()
            ax6.plot(t10y3m.index, t10y3m, linewidth=2, label='10Y-3M', color='blue')
        if 'T10Y2Y' in df.columns:
            t10y2y = df['T10Y2Y'].dropna()
            ax6.plot(t10y2y.index, t10y2y, linewidth=2, label='10Y-2Y', color='green')
        ax6.axhline(y=0, color='red', linestyle='--', alpha=0.7)
        ax6.set_title('Yield Curve', fontweight='bold')
        ax6.legend(fontsize=8)
        ax6.grid(True, alpha=0.3)
    
    # 7. HY OAS
    if 'HY_OAS' in df.columns:
        ax7 = fig.add_subplot(gs[3, :])
        hy_data = df['HY_OAS'].dropna()
        ax7.plot(hy_data.index, hy_data, linewidth=2, color='darkred', label='HY OAS')
        ax7.axhline(y=5, color='orange', linestyle='--', alpha=0.7, label='Caution (5%)')
        ax7.axhline(y=10, color='red', linestyle='--', alpha=0.7, label='Danger (10%)')
        ax7.fill_between(hy_data.index, 5, hy_data, 
                         where=(hy_data>=5), alpha=0.2, color='orange')
        ax7.fill_between(hy_data.index, 10, hy_data, 
                         where=(hy_data>=10), alpha=0.2, color='red')
        ax7.set_title('HY OAS (Credit Spread)', fontweight='bold')
        ax7.set_ylabel('Spread (%)', fontsize=10)
        ax7.legend(loc='best', fontsize=8)
        ax7.grid(True, alpha=0.3)
    
    fig.suptitle('Economic Indicators Dashboard', fontsize=18, fontweight='bold', y=0.995)
    plt.tight_layout()
    return fig

def evaluate_economy(df):
    """Evaluate current economic conditions"""
    signals = []
    score = 0
    
    # CAPE
    if 'CAPE' in df.columns:
        cape_latest = df['CAPE'].dropna().iloc[-1]
        if cape_latest > 30:
            signals.append("🔴 CAPE > 30: High valuation risk")
            score -= 2
        elif cape_latest > 25:
            signals.append("🟡 CAPE > 25: Moderate valuation")
            score -= 1
        else:
            signals.append("🟢 CAPE < 25: Reasonable valuation")
            score += 1
    
    # Margin Debt YoY
    if 'Margin_Debt_YoY' in df.columns:
        margin_yoy = df['Margin_Debt_YoY'].dropna().iloc[-1]
        if margin_yoy > 20:
            signals.append("🔴 Margin Debt YoY > 20%: High leverage risk")
            score -= 2
        elif margin_yoy < 0:
            signals.append("🟡 Margin Debt YoY < 0%: Deleveraging")
            score -= 1
        else:
            signals.append("🟢 Margin Debt YoY healthy")
            score += 1
    
    # NFCI
    if 'NFCI' in df.columns:
        nfci_latest = df['NFCI'].dropna().iloc[-1]
        if nfci_latest > 0:
            signals.append("🔴 NFCI > 0: Tightening financial conditions")
            score -= 2
        else:
            signals.append("🟢 NFCI < 0: Loose financial conditions")
            score += 1
    
    # Sahm Rule
    if 'Sahm_Rule' in df.columns:
        sahm_latest = df['Sahm_Rule'].dropna().iloc[-1]
        if sahm_latest >= 0.5:
            signals.append("🔴 Sahm Rule ≥ 0.5: RECESSION SIGNAL")
            score -= 3
        else:
            signals.append("🟢 Sahm Rule < 0.5: No recession signal")
            score += 1
    
    # Yield Curve
    if 'T10Y3M' in df.columns:
        yc_latest = df['T10Y3M'].dropna().iloc[-1]
        if yc_latest < 0:
            signals.append("🔴 Yield Curve Inverted: Recession risk")
            score -= 2
        else:
            signals.append("🟢 Yield Curve Positive: Normal conditions")
            score += 1
    
    # HY OAS
    if 'HY_OAS' in df.columns:
        hy_latest = df['HY_OAS'].dropna().iloc[-1]
        if hy_latest >= 10:
            signals.append("🔴 HY OAS ≥ 10%: Extreme credit stress")
            score -= 3
        elif hy_latest >= 5:
            signals.append("🟡 HY OAS ≥ 5%: Elevated credit stress")
            score -= 1
        else:
            signals.append("🟢 HY OAS < 5%: Healthy credit market")
            score += 1
    
    # Overall assessment
    if score >= 3:
        overall = "🟢 **POSITIVE**: Economic conditions are favorable"
    elif score >= 0:
        overall = "🟡 **NEUTRAL**: Mixed signals, monitor closely"
    else:
        overall = "🔴 **NEGATIVE**: Warning signs present"
    
    return signals, overall, score

# ==================== MAIN APP ====================

def main():
    st.title("📊 Economic Indicators Dashboard")
    st.markdown("Real-time monitoring of key economic indicators")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # FRED API Key
        api_key = st.text_input(
            "FRED API Key", 
            value="75ffc1847c9070a1f903e2ba5432bb1f",
            type="password",
            help="Get your free API key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
        
        st.markdown("---")
        
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📚 Data Sources")
        st.markdown("- **CAPE**: multpl.com")
        st.markdown("- **Margin**: FINRA")
        st.markdown("- **Others**: FRED")
        
        st.markdown("---")
        st.markdown(f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Load data
    with st.spinner("Loading data..."):
        cape_data = get_shiller_cape()
        margin_df = load_finra_margin_online()
        fred_data = get_fred_data(api_key) if api_key else None
    
    # Combine all data
    df = pd.DataFrame()
    
    if cape_data is not None:
        df['CAPE'] = cape_data
    
    if margin_df is not None:
        df = df.join(margin_df, how='outer')
    
    if fred_data is not None:
        for key, value in fred_data.items():
            if value is not None:
                if key == 'USSLIND':
                    df['LEI'] = value
                elif key == 'SAHMREALTIME':
                    df['Sahm_Rule'] = value
                elif key == 'BAMLH0A0HYM2':
                    df['HY_OAS'] = value
                else:
                    df[key] = value
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard", 
        "📈 Individual Indicators", 
        "🎯 Economic Assessment",
        "💾 Data"
    ])
    
    with tab1:
        st.header("Comprehensive Dashboard")
        
        if not df.empty:
            fig = plot_comprehensive_dashboard(df)
            st.pyplot(fig)
        else:
            st.error("No data available")
    
    with tab2:
        st.header("Individual Indicators")
        
        # CAPE
        if 'CAPE' in df.columns:
            st.subheader("1️⃣ Shiller CAPE")
            fig = plot_cape(df['CAPE'])
            st.pyplot(fig)
            
            latest_cape = df['CAPE'].dropna().iloc[-1]
            col1, col2, col3 = st.columns(3)
            col1.metric("Latest CAPE", f"{latest_cape:.2f}")
            col2.metric("Historical Avg", f"{df['CAPE'].mean():.2f}")
            col3.metric("Max", f"{df['CAPE'].max():.2f}")
        
        st.markdown("---")
        
        # Margin Debt
        if margin_df is not None:
            st.subheader("2️⃣ FINRA Margin Debt")
            fig = plot_margin_debt(margin_df)
            st.pyplot(fig)
            
            latest_margin = margin_df['Margin_Debt'].iloc[-1]
            latest_yoy = margin_df['Margin_Debt_YoY'].iloc[-1]
            col1, col2 = st.columns(2)
            col1.metric("Latest Margin Debt", f"${latest_margin:,.0f}M")
            col2.metric("YoY Growth", f"{latest_yoy:.2f}%")
        
        st.markdown("---")
        
        # Other indicators
        if 'NFCI' in df.columns:
            st.subheader("3️⃣ NFCI (Financial Conditions)")
            fig = plot_fred_indicator(df['NFCI'], 'Chicago Fed NFCI', 'Index', threshold=0)
            st.pyplot(fig)
        
        if 'LEI' in df.columns:
            st.subheader("4️⃣ LEI (Leading Economic Index)")
            lei_yoy = df['LEI'].pct_change(12) * 100
            fig = plot_fred_indicator(lei_yoy, 'LEI YoY %', 'YoY %', threshold=0)
            st.pyplot(fig)
        
        if 'Sahm_Rule' in df.columns:
            st.subheader("5️⃣ Sahm Rule")
            fig = plot_fred_indicator(df['Sahm_Rule'], 'Sahm Rule Recession Indicator', 
                                     'Value', threshold=0.5)
            st.pyplot(fig)
        
        if 'HY_OAS' in df.columns:
            st.subheader("6️⃣ High Yield OAS")
            fig = plot_hy_oas(df['HY_OAS'])
            st.pyplot(fig)
    
    with tab3:
        st.header("Economic Assessment")
        
        if not df.empty:
            signals, overall, score = evaluate_economy(df)
            
            st.markdown(f"### {overall}")
            st.markdown(f"**Overall Score**: {score}")
            
            st.markdown("---")
            st.markdown("### 📋 Detailed Signals")
            
            for signal in signals:
                st.markdown(signal)
            
            # Score gauge
            st.markdown("---")
            st.markdown("### 📊 Score Interpretation")
            st.progress((score + 10) / 20)  # Normalize to 0-1
            
            if score >= 3:
                st.success("Favorable economic environment for risk assets")
            elif score >= 0:
                st.warning("Mixed signals - exercise caution")
            else:
                st.error("Warning signs - consider defensive positioning")
        else:
            st.error("No data available for assessment")
    
    with tab4:
        st.header("Data Export")
        
        if not df.empty:
            # Show recent data
            st.subheader("Recent Data (Last 10 rows)")
            st.dataframe(df.tail(10))
            
            # Download button
            csv = df.to_csv()
            st.download_button(
                label="📥 Download Full Dataset (CSV)",
                data=csv,
                file_name=f"economic_indicators_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            # Data summary
            st.subheader("Data Summary")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Data Range**")
                st.write(f"Start: {df.index.min()}")
                st.write(f"End: {df.index.max()}")
                st.write(f"Total rows: {len(df)}")
            
            with col2:
                st.markdown("**Available Indicators**")
                for col in df.columns:
                    coverage = (df[col].notna().sum() / len(df) * 100)
                    st.write(f"{col}: {coverage:.1f}% coverage")
        else:
            st.error("No data available")

if __name__ == "__main__":
    main()
