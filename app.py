# app.py
import os, time, json, hmac, hashlib, base64, random
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, abort
from urllib3.exceptions import ProtocolError

# LINE v3 SDK
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage, StickerMessage
)
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent, PostbackEvent, LocationMessageContent
)

from handlers import handle_user_message, handle_postback, handle_location_message

# =========================
# ENV & CONFIG
# =========================
# from dotenv import load_dotenv
# load_dotenv()

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

if not CHANNEL_SECRET or not CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("Missing LINE credentials (LINE_CHANNEL_SECRET / LINE_CHANNEL_ACCESS_TOKEN).")

print(f"[boot] SECRET set? {bool(CHANNEL_SECRET)} | TOKEN set? {bool(CHANNEL_ACCESS_TOKEN)}")

app = Flask(__name__)
handler = WebhookHandler(CHANNEL_SECRET)
CFG = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

# xử lý nền: tránh request thread bị giữ lâu bởi tác vụ nặng (đọc file, vẽ ảnh…)
executor = ThreadPoolExecutor(max_workers=2)

# =========================
# TIỆN ÍCH
# =========================
def _verify_signature(secret: str, body: str, signature: str) -> bool:
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature)

def _safe_reply(event, messages) -> bool:
    """Reply 1 lần; nếu lỗi mạng (ProtocolError) retry 1 lần. Chỉ reply (không push)."""
    if not messages:
        messages = [TextMessage(text="(không có nội dung)")]
    try:
        with ApiClient(CFG) as c:
            MessagingApi(c).reply_message(
                ReplyMessageRequest(reply_token=event.reply_token, messages=messages)
            )
        return True
    except Exception as e:
        body = str(e)
        # Invalid/expired reply token -> bỏ qua (thường do xử lý lâu)
        if "Invalid reply token" in body or "Invalid replyToken" in body:
            print("[reply] invalid/expired replyToken -> drop")
            return False
        # Lỗi mạng “Remote end closed connection…” -> retry 1 lần
        if isinstance(e, ProtocolError) or "Remote end closed connection" in body:
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

class TTLSet:
    """Chống trùng đơn giản với TTL + giới hạn kích thước."""
    def __init__(self, ttl_sec=300, max_items=5000):
        self.ttl = ttl_sec
        self.max = max_items
        self.data = OrderedDict()
    def add(self, key):
        now = time.time()
        self.data[key] = now
        self.data.move_to_end(key)
        # evict theo TTL/kích thước
        cutoff = now - self.ttl
        while self.data and (len(self.data) > self.max or next(iter(self.data.values())) < cutoff):
            self.data.popitem(last=False)
    def __contains__(self, key):
        ts = self.data.get(key)
        return ts is not None and (time.time() - ts) <= self.ttl

_seen = TTLSet(ttl_sec=300, max_items=5000)

def _make_dedupe_key(event) -> str:
    mid = getattr(getattr(event, "message", None), "id", None)
    return f"msg:{mid}" if mid else f"rtok:{event.reply_token}"

def _is_redelivery(event) -> bool:
    dc = getattr(event, "delivery_context", None)
    return bool(dc and getattr(dc, "is_redelivery", False))

# =========================
# HANDLERS
# =========================
@handler.add(MessageEvent, message=TextMessageContent)
def on_message(event: MessageEvent):
    # Skip verify ping
    if event.reply_token == "00000000000000000000000000000000":
        return
    # Bỏ sự kiện retry cũ từ LINE
    if _is_redelivery(event):
        print("[message] redelivery -> skip")
        return
    # Chống trùng
    key = _make_dedupe_key(event)
    if key in _seen:
        return
    _seen.add(key)

    text = event.message.text
    print(f"[message] from={getattr(getattr(event,'source',None),'user_id',None)} text={text!r}")
    msgs = handle_user_message(text)
    _safe_reply(event, msgs)

@handler.add(PostbackEvent)
def on_postback(event: PostbackEvent):
    if event.reply_token == "00000000000000000000000000000000":
        return
    if _is_redelivery(event):
        print("[postback] redelivery -> skip")
        return
    key = _make_dedupe_key(event)
    if key in _seen:
        return
    _seen.add(key)

    data = getattr(getattr(event, "postback", None), "data", "") or ""
    print(f"[postback] data={data}")
    msgs = handle_postback(data)
    _safe_reply(event, msgs)

@handler.add(MessageEvent, message=LocationMessageContent)
def on_location(event: MessageEvent):
    if event.reply_token == "00000000000000000000000000000000":
        return
    if _is_redelivery(event):
        print("[location] redelivery -> skip")
        return
    key = _make_dedupe_key(event)
    if key in _seen:
        return
    _seen.add(key)

    lat = event.message.latitude
    lon = event.message.longitude
    print(f"[location] user={getattr(getattr(event,'source',None),'user_id',None)} lat={lat}, lon={lon}")
    msgs = handle_location_message(lat, lon)
    _safe_reply(event, msgs)


# =========================
# ROUTES
# =========================
@app.post("/callback")
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    # 1) verify nhanh
    if not _verify_signature(CHANNEL_SECRET, body, signature):
        print("[callback] signature verify failed")
        abort(400)
    # 2) đẩy xử lý vào thread để trả 200 ngay
    executor.submit(handler.handle, body, signature)
    return "Bot is running", 200

@app.get("/")
def home():
    return "Bot is running", 200

@app.get("/health")
def health_check():
    return "Bot is healthy", 200

# =========================
# LOCAL RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
