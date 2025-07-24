import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta

# Streamlit 설정
st.set_page_config(layout="wide", page_title="📈 ETF Chart Dashboard")
st.title("📊 ETF Technical Dashboard")

# 사이드바: ETF 선택
st.sidebar.header("설정")
etf_list = [
    'ACWI','SPY','QQQ','SMH', 'BBJP', 'EFA', 'IEMG', 'MCHI', 'IWM', 'VGK' ,'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XBI', 'XLU',
    'XLP', 'XLY', 'KRE', 'XLB', 'XLC', 'ARKK', 'ARKF', 'CRPT', 'XRT', 'XOP', 'XLRE', 'XHB', 'KBE', 'XME',
    'KIE', 'XSD', 'XAR', 'XES'
]
ticker = st.sidebar.selectbox("ETF 선택", etf_list)

# 날짜 선택
start_default = date(2020, 1, 1)
end_default = date.today()
date_range = st.sidebar.slider(
    "날짜 범위 선택",
    min_value=start_default,
    max_value=end_default,
    value=(start_default, end_default),
    format="YYYY-MM-DD"
)
start_date, end_date = date_range

# 지표 계산 함수
def calc_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 데이터 다운로드
st.text(f"{ticker} 데이터 로딩 중...")
df = yf.download(ticker, start=start_date, end=end_date + timedelta(days=1))
st.text(f"✅ {ticker} 데이터 로딩 완료")

# 데이터 유효성 확인
if df.empty:
    st.warning("데이터가 없습니다. 다른 날짜나 ETF를 선택해주세요.")
    st.stop()

# 멀티인덱스 컬럼 처리 (yfinance가 멀티인덱스로 반환하는 경우)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(1)

# 지표 계산
df['EMA_70'] = calc_ema(df['Close'], 70)
df['EMA_210'] = calc_ema(df['Close'], 210)
df['RSI'] = calc_rsi(df['Close'])

# 골든 크로스/데드 크로스 계산
df['EMA_70_prev'] = df['EMA_70'].shift(1)
df['EMA_210_prev'] = df['EMA_210'].shift(1)

# 골든 크로스: 70일 EMA가 210일 EMA를 위로 뚫고 올라가는 지점
df['golden_cross'] = (
    (df['EMA_70'] > df['EMA_210']) & 
    (df['EMA_70_prev'] <= df['EMA_210_prev'])
)

# 데드 크로스: 70일 EMA가 210일 EMA를 아래로 뚫고 내려가는 지점
df['dead_cross'] = (
    (df['EMA_70'] < df['EMA_210']) & 
    (df['EMA_70_prev'] >= df['EMA_210_prev'])
)

# 골든 크로스/데드 크로스 발생 지점 추출
golden_cross_points = df[df['golden_cross'] == True]
dead_cross_points = df[df['dead_cross'] == True]

# Plotly 인터랙티브 차트 생성
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.1,
    subplot_titles=(f'{ticker} Price + EMA', f'{ticker} RSI'),
    row_heights=[0.7, 0.3]
)

# 가격 + EMA 차트 (상단)
fig.add_trace(
    go.Scatter(x=df.index, y=df['Close'], 
               line=dict(color='blue', width=2),
               name='Price',
               yaxis='y1'),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(x=df.index, y=df['EMA_70'], 
               line=dict(color='orange', width=1.5),
               name='70 EMA',
               yaxis='y1'),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(x=df.index, y=df['EMA_210'], 
               line=dict(color='green', width=1.5),
               name='210 EMA',
               yaxis='y1'),
    row=1, col=1
)

# 골든 크로스 표시 (상단 차트에 추가)
if not golden_cross_points.empty:
    fig.add_trace(
        go.Scatter(
            x=golden_cross_points.index, 
            y=golden_cross_points['Close'],
            mode='markers',
            marker=dict(color='gold', size=12, symbol='triangle-up'),
            name='Golden Cross',
            yaxis='y1'
        ),
        row=1, col=1
    )

# 데드 크로스 표시 (상단 차트에 추가)
if not dead_cross_points.empty:
    fig.add_trace(
        go.Scatter(
            x=dead_cross_points.index, 
            y=dead_cross_points['Close'],
            mode='markers',
            marker=dict(color='red', size=12, symbol='triangle-down'),
            name='Dead Cross',
            yaxis='y1'
        ),
        row=1, col=1
    )

# RSI 차트 (하단)
fig.add_trace(
    go.Scatter(x=df.index, y=df['RSI'], 
               line=dict(color='purple', width=2),
               name='RSI',
               yaxis='y2'),
    row=2, col=1
)

# RSI 70, 30 기준선
fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)

# 차트 레이아웃 설정
fig.update_layout(
    title=f"{ticker} Interactive Chart",
    height=800,
    showlegend=True,
    template="plotly_white",
    # 드래그 모드를 zoom으로 설정
    dragmode='zoom',
    # 범위 선택 버튼 추가
    xaxis=dict(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(step="all")
            ])
        ),
        rangeslider=dict(visible=False),
        type="date"
    )
)

# Y축 설정 및 확대/축소 활성화
fig.update_xaxes(fixedrange=False)
fig.update_yaxes(fixedrange=False, row=1, col=1)  # Price 차트 Y축
fig.update_yaxes(range=[0, 100], fixedrange=False, row=2, col=1)  # RSI Y축

