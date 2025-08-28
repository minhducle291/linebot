import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError

from handlers import handle_user_message

# ====== CONFIG ======
# LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "herfNFzmF78yjleshKI+VnDR4VyynMY3KfOvn0Z2Nj/IP2LgshLBE7FS0+aO2PXc+s4FYpjEZ/4pKjU0l2rRNuBbCFds2rJIqZPdavYfikKJFw1iPRX8+nuDlWqf02AHUdrTT0mXMqstFkoT3nZ2RgdB04t89/1O/w1cDnyilFU=")
# LINE_CHANNEL_SECRET       = os.getenv("LINE_CHANNEL_SECRET",       "3e13e8971d902f02179e669510bc7d5f")

LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET       = os.environ["LINE_CHANNEL_SECRET"]

app = Flask(__name__, static_folder="static", static_url_path="/static")

config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
api_client = ApiClient(config)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ===== ROUTES =====
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def on_message(event: MessageEvent):
    reply_messages = handle_user_message(event.message.text)  # list of messages
    if reply_messages:
        messaging_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=reply_messages
            )
        )

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
