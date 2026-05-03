import matplotlib
matplotlib.use('Agg')  # 不使用視窗介面
import matplotlib.pyplot as plt
import yfinance as yf
import mplfinance as mpf
import requests
import os
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
urllib3.disable_warnings()  # 關掉SSL警告訊息

def upload_image(image_path):
    for i in range(3):
        try:
            with open(image_path, 'rb') as f:
                response = requests.post(
                    'https://litterbox.catbox.moe/resources/internals/api.php',
                    data={'reqtype': 'fileupload', 'time': '72h'},
                    files={'fileToUpload': f},
                    timeout=30,
                    verify=False
                )
            url = response.text.strip()
            if url.startswith('https://'):
                return url
        except Exception as e:
            print(f"上傳重試 {i+1}/3：{e}")
            import time
            time.sleep(2)
    raise Exception("圖片上傳失敗，請稍後再試")
    
    

# ── 父類別 ──
class exc_rsl:
    def __init__(self, stock_id, period="3mo"):
        self.stock_id = stock_id + ".TW"
        self.df = yf.download(self.stock_id, period=period)

# ── 子類別：K線圖 ──
class KLine(exc_rsl):
    def plot(self):
        path = "kline.png"
        df = self.df.copy()
        df.columns = df.columns.droplevel(1)  # 修正欄位格式
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df = df.astype(float)
        mpf.plot(df, type='candle', savefig=path, style='charles')
        return path

# ── 子類別：成交量 ──
class Volume(exc_rsl):
    def plot(self):
        df = self.df.copy()
        df.columns = df.columns.droplevel(1)
        
        volume = df['Volume']
        diff = volume.diff()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 成交量柱狀圖（漲紅跌綠）
        colors = ['red' if d >= 0 else 'green' for d in diff]
        ax.bar(df.index, volume, color=colors, label='Volume')
        
        # 成交量變化折線
        ax.plot(df.index, volume, color='black', linewidth=0.5)
        
        ax.set_title(f'Stock Volume Analysis')
        ax.set_xlabel('Date')
        ax.set_ylabel('Volume (Shares)')
        ax.legend()
        
        path = "volume.png"
        fig.savefig(path)
        plt.close()
        return path
# ── 子類別：均線 ──
class MALine(exc_rsl):
    def plot(self):
        df = self.df.copy()
        df.columns = df.columns.droplevel(1)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(df.index, df['Close'], label='Close', color='black', linewidth=1)
        ax.plot(df.index, df['Close'].rolling(5).mean(), label='MA5', color='red', linewidth=1)
        ax.plot(df.index, df['Close'].rolling(20).mean(), label='MA20', color='blue', linewidth=1)
        ax.plot(df.index, df['Close'].rolling(60).mean(), label='MA60', color='green', linewidth=1)
        
        ax.set_title('Moving Average')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.legend()
        
        path = "ma.png"
        fig.savefig(path)
        plt.close()
        return path    

# ── KD值 ──
# ── KD值 ──
class KD(exc_rsl):
    def calculate_kd(self):
        df = self.df.copy()
        df.columns = df.columns.droplevel(1)
        df = df.dropna()
        
        low_min = df['Low'].rolling(9).min()
        high_max = df['High'].rolling(9).max()
        rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
        rsv = rsv.fillna(50)
        
        K_values = [50]
        D_values = [50]
        
        for r in rsv.iloc[1:]:
            k = (2 / 3) * K_values[-1] + (1 / 3) * r
            K_values.append(k)
        
        K_series = pd.Series(K_values, index=df.index)
        
        for k in K_series.iloc[1:]:
            d = (2 / 3) * D_values[-1] + (1 / 3) * k
            D_values.append(d)
        
        D_series = pd.Series(D_values, index=df.index)
        
        df['K'] = K_series
        df['D'] = D_series
        return df

    def plot(self):
        df = self.calculate_kd()
        
        # 只取最近3個月
        df = df.iloc[-60:]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index, df['K'], label='K', color='blue')
        ax.plot(df.index, df['D'], label='D', color='orange')
        ax.axhline(y=80, color='red', linestyle='--', label='Overbought(80)')
        ax.axhline(y=20, color='green', linestyle='--', label='Oversold(20)')
        ax.set_title('KD Indicator')
        ax.set_xlabel('Date')
        ax.set_ylabel('Value')
        ax.set_ylim(0, 100)
        ax.legend()
        
        path = "kd.png"
        fig.savefig(path)
        plt.close()
        return path
    
