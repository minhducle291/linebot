import os
from datetime import datetime
import pytz
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
)
# from dotenv import load_dotenv
# load_dotenv()
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

# ====== CẤU HÌNH CƠ BẢN ======
THOI_GIAN_GUI_TIN_NHAN = [
    {"hour": 5, "minute": 30},
    {"hour": 7, "minute": 0}
]

XLSX_PATH  = os.getenv("SCHEDULE_XLSX", "./data/schedule.xlsx")
TZ_NAME = os.getenv("TZ", "Asia/Ho_Chi_Minh")
TZ = pytz.timezone(TZ_NAME)

# ====== LINE PUSH ======
def _push_text(user_id: str, text: str):
    cfg = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
    with ApiClient(cfg) as c:
        MessagingApi(c).push_message(
            PushMessageRequest(to=user_id, messages=[TextMessage(text=text)])
        )

# ====== ĐỌC EXCEL & LỌC HÔM NAY ======
def _read_rows_for_today() -> pd.DataFrame:
    try:
        df = pd.read_excel(XLSX_PATH, engine="openpyxl", dtype=str)
    except Exception as e:
        print(f"[scheduler] read_excel error: {e}")
        return pd.DataFrame(columns=["user_id", "ngay_gui_tin_nhan", "noi_dung"])

    # Chuẩn hoá cột bắt buộc
    for col in ["user_id", "ngay_gui_tin_nhan", "noi_dung"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()

    # Parse ngày linh hoạt: hỗ trợ yyyy-mm-dd, dd/mm/yyyy, v.v.
    # Chuyển về date (không kèm giờ) để so sánh với "hôm nay" theo TZ
    def to_date_safe(s):
        try:
            dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
            if pd.isna(dt):
                return None
            return dt.date()
        except Exception:
            return None

    df["_ngay"] = df["ngay_gui_tin_nhan"].map(to_date_safe)
    today = datetime.now(TZ).date()

    today_df = df[df["_ngay"] == today][["user_id", "noi_dung"]].copy()
    return today_df

# ====== JOB CHẠY MỖI LẦN ĐẾN SLOT ======
def _send_for_current_slot():
    rows = _read_rows_for_today()
    if rows.empty:
        print("[scheduler] today: nothing to send")
        return
    sent = 0
    for _, r in rows.iterrows():
        uid = r["user_id"]
        msg = r["noi_dung"]
        if not uid or not msg:
            continue
        try:
            _push_text(uid, msg)
            sent += 1
        except Exception as e:
            print(f"[scheduler][push][ERROR] to={uid} err={e}")
    print(f"[scheduler] sent {sent} message(s) for current slot")

# ====== KHỞI TẠO SCHEDULER ======
def init_scheduler():
    sch = BackgroundScheduler(timezone=TZ)
    sch.start()

    # Tạo job từng mốc giờ theo cấu hình {hour, minute}
    for i, tg in enumerate(THOI_GIAN_GUI_TIN_NHAN, start=1):
        try:
            h = int(tg.get("hour", 0))
            m = int(tg.get("minute", 0))
        except Exception:
            print(f"[scheduler] skip invalid time item: {tg!r}")
            continue
        if not (0 <= h <= 23 and 0 <= m <= 59):
            print(f"[scheduler] skip out-of-range time: {h}:{m:02d}")
            continue

        job_id = f"fixed_slot_{h:02d}{m:02d}_{i}"
        sch.add_job(
            _send_for_current_slot,
            trigger="cron",
            hour=h,
            minute=m,
            id=job_id,
            replace_existing=True
        )
        print(f"[scheduler] start cron @ {h:02d}:{m:02d} (TZ={TZ_NAME}) id={job_id}")

    return sch
