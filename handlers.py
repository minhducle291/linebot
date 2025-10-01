import re, os, hashlib
import pandas as pd
from urllib.parse import urljoin
from linebot.v3.messaging import TextMessage, ImageMessage, StickerMessage, QuickReply, QuickReplyItem, MessageAction
from utils import df_to_image, df_nhapban_to_image, nearest_stores
from datetime import datetime
from cache import load_df_once

# URL public (ngrok/domain)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://finer-mantis-allowed.ngrok-free.app")
NGANH_HANG = os.getenv("NGANH_HANG", "1254")
NHU_CAU_PATH = os.getenv("NHU_CAU_PATH", f"data/data_{NGANH_HANG}_nhucau.parquet")
NHAP_BAN_PATH = os.getenv("NHAP_BAN_PATH", f"data/data_{NGANH_HANG}_nhapban.parquet")

# region Kiểm tra cú pháp
VALID_REPORTS = {"thongtinchiahang", "ketquabanhang"}
df_subgroup = load_df_once(NHU_CAU_PATH)
VALID_GROUPS = {
    int(x.split("-")[0])
    for x in df_subgroup["Nhóm hàng"].dropna().astype(str).str.strip().unique()
    if x.split("-")[0].isdigit() and len(x.split("-")[0]) == 4
}

def parse_user_message(user_text: str, lst_store: list[int] | set[int]):
    """
    Cú pháp hợp lệ:
      1) /ten_bao_cao ma_sieu_thi
      2) /ten_bao_cao nhom_hang ma_sieu_thi

    - ten_bao_cao ∈ {thongtinchiahang, ketquabanhang}
    - nhom_hang (optional) ∈ {cabien, canuocngot, haisan}
    - ma_sieu_thi: 3–5 chữ số, và phải có trong lst_store
    """
    if not user_text or not user_text.strip():
        return None, "Tin nhắn trống. Cú pháp: /ten_bao_cao [nhom_hang] ma_sieu_thi"

    parts = user_text.strip().split()
    # cần 2 hoặc 3 phần
    if len(parts) not in (2, 3):
        return None, "Sai cấu trúc. Cú pháp: /ten_bao_cao [nhom_hang] ma_sieu_thi"

    report_token = parts[0]
    if not report_token.startswith("/"):
        return None, "Thiếu dấu '/' trước tên báo cáo. Ví dụ: /thongtinchiahang"

    report = report_token[1:].lower()
    if report not in VALID_REPORTS:
        return None, f"Tên báo cáo không hợp lệ. Hợp lệ: {', '.join(VALID_REPORTS)}"

    # Trường hợp 2 phần: không có nhóm hàng
    if len(parts) == 2:
        store_str = parts[1]
        group = None
    else:
        # 3 phần: có nhóm hàng
        group = parts[1].lower()
        if group not in VALID_GROUPS:
            return None, f"Nhóm hàng không hợp lệ. Hợp lệ: {', '.join(VALID_GROUPS)}"
        store_str = parts[2]

    # Check mã siêu thị: 3-5 ký tự digit
    if not (store_str.isdigit() and 3 <= len(store_str) <= 5):
        return None, "Mã siêu thị phải là số dài 3-5 ký tự (vd: 735, 1024)."

    store_id = int(store_str)

    # Tối ưu: chuyển lst_store thành set nếu là list dài
    store_container = set(lst_store) if isinstance(lst_store, list) else lst_store
    if store_id not in store_container:
        return None, "Mã siêu thị không nằm trong danh sách cho phép."

    # OK
    return {"report": report, "group": group, "store_id": store_id}, None
# endregion

def handle_user_message(user_text: str):
    messages = []

    df_store = pd.read_parquet('data/location.parquet')
    lst_store = df_store['Mã siêu thị'].tolist()
    parsed, error = parse_user_message(user_text, lst_store)

    if error:
        return [TextMessage(text=error)]
    # parsed["group"] có thể là None nếu user không nhập nhóm hàng
    report = parsed["report"]
    group  = parsed["group"]
    store_id  = parsed["store_id"]


    if report == "thongtinchiahang":
        df = load_df_once(NHU_CAU_PATH)
        ngay_cap_nhat = df['Ngày cập nhật'].iloc[0]
        if group is not None:
            df = df[df['Mã nhóm hàng'] == int(group)]
        df = df[df["Mã siêu thị"] == int(store_id)][["Tên siêu thị","Tên sản phẩm","Min chia","Số mua","Trạng thái chia hàng"]]
        ten_sieu_thi = df['Tên siêu thị'].iloc[0] if not df.empty else "N/A"
        df = df.drop(columns=["Tên siêu thị"])
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"table_thongtinchiahang_{store_id}_{ts}.png"
        out_path = f"static/{filename}"
        df_to_image(df, outfile=out_path, title=f"Thông tin chia hàng thủy sản ST: {store_id}\n(dữ liệu cập nhật ngày {ngay_cap_nhat})")

        img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
        messages.append(TextMessage(text=f"Đây là bảng chia hàng thủy sản cho siêu thị {store_id}-{ten_sieu_thi} (theo đvt của sản phẩm):"))
        messages.append(ImageMessage(original_content_url=img_url, preview_image_url=img_url))

    elif report == "ketquabanhang":
        df = load_df_once(NHAP_BAN_PATH)
        tu_ngay = df['Từ ngày'].iloc[0]
        den_ngay = df['Đến ngày'].iloc[0]
        if group is not None:
            df = df[df['Mã nhóm hàng'] == int(group)]
        df = df[df["Mã siêu thị"] == int(store_id)][["Tên siêu thị","Nhóm sản phẩm","Nhu cầu","PO","Nhập","Bán","% Nhập/PO","% Bán/Nhập","Số chia hiện tại"]]
        df = df.sort_values(by=["Nhập","Số chia hiện tại"], ascending=False)
        df = df.drop_duplicates(subset=["Nhóm sản phẩm"], keep="first")
        ten_sieu_thi = df['Tên siêu thị'].iloc[0] if not df.empty else "N/A"
        df = df.drop(columns=["Tên siêu thị"])
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"table_ketquabanhang_{store_id}_{ts}.png"
        out_path = f"static/{filename}"
        df_nhapban_to_image(df, outfile=out_path, title=f"Thông tin nhập - bán hàng thủy sản ST: {store_id} (đơn vị KG)\n(dữ liệu từ {tu_ngay} đến {den_ngay})")

        img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
        messages.append(TextMessage(text=f"Đây là bảng thông tin nhập - bán hàng thủy sản cho siêu thị {store_id}-{ten_sieu_thi} (đơn vị KG):"))
        messages.append(ImageMessage(original_content_url=img_url, preview_image_url=img_url))

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