import pandas as pd
from urllib.parse import parse_qs
# LINE SDK v3
from linebot.v3.messaging import TextMessage, FlexMessage
from linebot.v3.messaging.models import FlexContainer

from cache import load_df_once
from utils import build_flex_categories, build_flex_report_group, nearest_stores, build_flex_text_message, get_groups_for_category
from config import PUBLIC_BASE_URL, NHU_CAU_PATH, NHAP_BAN_PATH, REPORTS_DISPLAY, DATA_PATH_FOR_REPORT, REPORT_HANDLERS, CATEGORIES

df_nhap_ban = load_df_once(NHAP_BAN_PATH)
#====== DỮ LIỆU SIÊU THỊ ======
df_sieuthi = load_df_once(NHU_CAU_PATH)
lst_sieuthi = df_sieuthi['Mã siêu thị'].unique().tolist()

# ====== XỬ LÝ TEXT ======
def handle_user_message(user_text: str, user_id: str = None):
    user_text = (user_text or "").strip()
    # ---------- (1) TEXT COMMANDS ----------
    if user_text.strip().lower() == "/id":
        return [TextMessage(text=f"Đây là user_id của bạn:\n{user_id}")]
        
    if user_text.lower() == "ping":
        return [TextMessage(text="pong")]

    # nếu là text khác mà KHÔNG phải toàn số -> coi như không phải mã siêu thị
    if not user_text.isdigit():
        text = "Hãy gửi [Mã siêu thị] hoặc chia sẻ [Vị trí] của bạn để xem báo cáo nhé!"
        return [build_flex_text_message(text, bg="#038d38", fg="#FFFFFF", header_fg="#FFFFFF",
                                        size="md", weight="regular", header_text="💡Hướng dẫn")]
    # ---------- (2) NUMBER = MÃ SIÊU THỊ ----------
    store_id = int(user_text)
    if store_id not in lst_sieuthi:
        text = "[Mã siêu thị] không tồn tại!\nVui lòng kiểm tra lại!"
        return [build_flex_text_message(text, bg="#761414", fg="#FFFFFF", header_fg="#FFFFFF",
                                        size="md", weight="regular", header_text="⚠️ Cảnh báo")]

    # Flex: CHỌN NGÀNH HÀNG (4 nút)
    cat_flex = build_flex_categories(store_id, CATEGORIES, include_display_text=False)
    return [FlexMessage(altText="Chọn ngành hàng", contents=FlexContainer.from_dict(cat_flex))]

def handle_postback(data: str):
    """
    B2: a=category.select  -> đọc parquet theo 'Mã ngành hàng' -> build Flex nhóm hàng
    B3: a=report_group.select -> xác nhận + gọi report handler tương ứng
    """
    qs = parse_qs(data or "")
    action = (qs.get("a", [""])[0])

    # ===== BƯỚC 2: USER CHỌN NGÀNH =====
    if action == "category.select":
        store_id = int(qs.get("store", ["0"])[0] or 0)
        cat_id   = int(qs.get("cat",   ["0"])[0] or 0)

        # =========== NHÓM HÀNG ==================
        VALID_GROUPS = get_groups_for_category(NHU_CAU_PATH, cat_id)

        # Build Flex "chọn báo cáo & nhóm hàng" (dùng cùng groups cho mọi report)
        groups_by_report = {r["id"]: VALID_GROUPS for r in REPORTS_DISPLAY}
        grp_flex = build_flex_report_group(
            store_id=store_id,
            reports=REPORTS_DISPLAY,
            groups_by_report=groups_by_report,
            groups_per_bubble=7,
            include_display_text=False,   # không đẩy displayText vào khung chat
            cat_id=cat_id                 # giữ cat_id để truyền qua postback
        )
        return [FlexMessage(altText="Chọn báo cáo & nhóm hàng",
                            contents=FlexContainer.from_dict(grp_flex))]

    # ===== BƯỚC 3: USER CHỌN NHÓM TRONG 1 BÁO CÁO =====
    if action == "report_group.select":
        store  = qs.get("store",  [""])[0]
        report = qs.get("report", [""])[0]
        cat_id = qs.get("cat",    [""])[0]
        group  = qs.get("group",  [""])[0]
        
        # Lấy title hiển thị đẹp
        # title = next((r["title"] for r in REPORTS_DISPLAY if r["id"] == report), report)
        cat_name = next((c["title"] for c in CATEGORIES if str(c["id"]) == str(cat_id)), cat_id)
        messages = []

        # Gọi đúng report handler (đã map trong REPORT_HANDLERS)
        if report in REPORT_HANDLERS:
            handler_func = REPORT_HANDLERS[report]
            data_path = DATA_PATH_FOR_REPORT[report]
            messages.extend(handler_func(data_path=data_path,
                                         public_base_url=PUBLIC_BASE_URL,
                                         store_id=int(store),
                                         cat_id=cat_id,
                                         cat_name=cat_name,
                                         group=group))
        else:
            messages.append(TextMessage(text=f"⚠️ Chưa có handler cho báo cáo: {report}"))

        return messages

    # ===== KHÁC =====
    return [TextMessage(text="Lỗi xử lý postback. Vui lòng thử lại sau!")]

def handle_location_message(lat: float, lon: float):
    """
    Nhận vị trí người dùng -> tìm siêu thị gần nhất -> trả thông báo + Flex chọn ngành hàng.
    """
    try:
        df = nearest_stores(lat, lon, k=1, max_km=30)
    except Exception:
        return [TextMessage(text="⚠️ Không đọc được dữ liệu vị trí. Vui lòng thử lại sau.")]

    if df is None or getattr(df, "empty", True):
        return [TextMessage(text="❌ Không tìm thấy siêu thị trong bán kính 30km.")]

    raw_sid = df.iloc[0]["store_id"]
    distance = df.iloc[0]["distance_km"]
    store_id = str(int(float(raw_sid)))

    # bước 1: báo siêu thị gần nhất
    confirm_msg = TextMessage(
        text=f"📍 Siêu thị gần nhất: {store_id} (cách khoảng {distance:.1f} km)."
    )

    # bước 2: gọi lại flow chọn ngành hàng
    flex_msgs = handle_user_message(store_id)

    return [confirm_msg] + flex_msgs