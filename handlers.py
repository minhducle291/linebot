import re
import hashlib
import threading, time
import pandas as pd
from urllib.parse import urljoin
from linebot.v3.messaging import TextMessage, ImageMessage, StickerMessage, LocationMessage, QuickReply, QuickReplyItem, MessageAction
from utils import df_to_image, df_nhapban_to_image, nearest_stores
import os
from datetime import datetime

# URL public (ngrok/domain)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://linebot-qer1.onrender.com")
#PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://finer-mantis-allowed.ngrok-free.app")

def number_of_the_day():
    # Chuỗi ngày, ví dụ '2025-09-25'
    today = datetime.today().strftime("%Y-%m-%d")

    # Băm ngày bằng md5 → cho ra chuỗi hex dài
    h = hashlib.md5(today.encode()).hexdigest()

    # Lấy 4 ký tự cuối, convert sang số
    num = int(h[-4:], 16) % 100

    return f"{num:02d}"  # đảm bảo luôn 2 chữ số

def handle_user_message(user_text: str):
    """
    Trả về list các message (TextMessage, ImageMessage, ...) tùy theo nội dung user_text
    """
    messages = []

    # Trường hợp 1: tin nhắn chứa '@@' => trả text
    if "@@" in user_text:
        messages.append(TextMessage(text=f"Bạn vừa nhắn: {user_text}"))

    elif "/xinso" in user_text:
        num = number_of_the_day()
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        gif_url = urljoin(PUBLIC_BASE_URL + "/", f"static/magic.gif?v={ts}")

        messages.append(TextMessage(text="Người anh em chờ tôi xíu!"))
        messages.append(ImageMessage(original_content_url=gif_url, preview_image_url=gif_url))
        messages.append(TextMessage(text=f"Con số may mắn hôm nay là {num}"))
        messages.append(StickerMessage(package_id="6325", sticker_id="10979924"))

    # Trường hợp 2: tin nhắn chứa '!' và có số => vẽ ảnh gửi
    elif "/thongtinchiahang" in user_text:
        match = re.search(r"\d+", user_text)
        if match:
            store_number = int(match.group())
            df = pd.read_parquet("data.parquet")
            ngay_cap_nhat = df['Ngày cập nhật'].iloc[0]
            df = df[df["Mã siêu thị"] == store_number][["Tên sản phẩm","Min chia","Số mua","Trạng thái chia hàng"]]
            #df = df.sort_values(by=["Trạng thái chia hàng", "Tên sản phẩm"])
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"table_thongtinchiahang_{store_number}_{ts}.png"
            out_path = f"static/{filename}"
            df_to_image(df, outfile=out_path, title=f"Thông tin chia hàng thủy sản ST: {store_number}\n(dữ liệu cập nhật ngày {ngay_cap_nhat})")

            img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
            messages.append(TextMessage(text=f"Đây là bảng chia hàng thủy sản cho siêu thị {store_number} (theo đvt của sản phẩm):"))
            messages.append(
                ImageMessage(
                    original_content_url=img_url,
                    preview_image_url=img_url
                )
            )

    elif "/ketquabanhang" in user_text:
        match = re.search(r"\d+", user_text)
        if match:
            store_number = int(match.group())
            df = pd.read_parquet("data_nhapban.parquet")
            tu_ngay = df['Từ ngày'].iloc[0]
            den_ngay = df['Đến ngày'].iloc[0]
            df = df[df["Mã siêu thị"] == store_number][["Nhóm sản phẩm","Nhu cầu","PO","Nhập","Bán","% Nhập/PO","% Bán/Nhập","Số chia hiện tại"]]
            df = df.sort_values(by=["Nhập"], ascending=False)
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"table_ketquabanhang_{store_number}_{ts}.png"
            out_path = f"static/{filename}"
            df_nhapban_to_image(df, outfile=out_path, title=f"Thông tin nhập - bán hàng thủy sản ST: {store_number} (đơn vị KG)\n(dữ liệu từ {tu_ngay} đến {den_ngay})")

            img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
            messages.append(TextMessage(text=f"Đây là bảng thông tin nhập - bán hàng thủy sản cho siêu thị {store_number} (đơn vị KG):"))
            #messages.append(ImageMessage(originalContentUrl=img_url, previewImageUrl=img_url))
            messages.append(
                ImageMessage(
                    original_content_url=img_url,
                    preview_image_url=img_url
                )
            )

    # Trường hợp khác: trả text mặc định
    else:
        messages.append(TextMessage(text="Hãy nhập /lệnh + mã siêu thị để xem báo cáo!\nVí dụ:\n/thongtinchiahang 7300\n/ketquabanhang 7300"))
        messages.append(
            StickerMessage(
                package_id="8522",   # gói sticker
                sticker_id="16581271"   # id sticker trong gói
        )
    )

    return messages

