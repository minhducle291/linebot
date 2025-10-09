import pandas as pd
from datetime import datetime
from linebot.v3.messaging import TextMessage, ImageMessage
from urllib.parse import urljoin
from config import PUBLIC_BASE_URL, NHU_CAU_PATH, NHAP_BAN_PATH
from utils import df_nhucau_to_image, df_nhapban_to_image, build_flex_text_message
from cache import load_df_once


def report_thongtinchiahang(store_id: str, cat_id: str, cat_name: str, group: str):
    messages = []
    df = load_df_once(NHU_CAU_PATH)
    ngay_cap_nhat = df['Ngày cập nhật'].iloc[0]

    df = df[df['Mã ngành hàng'] == int(cat_id)]
    if group == "Xem tất cả nhóm": pass
    else: df = df[df['Mã nhóm hàng'] == int(group.split("-", 1)[0])]

    df = df[df["Mã siêu thị"] == int(store_id)][["Tên siêu thị","Tên sản phẩm","Min chia","Số chia","Trạng thái"]]
    ten_sieu_thi = df['Tên siêu thị'].iloc[0] if not df.empty else "N/A"
    df = df.drop(columns=["Tên siêu thị"])
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"table_thongtinchiahang_{store_id}_{ts}.png"
    out_path = f"static/{filename}"
    group_label = f"Ngành hàng {cat_name}" if group == "Xem tất cả nhóm" else f"Nhóm hàng {group}"
    df_nhucau_to_image(df, outfile=out_path, title=f"Thông tin chia hàng của siêu thị {store_id}-{ten_sieu_thi}\n{group_label}\n(ngày cập nhật: {ngay_cap_nhat})")

    img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
    text = f"Thông tin chia hàng - ST: {store_id}\n{group_label}"
    messages.append(build_flex_text_message(text, bg="#761414", fg="#FFFFFF", size="md", weight="regular"))
    messages.append(ImageMessage(original_content_url=img_url, preview_image_url=img_url))
    return messages


def report_ketquabanhang(store_id: str, cat_id: str, cat_name: str, group: str):
    messages = []
    df = load_df_once(NHAP_BAN_PATH)
    df = df.rename(columns={'Trạng thái':'Số chia hiện tại'})
    tu_ngay = df['Từ ngày'].iloc[0]
    den_ngay = df['Đến ngày'].iloc[0]

    if group == "Xem tất cả nhóm":
        df = df[df['Mã ngành hàng'] == int(cat_id)]
    else:
        df = df[df['Mã nhóm hàng'] == int(group.split("-", 1)[0])]

    df = df[df["Mã siêu thị"] == int(store_id)][["Tên siêu thị","Nhóm sản phẩm","Nhu cầu","PO","Nhập","Bán","% Nhập/PO","% Bán/Nhập","Số chia hiện tại"]]
    df = df.sort_values(by=["Nhập","Số chia hiện tại"], ascending=False)
    df = df.drop_duplicates(subset=["Nhóm sản phẩm"], keep="first")
    ten_sieu_thi = df['Tên siêu thị'].iloc[0] if not df.empty else "N/A"
    df = df.drop(columns=["Tên siêu thị"])
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"table_ketquabanhang_{store_id}_{ts}.png"
    out_path = f"static/{filename}"
    group_label = f"Ngành hàng {cat_name}" if group == "Xem tất cả nhóm" else f"Nhóm hàng {group}"
    df_nhapban_to_image(df, outfile=out_path, title=f"Báo cáo kết quả bán hàng của siêu thị {store_id}-{ten_sieu_thi}\n{group_label}\n(đơn vị KG) (dữ liệu từ {tu_ngay} đến {den_ngay})")

    img_url = urljoin(PUBLIC_BASE_URL + "/", out_path)
    messages.append(build_flex_text_message(f"Kết quả bán hàng - ST: {store_id}\n{group_label}", bg="#761414", fg="#FFFFFF", size="md", weight="regular"))
    messages.append(ImageMessage(original_content_url=img_url, preview_image_url=img_url))
    return messages