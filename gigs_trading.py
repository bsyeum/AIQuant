import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date, timedelta

# 한글 폰트 설정
#matplotlib.rcParams['font.family'] = 'Malgun Gothic'  # 또는 'Malgun Gothic' (Windows), 'AppleGothic' (macOS)
# 이 부분을 수정 권장
matplotlib.rcParams['font.family'] = 'DejaVu Sans'  # 또는 주석 처리

# 마이너스 깨짐 방지
matplotlib.rcParams['axes.unicode_minus'] = False

# Streamlit 설정
st.set_page_config(layout="wide", page_title="📈 ETF Chart Dashboard")
st.title("📊 ETF EMA/RSI Dashboard")

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

# 지표 계산
df['EMA_70'] = calc_ema(df['Close'], 70)
df['EMA_210'] = calc_ema(df['Close'], 210)
df['RSI'] = calc_rsi(df['Close'])

# matplotlib용 날짜 숫자 변환
df['date_num'] = mdates.date2num(df.index)

# 시각화
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

x_min = mdates.date2num(start_date)
x_max = mdates.date2num(end_date)

# 가격 + EMA 차트
ax1.plot(df['date_num'], df['Close'], label='price', color='blue')
ax1.plot(df['date_num'], df['EMA_70'], label='70 EMA', color='orange')
ax1.plot(df['date_num'], df['EMA_210'], label='210 EMA', color='green')
ax1.set_title(f"{ticker} price + EMA")
ax1.set_xlim([x_min, x_max])
ax1.legend()
ax1.grid(True)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

# RSI 차트
ax2.plot(df['date_num'], df['RSI'], label='RSI', color='purple')
ax2.axhline(70, linestyle='--', color='red', alpha=0.5)
ax2.axhline(30, linestyle='--', color='green', alpha=0.5)
ax2.set_title(f"{ticker} RSI")
ax2.set_xlim([x_min, x_max])
ax2.legend()
ax2.grid(True)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

# Streamlit에 그래프 출력
st.pyplot(fig)
