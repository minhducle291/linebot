# from dotenv import load_dotenv
# load_dotenv()
import os, time
from flask import Flask, request, abort
from urllib3.exceptions import ProtocolError
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
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

CFG = Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"])

def safe_reply(event, messages) -> bool:
    """Reply 1 lần; nếu lỗi mạng (ProtocolError) thì retry 1 lần.
       Không Push. Trả True nếu đã gửi được, False nếu không."""
    if not messages:
        return False
    try:
        # Mỗi lần gửi tạo client mới để tránh socket keep-alive bị stale sau khi idle lâu
        with ApiClient(CFG) as c:
            MessagingApi(c).reply_message(
                ReplyMessageRequest(replyToken=event.reply_token, messages=messages)
            )
        return True
    except ApiException as e:
        # Nếu token hết hạn/invalid -> chịu, không push
        body = getattr(e, "body", "") or str(e)
        if "Invalid reply token" in body or "Invalid replyToken" in body or e.status == 400:
            print("[reply] invalid/expired replyToken -> drop")
            return False
        print(f"[reply] ApiException: {e}")
        return False
    except Exception as e:
        # Lỗi mạng "Remote end closed connection without response" -> retry 1 lần
        if isinstance(e, ProtocolError) or "Remote end closed connection" in str(e):
            try:
                time.sleep(0.5)
                with ApiClient(CFG) as c:
                    MessagingApi(c).reply_message(
                        ReplyMessageRequest(replyToken=event.reply_token, messages=messages)
                    )
                return True
            except Exception as e2:
                print(f"[reply] retry failed: {e2}")
                return False
        print(f"[reply] unexpected error: {e}")
        return False

# (khuyên dùng) chống trùng tối giản theo message.id, tránh xử lý/redelivery lặp
_seen = set()
def make_key(event):
    mid = getattr(getattr(event, "message", None), "id", None)
    return f"msg:{mid}" if mid else f"rtok:{event.reply_token}"


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
    # Bỏ sự kiện Verify từ console
    if event.reply_token == "00000000000000000000000000000000":
        return

    # Bỏ qua redelivery để khỏi gửi lại (vì không dùng Push)
    dc = getattr(event, "delivery_context", None)
    if dc and getattr(dc, "is_redelivery", False):
        print("[event] redelivery -> skip (reply-only mode)")
        return

    # Chống trùng tối giản
    key = make_key(event)
    if key in _seen:
        return
    _seen.add(key)

    # Tạo message TRƯỚC, tránh xử lý nặng làm hết hạn token
    reply_messages = handle_user_message(event.message.text)

    # Gửi (reply-only). Nếu fail do token hết hạn -> chấp nhận rớt tin.
    safe_reply(event, reply_messages)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

@app.route("/health", methods=["GET"])
def health():
    return "Bot is running!", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)