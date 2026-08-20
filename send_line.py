"""
ส่ง dashboard.png (ที่เพิ่ง push ขึ้น GitHub Pages แล้ว) เข้า LINE ทุกเช้า
ผ่าน LINE Messaging API (push message) — ต้องมี dashboard.png ถูก deploy
บน GitHub Pages เรียบร้อยก่อนรันสคริปต์นี้ (LINE ต้องดึงรูปจาก URL จริงได้)

ต้องการ env:
  LINE_CHANNEL_TOKEN  - Channel access token ของ Messaging API channel
  LINE_USER_ID        - userId (หรือ groupId) ปลายทางที่จะ push ข้อความไปให้
"""
import json
import os
import urllib.request

PAGES_URL = "https://rackoran-netizen.github.io/generate_dashboard"
IMAGE_URL = f"{PAGES_URL}/dashboard.png"

TOKEN = os.environ["LINE_CHANNEL_TOKEN"]
USER_ID = os.environ["LINE_USER_ID"]

payload = {
    "to": USER_ID,
    "messages": [
        {
            "type": "image",
            "originalContentUrl": IMAGE_URL,
            "previewImageUrl": IMAGE_URL,
        },
        {
            "type": "text",
            "text": f"อัปเดต PT Dashboard วันนี้แล้ว ดูฉบับเต็ม/แชร์ต่อ: {PAGES_URL}/",
        },
    ],
}

req = urllib.request.Request(
    "https://api.line.me/v2/bot/message/push",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    },
    method="POST",
)

with urllib.request.urlopen(req, timeout=30) as res:
    print(f"ส่ง LINE สำเร็จ (status {res.status})")