# RSI Y축 범위 설정
fig.update_yaxes(range=[0, 100], row=2, col=1)

# Streamlit에 인터랙티브 차트 출력
config = {
    'scrollZoom': True,  # 휠 확대/축소 활성화
    'displayModeBar': True,  # 툴바 표시
    'modeBarButtonsToAdd': ['pan2d', 'select2d']
}
st.plotly_chart(fig, use_container_width=True, config=config)

# 사용법 안내
st.markdown("""
### 📋 차트 사용법:
- **🖱️ 박스 드래그**: 영역 선택해서 확대
- **🔍 더블클릭**: 전체 범위로 복원  
- **📅 버튼**: 1M, 3M, 6M, 1Y 빠른 선택
- **🖱️ 휠 (차트 위에서)**: 확대/축소
- **📊 범례**: 클릭해서 선택적 표시/숨김
- **🔧 툴바**: 확대/이동/선택 도구 사용
""")

st.info("💡 **팁**: 차트 영역에 마우스를 올린 후 휠을 사용하면 확대/축소됩니다!")

# ETF 골든 크로스 상태 표 생성
st.markdown("---")
st.subheader("📊 ETF 골든 크로스 상태표")

@st.cache_data(ttl=3600)  # 1시간 캐시
def get_etf_status():
    status_data = []
    
    # 진행 상태 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, etf in enumerate(etf_list):
        try:
            status_text.text(f"분석 중: {etf} ({i+1}/{len(etf_list)})")
            
            # 최근 1년 데이터만 가져와서 속도 향상
            temp_df = yf.download(etf, period="1y", progress=False)
            
            if temp_df.empty:
                continue
                
            # 멀티인덱스 처리
            if isinstance(temp_df.columns, pd.MultiIndex):
                temp_df.columns = temp_df.columns.droplevel(1)
            
            # EMA 계산
            temp_df['EMA_70'] = calc_ema(temp_df['Close'], 70)
            temp_df['EMA_210'] = calc_ema(temp_df['Close'], 210)
            
            # 최신 데이터
            latest = temp_df.iloc[-1]
            latest_price = latest['Close']
            latest_70 = latest['EMA_70']
            latest_210 = latest['EMA_210']
            
            # 현재 상태 판단
            if pd.isna(latest_70) or pd.isna(latest_210):
                status = "데이터 부족"
            elif latest_70 > latest_210:
                status = "Golden Cross"
            else:
                status = "Dead Cross"
            
            # RSI 계산
            rsi_value = calc_rsi(temp_df['Close']).iloc[-1]
            
            # 과매수/과매도 판단
            if pd.isna(rsi_value):
                rsi_status = "데이터 부족"
            elif rsi_value >= 70:
                rsi_status = "과매수"
            elif rsi_value <= 30:
                rsi_status = "과매도"
            else:
                rsi_status = "중립"
            
            status_data.append({
                'ETF': etf,
                'EMA상태': status,
                'RSI': f"{rsi_value:.1f}" if not pd.isna(rsi_value) else "N/A",
                'RSI상태': rsi_status,
                '현재가': f"${latest_price:.2f}"
            })
            
        except Exception as e:
            st.write(f"⚠️ {etf} 데이터 오류: {str(e)}")
            continue
        
        # 진행률 업데이트
        progress_bar.progress((i + 1) / len(etf_list))
    
    # 진행 상태 정리
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(status_data)

# 상태표 생성 및 표시
if st.button("🔄 ETF 상태 업데이트", type="primary"):
    st.cache_data.clear()

status_df = get_etf_status()

if not status_df.empty:
    # 컬럼별로 스타일 적용
    def highlight_status(row):
        styles = [''] * len(row)
        
        # EMA 상태 색상
        if row['EMA상태'] == 'Golden Cross':
            styles[1] = 'background-color: #90EE90'  # 연한 초록
        elif row['EMA상태'] == 'Dead Cross':
            styles[1] = 'background-color: #FFB6C1'  # 연한 빨강
        
        # RSI 상태 색상
        if row['RSI상태'] == '과매수':
            styles[3] = 'background-color: #FFB6C1'  # 연한 빨강
        elif row['RSI상태'] == '과매도':
            styles[3] = 'background-color: #90EE90'  # 연한 초록
        
        return styles
    
    styled_df = status_df.style.apply(highlight_status, axis=1)
    st.dataframe(styled_df, use_container_width=True)
    
    # 요약 통계
    col1, col2, col3 = st.columns(3)
    
    with col1:
        golden_count = len(status_df[status_df['EMA상태'] == 'Golden Cross'])
        st.metric("🟢 Golden Cross", f"{golden_count}개")
    
    with col2:
        dead_count = len(status_df[status_df['EMA상태'] == 'Dead Cross'])
        st.metric("🔴 Dead Cross", f"{dead_count}개")
    
    with col3:
        oversold_count = len(status_df[status_df['RSI상태'] == '과매도'])
        st.metric("💎 과매도", f"{oversold_count}개")

else:
    st.warning("데이터를 가져올 수 없습니다.")

# 데이터 정보 확인 (디버깅용)
st.write("데이터 구조:", df.columns.tolist())
st.write("데이터 샘플:", df.head())


