import re
import pandas as pd
from urllib.parse import urljoin
from linebot.v3.messaging import TextMessage, ImageMessage
from utils import df_to_image
import os

# URL public (ngrok/domain)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://caeb71f95a4c.ngrok-free.app")

def handle_user_message(user_text: str):
    """
    Trả về list các message (TextMessage, ImageMessage, ...) tùy theo nội dung user_text
    """
    messages = []

    # Trường hợp 1: tin nhắn chứa '@@' => trả text
    if "@@" in user_text:
        messages.append(TextMessage(text=f"Bạn vừa nhắn: {user_text}"))

    # Trường hợp 2: tin nhắn chứa '!' và có số => vẽ ảnh gửi
    elif "!" in user_text:
        match = re.search(r"\d+", user_text)
        if match:
            store_number = int(match.group())
            df = pd.read_parquet("data.parquet")
            ngay_cap_nhat = df['Ngày cập nhật'].iloc[0]
            df = df[df["Mã siêu thị"] == store_number][["Mã siêu thị","Tên sản phẩm","Min chia","Số mua","Trạng thái chia hàng"]]
            df = df.sort_values(by=["Trạng thái chia hàng", "Tên sản phẩm"])
            
            filename = f"table_{store_number}.png"
            out_path = f"static/{filename}"
            df_to_image(df, outfile=out_path, title=f"Thông tin chia hàng thủy sản ST: {store_number}\n(dữ liệu cập nhật ngày {ngay_cap_nhat})")

            img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
            messages.append(TextMessage(text=f"Đây là bảng chia hàng cho siêu thị {store_number}:"))
            messages.append(ImageMessage(originalContentUrl=img_url, previewImageUrl=img_url))

    # Trường hợp khác: trả text mặc định
    else:
        messages.append(TextMessage(text="Hãy gửi tin có chứa '!' kèm mã siêu thị để tra cứu! (VD: !7300)"))

    return messages