# ── 抓取個股新聞 ──
def get_news(stock_id):
    url = f"https://tw.stock.yahoo.com/quote/{stock_id}/news"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    news_items = soup.select('h3 a')[:3]
    
    if not news_items:
        return []
    
    news_list = []
    for item in news_items:
        title = item.get_text()
        href = item['href']
        if href.startswith('http'):
            link = href
        else:
            link = "https://tw.stock.yahoo.com" + href
        news_list.append({'title': title, 'link': link})
    
    return news_list

# ── RSI ──
class RSI(exc_rsl):
    def plot(self):
        df = self.df.copy()
        df.columns = df.columns.droplevel(1)
        df = df.dropna()
        
        # 計算RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 只取最近3個月
        rsi = rsi.iloc[-60:]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(rsi.index, rsi, label='RSI', color='purple')
        ax.axhline(y=70, color='red', linestyle='--', label='Overbought(70)')
        ax.axhline(y=30, color='green', linestyle='--', label='Oversold(30)')
        ax.set_title('RSI Indicator')
        ax.set_xlabel('Date')
        ax.set_ylabel('Value')
        ax.set_ylim(0, 100)
        ax.legend()
        
        path = "rsi.png"
        fig.savefig(path)
        plt.close()
        return path
    
# ── 綜合分析 ──
def get_analysis(stock_id):
    try:
        ticker = yf.Ticker(stock_id + ".TW")
        hist = ticker.history(period="6mo")
        df = hist.copy()
        
        # 現價與漲跌
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = current_price - prev_price
        change_pct = (change / prev_price) * 100
        
        # 均線
        ma5 = df['Close'].rolling(5).mean().iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        ma60 = df['Close'].rolling(60).mean().iloc[-1]
        
        # 成交量
        vol_today = df['Volume'].iloc[-1]
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_ratio = vol_today / vol_avg
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # KD
        low_min = df['Low'].rolling(9).min()
        high_max = df['High'].rolling(9).max()
        rsv = (df['Close'] - low_min) / (high_max - low_min) * 100
        rsv = rsv.fillna(50)
        K_values = [50]
        D_values = [50]
        for r in rsv.iloc[1:]:
            k = (2/3) * K_values[-1] + (1/3) * r
            K_values.append(k)
        K_series = pd.Series(K_values, index=df.index)
        for k in K_series.iloc[1:]:
            d = (2/3) * D_values[-1] + (1/3) * k
            D_values.append(d)
        D_series = pd.Series(D_values, index=df.index)
        k_val = K_series.iloc[-1]
        d_val = D_series.iloc[-1]
        
        # 52週高低
        high_52w = df['High'].max()
        low_52w = df['Low'].min()
        
        # 評分系統
        score = 0
        signals = []
        
        # 均線判斷
        if current_price > ma5:
            score += 1
            signals.append("✅ 股價站上MA5")
        else:
            score -= 1
            signals.append("❌ 股價跌破MA5")
            
        if current_price > ma20:
            score += 1
            signals.append("✅ 股價站上MA20")
        else:
            score -= 1
            signals.append("❌ 股價跌破MA20")
            
        if current_price > ma60:
            score += 1
            signals.append("✅ 股價站上MA60")
        else:
            score -= 1
            signals.append("❌ 股價跌破MA60")
        
        # RSI判斷
        if rsi < 30:
            score += 2
            signals.append(f"✅ RSI={rsi:.1f} 超賣，反彈機會大")
        elif rsi > 70:
            score -= 2
            signals.append(f"❌ RSI={rsi:.1f} 超買，注意回檔風險")
        else:
            signals.append(f"➡️ RSI={rsi:.1f} 處於中性區間")
        
        # KD判斷
        if k_val < 20:
            score += 2
            signals.append(f"✅ KD={k_val:.1f} 超賣區，留意反彈")
        elif k_val > 80:
            score -= 2
            signals.append(f"❌ KD={k_val:.1f} 超買區，注意風險")
        else:
            signals.append(f"➡️ KD={k_val:.1f} 中性區間")
        
        # 黃金/死亡交叉
        if k_val > d_val:
            score += 1
            signals.append("✅ KD黃金交叉，偏多訊號")
        else:
            score -= 1
            signals.append("❌ KD死亡交叉，偏空訊號")
        
        # 成交量判斷
        if vol_ratio > 1.5:
            signals.append(f"📊 成交量為均量的{vol_ratio:.1f}倍，市場活躍")
        elif vol_ratio < 0.5:
            signals.append(f"📊 成交量萎縮，市場觀望")
        else:
            signals.append(f"📊 成交量正常")
        
        # 綜合建議
        if score >= 4:
            suggestion = "🟢 強烈建議買入"
        elif score >= 2:
            suggestion = "🟢 建議買入"
        elif score <= -4:
            suggestion = "🔴 強烈建議賣出"
        elif score <= -2:
            suggestion = "🔴 建議賣出"
        else:
            suggestion = "🟡 建議觀望"
        
        # 漲跌符號
        arrow = "▲" if change >= 0 else "▼"
        
        result = (
            f"📊 {stock_id} 綜合分析\n"
            f"══════════════\n"
            f"💵 現價：{current_price:.2f} 元\n"
            f"📈 漲跌：{arrow} {abs(change):.2f} ({change_pct:+.2f}%)\n"
            f"📅 52週高：{high_52w:.2f} / 低：{low_52w:.2f}\n"
            f"══════════════\n"
            f"📉 技術指標\n"
            f"MA5：{ma5:.2f} | MA20：{ma20:.2f} | MA60：{ma60:.2f}\n"
            f"RSI：{rsi:.1f} | K：{k_val:.1f} | D：{d_val:.1f}\n"
            f"══════════════\n"
            f"🔍 訊號分析\n"
        )
        result += "\n".join(signals)
        result += (
            f"\n══════════════\n"
            f"📝 評分：{score}/8\n"
            f"{suggestion}\n"
            f"══════════════\n"
            f"⚠️ 以上僅供參考，投資需謹慎"
        )
        
        return result
        
    except Exception as e:
        return f"分析失敗：{str(e)}"
    
