# from dotenv import load_dotenv
# load_dotenv()
import os
from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration, ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging.exceptions import ApiException

from handlers import handle_user_message

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
    # --- Guard 1: bỏ qua token "Verify" toàn 0 từ LINE console
    if event.reply_token == "00000000000000000000000000000000":
        return

    # --- Guard 2: bỏ qua redelivery (LINE resend lại event cũ -> token đã hết hạn)
    dc = getattr(event, "delivery_context", None)
    if dc and getattr(dc, "is_redelivery", False):
        return

    reply_messages = handle_user_message(event.message.text)  # list[Message]

    if reply_messages:
        try:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=reply_messages
                )
            )
        except ApiException as e:
            # log rõ để soi các case hết hạn / double-reply
            print(f"[LINE ApiException] {e}")
            # không raise lại để tránh 500

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

@app.route("/health", methods=["GET"])
def health():
    return "Bot is running!", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)