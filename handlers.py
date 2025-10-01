import re, os, hashlib
import pandas as pd
from urllib.parse import urljoin
from linebot.v3.messaging import TextMessage, ImageMessage, StickerMessage, QuickReply, QuickReplyItem, MessageAction
from utils import df_to_image, df_nhapban_to_image, nearest_stores
from datetime import datetime
from cache import load_df_once

# URL public (ngrok/domain)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://finer-mantis-allowed.ngrok-free.app")
NGANH_HANG = os.getenv("NGANH_HANG", "1235")
NHU_CAU_PATH = os.getenv("NHU_CAU_PATH", f"data/data_{NGANH_HANG}_nhucau.parquet")
NHAP_BAN_PATH = os.getenv("NHAP_BAN_PATH", f"data/data_{NGANH_HANG}_nhapban.parquet")

if NGANH_HANG == "1234":
    group_name = "Rau củ trứng"
elif NGANH_HANG == "1235":
    group_name = "Trái cây"
elif NGANH_HANG == "1236":
    group_name = "Thịt"
elif NGANH_HANG == "1254":
    group_name = "Thủy sản"

# region Kiểm tra cú pháp
VALID_REPORTS = {"thongtinchiahang", "ketquabanhang"}
df_subgroup = load_df_once(NHU_CAU_PATH)
VALID_GROUPS = set(df_subgroup['subgroup'].unique())
df_sieuthi = pd.read_parquet('data/location.parquet')
VALID_STORES = set(df_sieuthi['Mã siêu thị'].unique())

def parse_user_message(user_text: str) -> tuple[dict | None, str | None]:
    txt_warnings = (
        "💡 Hướng dẫn xem báo cáo!\n"
        " \n"
        "👉 Hãy nhập theo cú pháp:\n"
        "/tên_báo_cáo [tên_nhóm_hàng] mã_siêu_thị     (tên_nhóm_hàng có thể bỏ trống)\n"
        " \n"
        "📈 Danh sách báo cáo:"
        f" {', '.join(sorted(map(str, VALID_REPORTS)))}\n"
        "📚 Danh sách nhóm hàng:"
        f" {', '.join(sorted(map(str, VALID_GROUPS)))}\n"
        " \n"
        "✔️ Ví dụ:\n"
        "/thongtinchiahang 7300\n"
        "/ketquabanhang 7300\n"
        f"/thongtinchiahang {sorted(VALID_GROUPS)[0]} 7300\n"
        f"/ketquabanhang {sorted(VALID_GROUPS)[1]} 7300"
    )

    if not user_text:
        return None, txt_warnings

    parts = user_text.strip().split()
    if len(parts) not in (2, 3):  # chỉ chấp nhận 2 hoặc 3 thành phần
        return None, txt_warnings

    # báo cáo
    report = parts[0].lstrip("/").lower()
    if report not in VALID_REPORTS:
        return None, f"Tên báo cáo không hợp lệ. \nDanh sách hợp lệ: {', '.join(sorted(VALID_REPORTS))}"

    # nhóm hàng (có thể bỏ trống)
    if len(parts) == 2:
        group = None
        store_str = parts[1]
    else:
        group = parts[1]
        if group not in VALID_GROUPS:
            return None, f"Nhóm hàng không hợp lệ. \nDanh sách hợp lệ: {', '.join(sorted(map(str, VALID_GROUPS)))}"
        store_str = parts[2]

    # siêu thị
    if not store_str.isdigit():
        return None, "Mã siêu thị phải là số!"

    store_id = int(store_str)
    if store_id not in VALID_STORES:
        return None, "Mã siêu thị không tồn tại!"

    return {"report": report, "group": group, "store_id": store_id}, None
# endregion

def handle_user_message(user_text: str):
    messages = []

    parsed, error = parse_user_message(user_text)
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
            df = df[df['subgroup'] == group]
        df = df[df["Mã siêu thị"] == int(store_id)][["Tên siêu thị","Tên sản phẩm","Min chia","Số chia","Trạng thái"]]
        ten_sieu_thi = df['Tên siêu thị'].iloc[0] if not df.empty else "N/A"
        df = df.drop(columns=["Tên siêu thị"])
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"table_thongtinchiahang_{store_id}_{ts}.png"
        out_path = f"static/{filename}"
        df_to_image(df, outfile=out_path, title=f"Thông tin chia hàng {group_name} ST: {store_id}\n(dữ liệu cập nhật ngày {ngay_cap_nhat})")

        img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
        messages.append(TextMessage(text=f"Đây là bảng chia hàng {group_name}\ncủa siêu thị {store_id}-{ten_sieu_thi} (theo đvt của sản phẩm):"))
        messages.append(ImageMessage(original_content_url=img_url, preview_image_url=img_url))

    elif report == "ketquabanhang":
        df = load_df_once(NHAP_BAN_PATH)
        df = df.rename(columns={'Trạng thái':'Số chia hiện tại'})
        tu_ngay = df['Từ ngày'].iloc[0]
        den_ngay = df['Đến ngày'].iloc[0]
        if group is not None:
            df = df[df['subgroup'] == group]
        df = df[df["Mã siêu thị"] == int(store_id)][["Tên siêu thị","Nhóm sản phẩm","Nhu cầu","PO","Nhập","Bán","% Nhập/PO","% Bán/Nhập","Số chia hiện tại"]]
        df = df.sort_values(by=["Nhập","Số chia hiện tại"], ascending=False)
        df = df.drop_duplicates(subset=["Nhóm sản phẩm"], keep="first")
        ten_sieu_thi = df['Tên siêu thị'].iloc[0] if not df.empty else "N/A"
        df = df.drop(columns=["Tên siêu thị"])
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"table_ketquabanhang_{store_id}_{ts}.png"
        out_path = f"static/{filename}"
        df_nhapban_to_image(df, outfile=out_path, title=f"Thông tin nhập - bán hàng {group_name} ST: {store_id} (đơn vị KG)\n(dữ liệu từ {tu_ngay} đến {den_ngay})")

        img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
        messages.append(TextMessage(text=f"Đây là bảng thông tin nhập - bán hàng {group_name}\ncủa siêu thị {store_id}-{ten_sieu_thi} (đơn vị KG):"))
        messages.append(ImageMessage(original_content_url=img_url, preview_image_url=img_url))

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