# ── 主要處理函數 ──
def get_stock_reply(msg):
    parts = msg.strip().split()

    if len(parts) != 2:
        return ("text", "請輸入格式：股票代號 功能\n例如：2330 價格\n2330 K線")

    stock_id = parts[0]
    query = parts[1]

    if query == "價格":
        try:
            ticker = yf.Ticker(stock_id + ".TW")
            hist = ticker.history(period="5d")
            
            today = hist.iloc[-1]
            prev = hist.iloc[-2]
            
            open_price = today['Open']
            close_price = today['Close']
            high_price = today['High']
            low_price = today['Low']
            volume = today['Volume']
            
            change = close_price - prev['Close']
            change_pct = (change / prev['Close']) * 100
            arrow = "▲" if change >= 0 else "▼"
            
            return ("text", (
                f"📈 {stock_id} 今日行情\n"
                f"══════════════\n"
                f"開盤：{open_price:.2f} 元\n"
                f"收盤：{close_price:.2f} 元\n"
                f"最高：{high_price:.2f} 元\n"
                f"最低：{low_price:.2f} 元\n"
                f"══════════════\n"
                f"漲跌：{arrow} {abs(change):.2f} 元\n"
                f"漲跌幅：{change_pct:+.2f}%\n"
                f"成交量：{int(volume):,} 股"
            ))
        except Exception as e:
            return ("text", f"價格查詢失敗：{str(e)}")

    elif query == "K線":
        try:
            k = KLine(stock_id)
            path = k.plot()
            url = upload_image(path)
            os.remove(path)
            return ("image", url)
        except Exception as e:
            return ("text", f"K線查詢失敗：{str(e)}")
    
    elif query == "成交量":
        try:
            v = Volume(stock_id)
            path = v.plot()
            url = upload_image(path)
            os.remove(path)
            return ("image", url)
        except Exception as e:
            return ("text", f"成交量查詢失敗：{str(e)}")
        
    elif query == "新聞":
        try:
            news = get_news(stock_id)
            return ("text", news)
        except Exception as e:
            return ("text", f"新聞查詢失敗：{str(e)}")
    
    elif query == "均線":
        try:
            ma = MALine(stock_id)
            path = ma.plot()
            url = upload_image(path)
            os.remove(path)
            return ("image", url)
        except Exception as e:
            return ("text", f"均線查詢失敗：{str(e)}")
        
    elif query == "KD":
        try:
            kd = KD(stock_id)
            path = kd.plot()
            url = upload_image(path)
            os.remove(path)
            return ("image", url)
        except Exception as e:
            return ("text", f"KD查詢失敗：{str(e)}")

    elif query == "分析":
        return ("text", get_analysis(stock_id))
    
    elif query == "RSI":
        try:
            rsi = RSI(stock_id)
            path = rsi.plot()
            url = upload_image(path)
            os.remove(path)
            return ("image", url)
        except Exception as e:
            return ("text", f"RSI查詢失敗：{str(e)}")
    
    else:
        return ("text", "目前支援功能：價格、K線\n例如：2330 K線")