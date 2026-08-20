"""
ส่ง dashboard.pdf เข้า Telegram ทุกเช้า ผ่าน Telegram Bot API (sendDocument)
อัปโหลดไฟล์ตรงๆ ไม่ต้องพึ่ง URL สาธารณะเหมือน LINE — ไม่ต้องรอ GitHub Pages deploy

ต้องการ env:
  TELEGRAM_BOT_TOKEN - token ของบอทจาก @BotFather
  TELEGRAM_CHAT_ID   - chat id ปลายทาง (ผู้ใช้/กลุ่ม) ที่จะส่งไฟล์ไปให้
"""
import os

import requests

PAGES_URL = "https://rackoran-netizen.github.io/generate_dashboard/"
PDF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.pdf")

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

with open(PDF_PATH, "rb") as f:
    res = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendDocument",
        data={
            "chat_id": CHAT_ID,
            "caption": f"อัปเดต PT Dashboard วันนี้แล้ว ดูฉบับเต็ม/แชร์ต่อ: {PAGES_URL}",
        },
        files={"document": ("Jetts_RRA_Report.pdf", f, "application/pdf")},
        timeout=30,
    )

res.raise_for_status()
print(f"ส่ง Telegram สำเร็จ (status {res.status_code})")
