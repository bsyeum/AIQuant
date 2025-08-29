import streamlit as st
import numpy as np
import pandas as pd
import warnings
import yfinance as yf
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings('ignore')

# Streamlit 페이지 설정
st.set_page_config(
    page_title="Trading Strategy Dashboard",
    page_icon="📊",
    layout="wide"
)

# 제목
st.title("📊 Trading Strategy Dashboard")
st.markdown("---")

# 사이드바 - 파라미터 설정
st.sidebar.header("📋 Strategy Parameters")

# Mean Reversion Strategy Parameters
st.sidebar.subheader("Mean Reversion Strategy")
param1 = st.sidebar.slider("Rolling Window (param1)", min_value=5, max_value=30, value=10)
param2 = st.sidebar.slider("Band Multiplier (param2)", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
param3 = st.sidebar.slider("IBS Threshold (param3)", min_value=0.1, max_value=1.0, value=0.5, step=0.1)

# Date Range
st.sidebar.subheader("📅 Date Range")
start_date = st.sidebar.date_input("Start Date", value=datetime(2024, 1, 1))
end_date = st.sidebar.date_input("End Date", value=datetime.now())

# Refresh Button
if st.sidebar.button("🔄 Refresh Data", type="primary"):
    st.cache_data.clear()

@st.cache_data
def get_mean_reversion_data(tickers, start_date, end_date, param1, param2, param3):
    """Mean Reversion 전략 데이터 계산"""
    weights_df = pd.DataFrame()
    individual_data = {}
    
    for ticker in tickers:
        try:
            # 단일 ticker로 다운로드
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if df.empty:
                st.warning(f"No data available for {ticker}")
                continue
            
            # --- FIX: MultiIndex 컬럼 처리 로직 개선 ---
            # yfinance가 가끔 단일 티커에 대해서도 MultiIndex를 반환하는 경우에 대비
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            df.index = pd.to_datetime(df.index)
            position = 0
            
            # 계산 진행
            hl_avg = df['High'].rolling(window=param1).mean() - df['Low'].rolling(window=param1).mean()
            band = df['Close'].rolling(window=param1).mean() - (hl_avg * param2)
            ibs = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
            
            df['HL_avg'] = hl_avg
            df['Band'] = band
            df['IBS'] = ibs
            df['Position'] = np.nan
            
            # Position 계산
            for i in range(len(df.index)):
                if i >= param1:
                    close_val = df['Close'].iloc[i]
                    band_val = df['Band'].iloc[i]
                    ibs_val = df['IBS'].iloc[i]
                    
                    if pd.notna(close_val) and pd.notna(band_val) and pd.notna(ibs_val):
                        if (close_val <= band_val) and (ibs_val <= param3):
                            position += 1
                            df.loc[df.index[i], 'Position'] = position
                        elif (position > 0) and (close_val >= df['Close'].iloc[i-1]):
                            position = 0
                            df.loc[df.index[i], 'Position'] = position
                        else:
                            df.loc[df.index[i], 'Position'] = position
                    else:
                        df.loc[df.index[i], 'Position'] = position
            
            # weights_df에 추가
            if weights_df.empty:
                weights_df = pd.DataFrame(index=df.index)
            weights_df[ticker] = df['Position']
            individual_data[ticker] = df
            
        except Exception as e:
            st.error(f"Error processing {ticker}: {str(e)}")
            continue
    
    return weights_df, individual_data

@st.cache_data
def get_vix_data(start_date, end_date):
    """VIX Tail-Risk 전략 데이터 계산"""
    try:
        tickers = ['^GSPC', '^VIX', '^VIX3M']
        vc_df = yf.download(tickers, start=start_date, end=end_date)['Close']
        vc_df.ffill(inplace=True)
        vc_df.columns = ['SPX', 'VIX', 'VIX3M']
        vc_df.index = pd.to_datetime(vc_df.index)
        
        RV = vc_df['SPX'].pct_change().rolling(2).std() * np.sqrt(252) * 100
        VRP = vc_df['VIX'] - RV
        VTS = vc_df['VIX3M'] / vc_df['VIX']
        
        final_vc_df = pd.concat([vc_df['VIX'], VRP, VTS], axis=1, join='inner')
        final_vc_df.columns = ['VIX', 'VRP', 'VTS']
        final_vc_df['weight'] = np.where((final_vc_df['VRP'] < 0) & (final_vc_df['VTS'] < 1), 
                                         final_vc_df['VIX'] / 100 * 1, 0)
        
        return final_vc_df, vc_df
    except Exception as e:
        st.error(f"Error downloading VIX data: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# Main Content
col1, col2 = st.columns(2)

with col1:
    st.header("📈 Mean Reversion Strategy")
    
    # Mean Reversion Strategy 실행
    tickers = ['SPY', 'QQQ']
    weights_df, individual_data = get_mean_reversion_data(tickers, start_date, end_date, param1, param2, param3)
    
    if not weights_df.empty:
        # 현재 포지션 표시
        st.subheader("🎯 Current Positions")
        latest_positions = weights_df.iloc[-1].fillna(0) if len(weights_df) > 0 else pd.Series(dtype='float64')
        
        col_spy, col_qqq = st.columns(2)
        with col_spy:
            spy_pos = latest_positions.get('SPY', 0)
            st.metric("SPY Position", f"{spy_pos:.0f}")
        
        with col_qqq:
            qqq_pos = latest_positions.get('QQQ', 0)
            st.metric("QQQ Position", f"{qqq_pos:.0f}")
        
        # 포지션 차트
        st.subheader("📊 Position History")
        fig_pos = go.Figure()
        
        for ticker in tickers:
            if ticker in weights_df.columns:
                fig_pos.add_trace(go.Scatter(
                    x=weights_df.index,
                    y=weights_df[ticker],
                    mode='lines',
                    name=ticker,
                    line=dict(width=2)
                ))
        
        fig_pos.update_layout(
            title="Position Over Time",
            xaxis_title="Date",
            yaxis_title="Position Size",
            hovermode='x unified'
        )
        st.plotly_chart(fig_pos, use_container_width=True)
        
        # 개별 종목 상세 정보
        if individual_data:
            st.subheader("📋 Individual Stock Analysis")
            selected_ticker = st.selectbox("Select Ticker for Detailed View", tickers)
            
            if selected_ticker in individual_data:
                stock_data = individual_data[selected_ticker]
                
                # 가격과 밴드 차트
                fig_stock = make_subplots(
                    rows=3, cols=1,
                    subplot_titles=(f'{selected_ticker} Price & Band', 'IBS Indicator', 'Position'),
                    row_heights=[0.5, 0.25, 0.25],
                    shared_xaxes=True
                )
                
                # 가격과 밴드
                fig_stock.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Close'], 
                                             name='Close', line=dict(color='blue')), row=1, col=1)
                fig_stock.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Band'], 
                                             name='Band', line=dict(color='red', dash='dash')), row=1, col=1)
                
                # IBS
                fig_stock.add_trace(go.Scatter(x=stock_data.index, y=stock_data['IBS'], 
                                             name='IBS', line=dict(color='green')), row=2, col=1)
                fig_stock.add_hline(y=param3, line_dash="dash", line_color="red", 
                                  annotation_text=f"Threshold ({param3})", row=2, col=1)
                
                # Position
                fig_stock.add_trace(go.Scatter(x=stock_data.index, y=stock_data['Position'], 
                                             name='Position', line=dict(color='orange')), row=3, col=1)
                
                fig_stock.update_layout(height=800, showlegend=True)
                st.plotly_chart(fig_stock, use_container_width=True)

