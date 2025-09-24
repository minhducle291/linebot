# from dotenv import load_dotenv
# load_dotenv()
import os
from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent, LocationMessageContent
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration, ReplyMessageRequest, PushMessageRequest
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


def push_to_source(messaging_api, source, messages):
    """
    Gửi Push theo loại nguồn: user, group, room.
    """
    to_id = None
    st = getattr(source, "type", None)
    if st == "user":
        to_id = source.user_id
    elif st == "group":
        to_id = source.group_id
    elif st == "room":
        to_id = source.room_id

    if not to_id:
        # Không xác định được nơi đẩy (ví dụ webhook xác thực)
        return False

    messaging_api.push_message(PushMessageRequest(to=to_id, messages=messages))
    return True

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

@handler.add(MessageEvent)
def on_message(event: MessageEvent):
    # 1) Không xử lý token "Verify" toàn số 0
    if event.reply_token == "00000000000000000000000000000000":
        return

    # 2) Tạo message trả lời (nhanh, không I/O nặng ở đây)
    msg_obj = event.message
    if not isinstance(msg_obj, (TextMessageContent, LocationMessageContent)):
        return

    reply_messages = handle_user_message(
        msg_obj.text if isinstance(msg_obj, TextMessageContent) else "@@LOCATION@@"
    )

    # 3) Nếu là redelivery, nhiều khả năng replyToken đã hết hạn
    is_redelivery = bool(getattr(getattr(event, "delivery_context", None), "is_redelivery", False))

    try:
        if not is_redelivery:
            # thử reply trước
            if reply_messages:
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        replyToken=event.reply_token,
                        messages=reply_messages
                    )
                )
        else:
            # redelivery: đẩy Push luôn
            push_to_source(messaging_api, event.source, reply_messages)

    except ApiException as e:
        # Nếu reply fail vì token hết hạn/invalid → fallback Push
        body = getattr(e, "body", "") or str(e)
        if "Invalid reply token" in body or "Invalid replyToken" in body or e.status == 400:
            try:
                push_to_source(messaging_api, event.source, reply_messages)
            except ApiException as e2:
                print(f"[Push Fallback Failed] {e2}")
        else:
            print(f"[LINE ApiException] {e}")

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

@app.route("/health", methods=["GET"])
def health():
    return "Bot is running!", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)