# def handle_location_message(lat: float, lon: float):
#     messages = []
#     res = nearest_stores(lat, lon, k=3, max_km=30)

#     if res is None or len(res) == 0:
#         messages.append(TextMessage(text="Không tìm thấy siêu thị trong bán kính 30km."))
#         return messages

#     top = res.iloc[0]
#     gmap = f"https://maps.google.com/?q={top.lat},{top.lon}"

#     lines = [
#         f"Siêu thị gần bạn nhất: {int(top.store_id)} — {top.distance_km:.2f} km",
#         f"Vĩ độ: {top.lat:.6f}, Kinh độ: {top.lon:.6f}",
#         f"📍 Map: {gmap}",
#         f"",
#         f"Bonus 2 siêu thị gần kế:"
#     ]
#     for i in range(1, len(res)):
#         r = res.iloc[i]
#         lines.append(f"• #{i+1}: {int(r.store_id)} — {r.distance_km:.2f} km")

#     messages.append(TextMessage(text="\n".join(lines)))
#     messages.append(
#         LocationMessage(
#             title=f"BHX {top.store_id}",
#             address=f"BHX {top.store_id}",
#             latitude=float(top.lat),
#             longitude=float(top.lon),
#         )
#     )
#     return messages


def handle_location_message(lat: float, lon: float, mode: str = "ketquabanhang"):
    """
    Trả về messages khi user gửi vị trí:
      - Tự tìm ST gần nhất
      - Gọi lại handle_user_message với /lenh <ma_st>
    mode: "ketquabanhang" | "thongtinchiahang"
    """
    # 1) tìm ST gần nhất
    res = nearest_stores(lat, lon, k=3, max_km=30)
    if res is None or len(res) == 0:
        return [TextMessage(text="Không tìm thấy siêu thị trong bán kính 30km.")]

    top = res.iloc[0]
    store_id = int(top.store_id)
    km = float(top.distance_km)

    # 2) chọn lệnh mặc định
    if mode == "thongtinchiahang":
        cmd = f"/thongtinchiahang {store_id}"
    else:
        cmd = f"/ketquabanhang {store_id}"

    # 3) gọi lại handler text sẵn có
    report_msgs = handle_user_message(cmd)  # tái dụng logic /thongtinchiahang & /ketquabanhang đã có
    # (Các nhánh /thongtinchiahang và /ketquabanhang hiện có sẵn trong handle_user_message. :contentReference[oaicite:3]{index=3} :contentReference[oaicite:4]{index=4})

    # 4) prepend thông báo + quick reply cho lệnh khác
    gmap = f"https://maps.google.com/?q={top.lat},{top.lon}"
    header = TextMessage(
        text=f"🏬 Gần bạn nhất: ST {store_id} — {km:.2f} km\n📍 {gmap}",
        quick_reply=QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label=f"Chia hàng ST {store_id}", text=f"/thongtinchiahang {store_id}")),
                QuickReplyItem(action=MessageAction(label=f"Nhập-Bán ST {store_id}", text=f"/ketquabanhang {store_id}")),
            ]
        ),
    )
    return [header] + (report_msgs or [])