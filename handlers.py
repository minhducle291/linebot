import re
import pandas as pd
from urllib.parse import urljoin
from linebot.v3.messaging import TextMessage, ImageMessage
from utils import df_to_image
import os

# URL public (ngrok/domain)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://linebot-qer1.onrender.com")
#PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://787e732a65b9.ngrok-free.app")

def handle_user_message(user_text: str):
    """
    Trả về list các message (TextMessage, ImageMessage, ...) tùy theo nội dung user_text
    """
    messages = []

    # Trường hợp 1: tin nhắn chứa '@@' => trả text
    if "@@" in user_text:
        messages.append(TextMessage(text=f"Bạn vừa nhắn: {user_text}"))

    # Trường hợp 2: tin nhắn chứa '!' và có số => vẽ ảnh gửi
    elif "/nhucau" in user_text:
        match = re.search(r"\d+", user_text)
        if match:
            store_number = int(match.group())
            df = pd.read_parquet("data.parquet")
            ngay_cap_nhat = df['Ngày cập nhật'].iloc[0]
            df = df[df["Mã siêu thị"] == store_number][["Tên sản phẩm","Min chia","Số mua","Trạng thái chia hàng"]]
            df = df.sort_values(by=["Trạng thái chia hàng", "Tên sản phẩm"])
            
            filename = f"table_{store_number}.png"
            out_path = f"static/{filename}"
            df_to_image(df, outfile=out_path, title=f"Thông tin chia hàng thủy sản ST: {store_number}\n(dữ liệu cập nhật ngày {ngay_cap_nhat})")

            img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
            #messages.append(TextMessage(text=f"Đây là bảng chia hàng thủy sản cho siêu thị {store_number}:"))
            #messages.append(ImageMessage(originalContentUrl=img_url, previewImageUrl=img_url))
            messages.append(
                ImageMessage(
                    original_content_url=img_url,
                    preview_image_url=img_url
                )
            )

    # elif "/kqkd" in user_text:
    #     match = re.search(r"\d+", user_text)
    #     if match:
    #         store_number = int(match.group())
    #         df = pd.read_parquet("data_nhapban.parquet")
    #         tu_ngay = df['Từ ngày'].iloc[0]
    #         den_ngay = df['Đến ngày'].iloc[0]
    #         df = df[df["Mã siêu thị"] == store_number][["Nhóm sản phẩm","SL nhu cầu (KG)","SL lên PO (KG)","SL thực nhập (KG)","SL xuất bán (KG)","Tỉ lệ nhập/PO","Tỉ lệ bán/nhập"]]
    #         df = df.sort_values(by=["SL thực nhập (KG)"], ascending=False)
            
    #         filename = f"table_kqkd_{store_number}.png"
    #         out_path = f"static/{filename}"
    #         df_nhapban_to_image(df, outfile=out_path, title=f"Thông tin nhập - bán hàng thủy sản ST: {store_number}\n(dữ liệu từ {tu_ngay} đến {den_ngay})")

    #         img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
    #         messages.append(TextMessage(text=f"Đây là bảng thông tin nhập - bán hàng thủy sản cho siêu thị {store_number}:"))
    #         #messages.append(ImageMessage(originalContentUrl=img_url, previewImageUrl=img_url))
    #         messages.append(
    #             ImageMessage(
    #                 original_content_url=img_url,
    #                 preview_image_url=img_url
    #             )
    #         )

    # Trường hợp khác: trả text mặc định
    else:
        messages.append(TextMessage(text="Hãy nhập lệnh + mã siêu thị để xem báo cáo!\nVí dụ:\n/nhucau 7300\n/kqkd 7300"))

    return messages