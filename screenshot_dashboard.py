"""
ถ่ายภาพ index.html (โหมดเดียวกับปุ่ม "ดาวน์โหลด PDF" บนหน้าเว็บ — คลาส .pdf-export)
ออกมาเป็น dashboard.png สำหรับส่งเข้า LINE ทุกเช้า
รันหลัง generate_dashboard.py เสมอ (ต้องมี index.html ล่าสุดอยู่ในโฟลเดอร์นี้แล้ว)
"""
import os
from playwright.sync_api import sync_playwright

INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.png")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 1000})
    page.goto(f"file://{INDEX_PATH}")
    # บังคับใช้สไตล์โหมดพิมพ์/PDF (คอมแพกต์ พอดี A4 หน้าเดียว) เหมือนปุ่มดาวน์โหลด PDF
    page.evaluate("document.body.classList.add('pdf-export')")
    page.wait_for_timeout(150)
    page.locator(".a4").screenshot(path=OUT_PATH)
    browser.close()

print(f"บันทึก {OUT_PATH} แล้ว")
