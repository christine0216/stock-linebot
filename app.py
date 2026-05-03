from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageSendMessage, QuickReply, QuickReplyButton, 
    MessageAction, FlexSendMessage, URIAction
)
from stock import get_stock_reply, get_news
from dotenv import load_dotenv
import os
from stock import get_stock_reply

load_dotenv()

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        user_msg = event.message.text.strip()
        parts = user_msg.split()

        if len(parts) == 1 and parts[0].isdigit():
            stock_id = parts[0]
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=(
                        f"📈 {stock_id} 股票查詢\n"
                        "══════════════\n"
                        "💰 價格：查詢最新收盤價\n"
                        "📊 K線：查看K線圖（紅漲綠跌）\n"
                        "📉 成交量：查看每日交易量\n"
                        "📈 均線：MA5/MA20/MA60趨勢\n"
                        "🔢 KD：KD指標（>80超買 <20超賣）\n"
                        "📉 RSI：強弱指標（>70超買 <30超賣）\n"
                        "📰 新聞：查看最新相關新聞\n"
                        "🔍 分析：綜合指標給出買賣建議\n"
                        "══════════════\n"
                        "👇 請點選下方功能："
                    ),
                    quick_reply=QuickReply(items=[
                        QuickReplyButton(action=MessageAction(label="💰 價格", text=f"{stock_id} 價格")),
                        QuickReplyButton(action=MessageAction(label="📊 K線", text=f"{stock_id} K線")),
                        QuickReplyButton(action=MessageAction(label="📉 成交量", text=f"{stock_id} 成交量")),
                        QuickReplyButton(action=MessageAction(label="📈 均線", text=f"{stock_id} 均線")),
                        QuickReplyButton(action=MessageAction(label="🔢 KD", text=f"{stock_id} KD")),
                        QuickReplyButton(action=MessageAction(label="📉 RSI", text=f"{stock_id} RSI")),
                        QuickReplyButton(action=MessageAction(label="📰 新聞", text=f"{stock_id} 新聞")),
                        QuickReplyButton(action=MessageAction(label="🔍 分析", text=f"{stock_id} 分析")),
                    ])
                )
            )
            return

        # 新聞用Flex Message
        if len(parts) == 2 and parts[1] == "新聞":
            stock_id = parts[0]
            news_list = get_news(stock_id)
            
            if not news_list:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="找不到相關新聞"))
                return
            
            # 建立新聞卡片
            bubbles = []
            for news in news_list:
                bubble = {
                    "type": "bubble",
                    "size": "kilo",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📰 " + stock_id + " 新聞",
                                "weight": "bold",
                                "color": "#1DB446",
                                "size": "sm"
                            },
                            {
                                "type": "text",
                                "text": news['title'],
                                "wrap": True,
                                "size": "sm",
                                "margin": "md"
                            }
                        ]
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "uri",
                                    "label": "閱讀更多",
                                    "uri": news['link']
                                },
                                "style": "primary",
                                "color": "#1DB446"
                            }
                        ]
                    }
                }
                bubbles.append(bubble)
            
            flex_message = FlexSendMessage(
                alt_text=f"{stock_id} 最新新聞",
                contents={
                    "type": "carousel",
                    "contents": bubbles
                }
            )
            
            follow_up = TextSendMessage(
                text=f"還想查詢 {stock_id} 的其他資訊嗎？",
                quick_reply=QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="💰 價格", text=f"{stock_id} 價格")),
                    QuickReplyButton(action=MessageAction(label="📊 K線", text=f"{stock_id} K線")),
                    QuickReplyButton(action=MessageAction(label="📉 成交量", text=f"{stock_id} 成交量")),
                    QuickReplyButton(action=MessageAction(label="📈 均線", text=f"{stock_id} 均線")),
                    QuickReplyButton(action=MessageAction(label="🔢 KD", text=f"{stock_id} KD")),
                    QuickReplyButton(action=MessageAction(label="📉 RSI", text=f"{stock_id} RSI")),
                    QuickReplyButton(action=MessageAction(label="🔍 分析", text=f"{stock_id} 分析")),
                ])
            )
            
            line_bot_api.reply_message(event.reply_token, [flex_message, follow_up])
            return
        result = get_stock_reply(user_msg)
        stock_id = parts[0]

        # 查詢完後再跳出按鈕
        follow_up = TextSendMessage(
            text=f"還想查詢 {stock_id} 的其他資訊嗎？",
            quick_reply=QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="💰 價格", text=f"{stock_id} 價格")),
                QuickReplyButton(action=MessageAction(label="📊 K線", text=f"{stock_id} K線")),
                QuickReplyButton(action=MessageAction(label="📉 成交量", text=f"{stock_id} 成交量")),
                QuickReplyButton(action=MessageAction(label="📈 均線", text=f"{stock_id} 均線")),
                QuickReplyButton(action=MessageAction(label="🔢 KD", text=f"{stock_id} KD")),
                QuickReplyButton(action=MessageAction(label="📉 RSI", text=f"{stock_id} RSI")),
                QuickReplyButton(action=MessageAction(label="📰 新聞", text=f"{stock_id} 新聞")),
                QuickReplyButton(action=MessageAction(label="🔍 分析", text=f"{stock_id} 分析")),
            ])
        )

        if result[0] == "text":
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(text=result[1]),
                follow_up
            ])
        elif result[0] == "image":
            line_bot_api.reply_message(event.reply_token, [
                ImageSendMessage(
                    original_content_url=result[1],
                    preview_image_url=result[1]
                ),
                follow_up
            ])
    except Exception as e:
        print(f"錯誤：{e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"錯誤：{str(e)}"))

if __name__ == "__main__":
    app.run(port=5000)