with col2:
    st.header("🌪️ VIX Tail-Risk Strategy")
    
    # VIX Strategy 실행
    final_vc_df, vc_df = get_vix_data(start_date, end_date)
    
    # Initialize variables to avoid errors if data is empty
    current_weight = 0
    current_vix = 0
    current_vrp = 0
    current_vts = 0

    if not final_vc_df.empty:
        # 현재 신호 표시
        st.subheader("⚡ Current Signal")
        current_weight = final_vc_df['weight'].iloc[-1]
        current_vix = final_vc_df['VIX'].iloc[-1]
        current_vrp = final_vc_df['VRP'].iloc[-1]
        current_vts = final_vc_df['VTS'].iloc[-1]
        
        col_vix1, col_vix2 = st.columns(2)
        with col_vix1:
            st.metric("VIX Level", f"{current_vix:.2f}")
            st.metric("VRP", f"{current_vrp:.2f}")
        
        with col_vix2:
            st.metric("VTS", f"{current_vts:.3f}")
            st.metric("Weight", f"{current_weight:.3f}", 
                      delta="SIGNAL ON" if current_weight > 0 else "SIGNAL OFF")
        
        # VIX 관련 차트
        st.subheader("📊 VIX Analysis")
        
        fig_vix = make_subplots(
            rows=3, cols=1,
            subplot_titles=('VIX Level', 'VRP (Volatility Risk Premium)', 'VTS (Term Structure) & Weight'),
            row_heights=[0.4, 0.3, 0.3],
            shared_xaxes=True
        )
        
        # VIX
        fig_vix.add_trace(go.Scatter(x=final_vc_df.index, y=final_vc_df['VIX'], 
                                     name='VIX', line=dict(color='blue', width=2)), row=1, col=1)
        
        # VRP
        fig_vix.add_trace(go.Scatter(x=final_vc_df.index, y=final_vc_df['VRP'], 
                                     name='VRP', line=dict(color='green')), row=2, col=1)
        fig_vix.add_hline(y=0, line_dash="dash", line_color="red", row=2, col=1)
        
        # VTS and Weight
        fig_vix.add_trace(go.Scatter(x=final_vc_df.index, y=final_vc_df['VTS'], 
                                     name='VTS', line=dict(color='purple')), row=3, col=1)
        fig_vix.add_trace(go.Scatter(x=final_vc_df.index, y=final_vc_df['weight'], 
                                     name='Weight', line=dict(color='red', width=3)), row=3, col=1)
        fig_vix.add_hline(y=1, line_dash="dash", line_color="gray", row=3, col=1)
        
        fig_vix.update_layout(height=800, showlegend=True)
        st.plotly_chart(fig_vix, use_container_width=True)
        
        # 신호 조건 설명
        st.subheader("📋 Signal Conditions")
        st.write("**Signal triggers when:**")
        st.write("- VRP < 0 (VIX < Realized Volatility)")
        st.write("- VTS < 1 (VIX > VIX3M)")
        st.write("- Weight = VIX / 100")
        
        # 최근 신호 발생 날짜들
        recent_signals = final_vc_df[final_vc_df['weight'] > 0].tail(10)
        if not recent_signals.empty:
            st.subheader("🚨 Recent Signal Days")
            st.dataframe(recent_signals[['VIX', 'VRP', 'VTS', 'weight']], use_container_width=True)

