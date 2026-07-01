#!/bin/bash
set -e
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== $(date) ==="
echo "1. ดึงข้อมูลจาก Jetts..."
python3 scraper.py

echo "2. สร้าง dashboard..."
python3 generate_dashboard.py

echo "3. Push ขึ้น GitHub..."
git add data.json index.html
git commit -m "update: $(date '+%d/%m/%Y %H:%M')"
git push

echo "เสร็จแล้ว ✓"
