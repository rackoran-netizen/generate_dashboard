"""
สร้าง dashboard.pdf จาก index.html ด้วย Playwright's page.pdf()
(ใช้ @media print CSS ในตัวเว็บโดยตรง — ผลลัพธ์เหมือนกับปุ่ม "ดาวน์โหลด PDF" บนหน้าเว็บ)
รันหลัง generate_dashboard.py เสมอ (ต้องมี index.html ล่าสุดอยู่ในโฟลเดอร์นี้แล้ว)
"""
import os
from playwright.sync_api import sync_playwright

INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.pdf")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file://{INDEX_PATH}")
    page.pdf(
        path=OUT_PATH,
        print_background=True,      # ต้องเปิด ไม่งั้นแถบกราฟ/สีพื้นหลังหาย
        prefer_css_page_size=True,  # ให้ @page{size:A4;margin:8mm} ใน CSS เป็นตัวกำหนด ไม่ใช่ default Letter
    )
    browser.close()

print(f"บันทึก {OUT_PATH} แล้ว")