# 하단 - 종합 정보
st.markdown("---")
st.header("📊 Summary Dashboard")

col_summary1, col_summary2, col_summary3, col_summary4 = st.columns(4)

with col_summary1:
    active_positions = 0
    if not weights_df.empty:
        latest_pos = weights_df.iloc[-1].fillna(0)
        active_positions = int((latest_pos > 0).sum())
    st.metric("Active Mean Reversion Positions", active_positions)

with col_summary2:
    vix_signal_status = "ON" if current_weight > 0 else "OFF"
    st.metric("VIX Tail-Risk Signal", vix_signal_status)

with col_summary3:
    signal_pct = 0.0
    if not final_vc_df.empty:
        signal_days = (final_vc_df['weight'] > 0).sum()
        total_days = len(final_vc_df)
        if total_days > 0:
            signal_pct = (signal_days / total_days * 100)
    st.metric("VIX Signal Frequency", f"{signal_pct:.1f}%")

with col_summary4:
    st.metric("Data Updated", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# 데이터 테이블 (선택사항)
if st.checkbox("📋 Show Raw Data"):
    tab1, tab2 = st.tabs(["Mean Reversion Data", "VIX Data"])
    
    with tab1:
        if not weights_df.empty:
            st.subheader("Mean Reversion Weights")
            st.dataframe(weights_df.tail(20), use_container_width=True)
    
    with tab2:
        if not final_vc_df.empty:
            st.subheader("VIX Strategy Data")
            st.dataframe(final_vc_df.tail(20), use_container_width=True)

# Footer
st.markdown("---")
st.markdown("*Dashboard updates automatically when parameters change. Use the refresh button to get latest market data.*")
