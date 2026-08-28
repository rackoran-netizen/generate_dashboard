"""
ส่ง dashboard.pdf เข้า Telegram ทุกเช้า ผ่าน Telegram Bot API (sendDocument)
แนบไฟล์ PDF ตรงๆ ไม่มีลิงก์ — caption สรุปตัวเลขสำคัญ + เทียบความคืบหน้ากับเวลาที่ผ่านไป

env (อ่านตอนส่งจริงเท่านั้น — import build_caption() ได้โดยไม่ต้องตั้ง env):
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

ดูตัวอย่าง caption โดยไม่ส่งจริง:  python3 send_telegram.py --preview
"""
import calendar
import datetime as _dt
import json
import os
import sys

import requests

from metrics import GOAL_MEMBER, GOAL_PT_SOLD, active_mem_summary, num, split_club

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE, "dashboard.pdf")
DATA_PATH = os.path.join(BASE, "data.json")


def _pace(actual_pct, elapsed_pct):
    diff = actual_pct - elapsed_pct
    if diff >= 2:
        return f"นำแผน {diff:.0f}%"
    if diff <= -2:
        return f"ช้ากว่าแผน {abs(diff):.0f}%"
    return "ตามแผน"


def build_caption(data_path=DATA_PATH, report_date=None):
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    sold, _ = split_club(data["sold"]["rows"])
    mem_total = sum(r["count"] for r in active_mem_summary(data))

    sold_actual = num(sold.get("Total Amount", "0"))
    sold_pct = sold_actual / GOAL_PT_SOLD * 100
    mem_pct = mem_total / GOAL_MEMBER * 100

    # เวลาที่ผ่านไป อิงจากวันที่ส่งรายงาน
    today = report_date or _dt.date.today()
    month_pct = today.day / calendar.monthrange(today.year, today.month)[1] * 100
    days_in_year = 366 if calendar.isleap(today.year) else 365
    year_pct = today.timetuple().tm_yday / days_in_year * 100

    return (
        f"PT Dashboard — Jetts Robinson Ratchaphruek\n"
        f"ส่งรายงาน {today:%d/%m/%Y} · ข้อมูลถึง {data['period']['end']}\n"
        f"เดือนผ่านไป {month_pct:.0f}% · ปีผ่านไป {year_pct:.0f}%\n"
        f"\n"
        f"PT Sold  {sold_actual:,.0f} ฿ · {sold_pct:.1f}% ของเป้าเดือน ({_pace(sold_pct, month_pct)})\n"
        f"สมาชิกใหม่  {mem_total} คน · {mem_pct:.1f}% ของเป้าคลับ ({_pace(mem_pct, month_pct)})"
    )


def main():
    caption = build_caption()

    if "--preview" in sys.argv:
        print(caption)
        return

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    with open(PDF_PATH, "rb") as f:
        res = requests.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": ("Jetts_RRA_Report.pdf", f, "application/pdf")},
            timeout=30,
        )

    res.raise_for_status()
    print(f"ส่ง Telegram สำเร็จ (status {res.status_code})")


if __name__ == "__main__":
    main()
