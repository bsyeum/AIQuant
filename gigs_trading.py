import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta

# Streamlit 설정
st.set_page_config(layout="wide", page_title="📈 ETF Chart Dashboard")
st.title("📊 ETF EMA/RSI Interactive Dashboard")

# 사이드바: ETF 선택
st.sidebar.header("설정")
etf_list = [
    'ARKK', 'ARKF', 'CRPT', 'SMH', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XBI', 'XLU',
    'XLP', 'XLY', 'KRE', 'XLB', 'XLC', 'XRT', 'XOP', 'XLRE', 'XHB', 'KBE', 'XME',
    'KIE', 'XSD', 'XAR', 'XES', 'KCE', 'XNTK', 'XHE', 'XSW', 'XPH', 'XTN', 'XHS',
    'XITK', 'XTL'
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

# 데이터 정보 확인 (디버깅용)
st.write("데이터 구조:", df.columns.tolist())
st.write("데이터 샘플:", df.head())

# 지표 계산
df['EMA_70'] = calc_ema(df['Close'], 70)
df['EMA_210'] = calc_ema(df['Close'], 210)
df['RSI'] = calc_rsi(df['Close'])

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
