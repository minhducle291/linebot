import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent, LocationMessageContent
from handlers import handle_user_message, handle_postback, handle_location_message

# ===== LOAD ENV =====
from dotenv import load_dotenv
load_dotenv()
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

print(f"[boot] SECRET set? {bool(CHANNEL_SECRET)} | TOKEN set? {bool(CHANNEL_ACCESS_TOKEN)}")

# ===== APP / LINE =====
app = Flask(__name__)
handler = WebhookHandler(CHANNEL_SECRET)
CFG = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

def reply(event, messages):
    if not messages:
        messages = [TextMessage(text="(không có nội dung)")]
    try:
        with ApiClient(CFG) as c:
            MessagingApi(c).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=messages
                )
            )
        print("[reply] OK")
    except Exception as e:
        # In ra lỗi từ LINE SDK (hay gặp nhất: invalid/expired replyToken)
        print(f"[reply][ERROR] {e}")


@handler.add(MessageEvent, message=TextMessageContent)
def on_message(event: MessageEvent):
    text = event.message.text
    print(f"[message] from={getattr(getattr(event,'source',None),'user_id',None)} text={text!r}")
    msgs = handle_user_message(text)
    return reply(event, msgs)

@handler.add(PostbackEvent)
def on_postback(event: PostbackEvent):
    data = getattr(getattr(event, "postback", None), "data", "") or ""
    print(f"[postback] data={data}")
    msgs = handle_postback(data)
    return reply(event, msgs)

@handler.add(MessageEvent, message=LocationMessageContent)
def on_location(event: MessageEvent):
    lat = event.message.latitude
    lon = event.message.longitude
    print(f"[location] user={getattr(getattr(event,'source',None),'user_id',None)} lat={lat}, lon={lon}")

    msgs = handle_location_message(lat, lon)
    return reply(event, msgs)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    print(f"[callback] signature? {bool(signature)} | body_len={len(body)}")
    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f"[callback][ERROR] {e}")
        abort(400)
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
