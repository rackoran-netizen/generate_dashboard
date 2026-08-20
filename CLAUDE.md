# PT Dashboard — Jetts Robinson Ratchaphruek

## ภาพรวม

ระบบ scrape ข้อมูล PT จาก jettsapp.jetts.co.th แล้วสร้าง HTML dashboard deploy บน GitHub Pages
อัตโนมัติทุกวัน **07:00 Bangkok** (สั่งโดย Cloudflare Cron Trigger ไม่ใช่ GitHub schedule — ดูเหตุผลด้านล่าง)
จากนั้นส่งภาพสรุป dashboard เข้า LINE ผู้ดูแลอัตโนมัติ (เป้าหมายถึงก่อน 7:30)

---

## Repository & Paths

- **GitHub repo**: `rackoran-netizen/generate_dashboard` (public)
- **GitHub Pages**: https://rackoran-netizen.github.io/generate_dashboard/
- **Local path**: `/Users/oran_raurhotmail.com/Jetts_RRA_Report/`
- **Remote**: `git@github.com:rackoran-netizen/generate_dashboard.git` (SSH ED25519)
- **Git config**: `rackoran-netizen` / `rackoran@gmail.com`
- **Cloudflare account**: `rackoran@gmail.com` (`wrangler` login ไว้ในเครื่อง local แล้ว)

⚠️ **repo นี้เป็น public** — ห้ามใส่ credential จริงลงไฟล์ที่ commit เด็ดขาด (เคยหลุดมาแล้วครั้งหนึ่ง ดูท้ายไฟล์)

---

## ไฟล์ในโปรเจกต์

```
Jetts_RRA_Report/
├── scraper.py                # Playwright ดึงข้อมูลจาก jettsapp → data.json
├── generate_dashboard.py     # สร้าง index.html จาก data.json (screen + print/PDF แยกกัน)
├── screenshot_dashboard.py   # Playwright ถ่าย index.html (โหมด .pdf-export) → dashboard.png
├── send_line.py              # push dashboard.png + ลิงก์เข้า LINE ผ่าน Messaging API
├── data.json                 # ข้อมูลดิบ (commit ด้วย)
├── index.html                # Dashboard (commit ด้วย)
├── dashboard.png             # snapshot สำหรับ LINE (commit ด้วย, gen ทุกรอบ)
├── run.sh                    # รัน manual บน Mac (cd เข้าโฟลเดอร์ตัวเอง + source .env เอง)
├── .env                      # credentials (ห้าม commit)
├── .gitignore
├── worker/                   # Cloudflare Worker: ปุ่ม Refresh + cron ยิง workflow_dispatch
│   ├── src/index.js
│   └── wrangler.toml
└── .github/
    └── workflows/
        └── update.yml         # GitHub Actions (workflow_dispatch เท่านั้น ไม่มี schedule:)
```

---

## Credentials

| ที่เก็บ | ตัวแปร | ใช้ทำอะไร |
|---|---|---|
| `.env` (local, gitignored) + GitHub Actions Secrets | `JETTS_USERNAME`, `JETTS_PASSWORD` | login jettsapp (`scraper.py` อ่านจาก `os.environ[...]` เท่านั้น **ไม่มีค่า default** — ถ้าลืมตั้งจะ error ทันทีแทนที่จะ fallback ไปใช้ค่าที่หลุด) |
| GitHub Actions Secrets | `LINE_CHANNEL_TOKEN`, `LINE_USER_ID` | ส่ง push message เข้า LINE (`send_line.py`) |
| Cloudflare Worker secret (`wrangler secret put GH_TOKEN`) | `GH_TOKEN` | Worker ยิง `workflow_dispatch` แทนผู้ใช้ (ปุ่ม Refresh + cron รายวัน) — token ไม่โผล่ในโค้ด public |

ห้ามเขียนค่าจริงไว้ในไฟล์เอกสารหรือโค้ดใดๆ ที่จะถูก commit

---

## เป้าหมาย (Goals)

```python
GOAL_PT_SOLD  = 2_400_000 * 1.07   # 2,568,000 ฿
GOAL_MEMBER   = 125                  # สมาชิกรวม club
GOAL_MEM_EACH = 6                   # สมาชิกรายคน
```

---

## scraper.py — Logic สำคัญ

### URLs
| Report | URL |
|--------|-----|
| Login | `https://jettsapp.jetts.co.th` |
| PT Conduct | `https://jettsapp.jetts.co.th/PTConductCommissionReport` |
| PT Sold | `https://jettsapp.jetts.co.th/PTSoldCommissionReport` |
| Membership | `https://jettsapp.jetts.co.th/MemberRegisterReport` |

### ข้อควรระวัง
- ใช้ `wait_for_load_state("load")` **ไม่ใช่** `"networkidle"` (timeout บน GitHub Actions)
- Bootstrap multiselect ซ่อน → ใช้ `state="attached"` ไม่ใช่ `state="visible"`
- Club Jetts Robinson Ratchaphruek = value `'46'`
- Membership pagination: `span[page="N"].page_inactive`
- ต้องใส่ User-Agent Chrome/Macintosh ไม่งั้น headless ถูก block
- Exclude จาก membership: `BGPL_Ou_00936`, `ecommerce_website`, `Online` (ไม่ใช่เทรนเนอร์จริง)
- `USERNAME`/`PASSWORD` มาจาก `os.environ[...]` ตรงๆ (ไม่มี `.getenv(..., default)`) — ถ้าไม่ตั้ง env จะ `KeyError` ทันที ห้ามเติม default fallback กลับเข้าไปอีก

### ฟังก์ชันหลัก
- `login(page)` — เข้าสู่ระบบ
- `scrape_table(page, url, start, end)` — ดึงตาราง + expand รายบุคคล
- `scrape_membership(page, start, end)` — ดึง membership + pagination หลายหน้า

---

## generate_dashboard.py — Logic สำคัญ

โครงสร้างข้อมูล: รวม conduct/sold/membership เข้าเป็น list `trainers` (1 dict ต่อคน) โดยยึด
`conduct_ind` เป็นรายชื่อหลัก แล้ว join ด้วย `sold_by_id`/`mem_by_id` — เรียงลำดับด้วย `score`
(ผลรวม sold/sessions/trial/members ที่ normalize ด้วยค่า max ของแต่ละตัวชี้วัด เพื่อไม่ปนหน่วย)

### ฟังก์ชันหลัก
| ฟังก์ชัน | หน้าที่ |
|----------|---------|
| `pcolor(pct)` | สีตาม % (`#d03b3b` / `#eb6834` / `#0ca30c`) |
| `display_name(raw)` | ตัด prefix `RRA_`/`IBA_`/`BGPL_` + ตัด `_ID` ท้ายชื่อ |
| `pos_tag(pos_rate)` | ป้ายตำแหน่ง (ST/ET/PT/CM) จาก Position Rate |
| `grid_rows_html()` | สร้างแถวตารางเทรนเนอร์ (การ์ด + แถบกราฟในตัว) พร้อม `<span class="m-label">` สำหรับโหมดมือถือ |
| `_print_rules_css(prefix)` | generate กฎ CSS ชุดเดียวกัน ใช้ทั้งใน `@media print` และคลาส `.pdf-export` (กันค่าที่คำนวณไดนามิกหลุด sync กัน) |
| `fmt(v)` / `num(s)` | format ตัวเลขใส่ comma / แปลง string → float |
| `compact(v)` | format แบบย่อ เช่น `12.3k` |

### หน้าจอ (screen) กับ พิมพ์/PDF แยกกันเด็ดขาด
เดิมหน้าจอใช้ font/ระยะห่างขนาดเดียวกับที่คำนวณไว้สำหรับพิมพ์ (บีบให้พอดี A4 หน้าเดียว) ทำให้บนมือถือ
คอลัมน์ New Member ล้นออกนอก grid และชื่อเทรนเนอร์ถูกตัดเหลือ 3-4 ตัวอักษร (bug ที่แก้ไปแล้ว) — ตอนนี้:

- **หน้าจอ** ใช้ค่าคงที่อ่านง่าย (`.grid-row`, `.gr-name` ฯลฯ ใน base CSS) และมี
  `@media screen and (max-width:640px)` (สโคปเฉพาะ `screen` ไม่ปนกับตอนพิมพ์) ทำ layout
  เป็นการ์ดสแต็ก 1 คอลัมน์ พร้อม `.m-label` (PT Sold/PT Conducted/Fs+Ra/สมาชิกใหม่) กำกับแต่ละแถบ
- **พิมพ์/PDF** ใช้ขนาดไดนามิกที่คำนวณจากจำนวนเทรนเนอร์ (`ROW_MIN`/`ROW_MAX`/`PAGE_BUDGET`/`FIXED_OVERHEAD`
  ใน `generate_dashboard.py`) ให้พอดี A4 หน้าเดียวเสมอ ผ่าน `_print_rules_css()` — ใช้ซ้ำสองที่:
  `@media print` (Ctrl+P ปกติ) และคลาส `.pdf-export` (JS ใส่ชั่วคราวตอนกดปุ่ม "ดาวน์โหลด PDF")

### ปุ่ม "ดาวน์โหลด PDF" — ทำไมไม่ใช้ `window.print()`
Browser/OS print dialog (โดยเฉพาะ iOS AirPrint) ควบคุม header/footer (URL, วันที่) เอง โค้ดหน้าเว็บสั่งปิด
ไม่ได้ — จึงสร้างไฟล์ PDF จริงฝั่ง client ด้วย `html2canvas` + `jsPDF` (CDN, โหลดใน `<script>` ท้าย body)
แทน: ใส่คลาส `.pdf-export` บน `<body>` → capture `.a4` ที่ `windowWidth:900` (กัน mobile media query
มาปน) → build PDF → `pdf.save()` ดาวน์โหลด ไม่มี URL ติดมาแน่นอน (ทดสอบแล้ว)

---

## GitHub Actions (update.yml)

```yaml
on: workflow_dispatch   # ไม่มี schedule: — ดูเหตุผลใน "Cloudflare Worker" ด้านล่าง
python-version: '3.11'
secrets: JETTS_USERNAME, JETTS_PASSWORD, LINE_CHANNEL_TOKEN, LINE_USER_ID
steps: checkout → pip install playwright → playwright install chromium --with-deps
       → scraper.py → generate_dashboard.py → screenshot_dashboard.py
       → git add data.json index.html dashboard.png + commit + push
       → sleep 90 (รอ GitHub Pages deploy รูป) → send_line.py (continue-on-error: true)
```

---

## Cloudflare Worker (`worker/`) — ปุ่ม Refresh + cron รายวัน

`jetts-rra-refresh.rackoran.workers.dev` เป็น proxy เดียวที่ยิง GitHub `workflow_dispatch` API
(เก็บ `GH_TOKEN` เป็น Worker secret ไม่โผล่ในโค้ด public) ใช้ 2 ทาง:

1. **ปุ่ม "Refresh ข้อมูล"** บนหน้าเว็บ — fetch POST มาที่ Worker ตอนผู้ใช้กดเอง
2. **Cloudflare Cron Trigger** (`wrangler.toml` → `[triggers] crons = ["0 0 * * *"]` = 07:00 Bangkok)
   — ยิง `workflow_dispatch` ตรงเวลาทุกเช้าแทน `schedule:` ของ GitHub Actions เอง

**ทำไมไม่ใช้ GitHub `schedule:` ตรงๆ**: เคยพบว่า GitHub Actions scheduled runs ดีเลย์ ~2-3 ชม.
(บันทึกไว้ใน commit เก่า `df0c705`) ทำให้ควบคุมเวลาส่ง LINE ตอน 7:30 ไม่ได้ — Cloudflare Cron
แม่นยำกว่ามาก จึงย้ายให้เป็นตัวสั่งหลัก และถอด `schedule:` ออกจาก `update.yml` (กัน run ซ้ำสองครั้ง/วัน)

Deploy หลังแก้ `worker/`:
```bash
cd worker && npx wrangler deploy
```

---

## LINE notification (`screenshot_dashboard.py` + `send_line.py`)

LINE Messaging API **ไม่มี message type สำหรับแนบไฟล์ PDF ตรงๆ** (มีแค่ text/image/video/sticker/flex ฯลฯ)
จึงถ่ายภาพ dashboard เป็น PNG แทน:

1. `screenshot_dashboard.py` — Playwright เปิด `index.html` ในเครื่อง ใส่คลาส `.pdf-export`
   (สไตล์เดียวกับปุ่มดาวน์โหลด PDF) แล้ว screenshot element `.a4` → `dashboard.png`
2. commit + push `dashboard.png` ขึ้น GitHub Pages พร้อม `data.json`/`index.html`
3. รอ ~90 วินาทีให้ Pages build เสร็จ (LINE ต้องดึงรูปจาก URL จริงได้)
4. `send_line.py` — push message ชนิด `image` (ชี้ไป `dashboard.png` บน Pages) + `text` แนบลิงก์
   dashboard เต็ม ไปยัง `LINE_USER_ID` ผ่าน `https://api.line.me/v2/bot/message/push`

ขั้นตอนส่ง LINE ใน workflow ใส่ `continue-on-error: true` ไว้ — ส่งไม่สำเร็จก็ไม่กระทบการอัปเดต
dashboard หลัก (LINE Notify **ปิดให้บริการไปแล้วตั้งแต่ปี 2025** ต้องใช้ Messaging API เท่านั้น)

---

## การรันด้วยตัวเอง (Manual)

```bash
cd /Users/oran_raurhotmail.com/Jetts_RRA_Report
bash run.sh
```

`run.sh` จะ `cd` เข้าโฟลเดอร์ตัวเอง + `source .env` ให้อัตโนมัติ (ก่อนหน้านี้เคย `cd` ไปผิดโฟลเดอร์และ
ไม่โหลด `.env` เลย ทำให้ใช้ไม่ได้จริง — แก้แล้ว)

หรือแยกขั้นตอน:
```bash
set -a && source .env && set +a
python3 scraper.py
python3 generate_dashboard.py
python3 screenshot_dashboard.py   # ถ้าต้องการทดสอบรูปสำหรับ LINE ด้วย
git add data.json index.html dashboard.png
git commit -m "update: $(date +'%d/%m/%Y %H:%M')"
git push
```

### ถ้า push ไม่ได้ (remote ahead)
```bash
git status                 # เช็คว่ามีงานที่ยังไม่ push ค้างอยู่หรือไม่ก่อนเสมอ
git fetch origin
git reset --hard origin/main
# รัน scraper + generate ใหม่แล้ว push
```
⚠️ วิธีนี้ทิ้ง local commits ที่ไม่เคย push ทั้งหมด — **CLAUDE.md เคยหายไปเพราะเหตุนี้มาแล้ว** (ถูกแก้/สร้าง
ใน local commit ที่ไม่เคย push แล้วโดน `reset --hard` ทับ) กู้คืนได้จาก `git reflog` ถ้ายังไม่ถูก
garbage collect — แต่ทางที่ดีกว่าคือ **commit + push CLAUDE.md ทันทีหลังแก้ทุกครั้ง** อย่าปล่อยค้าง

---

## Dashboard Layout

```
[Topbar: ชื่อ + ปุ่ม Refresh ข้อมูล + ปุ่ม ดาวน์โหลด PDF]   (ไม่พิมพ์/ไม่อยู่ใน PDF)
[Header: ชื่อ report + ช่วงเวลา + อัพเดตล่าสุด]
[KPI tiles: Total Session | PT Sold | สมาชิกใหม่]
[Goal tiles: % PT Sold | % สมาชิกรวมคลับ]
[Grid: ผลงานรายบุคคล — #, ชื่อ, PT Sold, PT Conducted, Fs+Ra, สมาชิกใหม่ (แถบกราฟในตัว)]
[Footnote: คำอธิบายการเทียบแถบ]
```
มือถือ (`@media screen and (max-width:640px)`): grid เปลี่ยนเป็นการ์ดสแต็กต่อคน แต่ละ metric
มี label กำกับ (PT Sold / PT Conducted / Fs+Ra / สมาชิกใหม่) ไม่ตัดชื่อ ไม่มีคอลัมน์ไหนหลุดจอ

---

## ปัญหาที่เคยเจอและวิธีแก้

| ปัญหา | สาเหตุ | วิธีแก้ |
|-------|--------|---------|
| `networkidle` timeout | GitHub Actions ช้ากว่า Mac | เปลี่ยนเป็น `"load"` |
| Bootstrap multiselect ไม่เจอ | element ซ่อน (`display:none`) | `state="attached"` |
| Login timeout headless | site detect headless | ใส่ User-Agent Chrome |
| `document.querySelector(...).value` error | page ยังไม่โหลด | ใช้ `wait_for_selector` ก่อน |
| push rejected (remote ahead) | GitHub Actions push ก่อน | `git reset --hard origin/main` แล้วรัน scrape ใหม่ (ระวัง local commit ที่ไม่เคย push จะหาย) |
| `timedelta` import error | import ผิด | `from datetime import datetime as _dt, timedelta as _td` |
| **credential หลุดใน public repo** | `scraper.py` เคยมี `os.getenv("JETTS_USERNAME", "00936")` เป็น default fallback | เปลี่ยนเป็น `os.environ["JETTS_USERNAME"]` (ไม่มี default) — **ห้ามเติม default กลับเข้าไปอีกเด็ดขาด** |
| `run.sh` ใช้ไม่ได้ | `cd` ไปโฟลเดอร์อื่นที่ไม่มีอยู่จริง (`team-request-hub`) + ไม่โหลด `.env` | `cd "$(dirname "$0")"` + `source .env` |
| GitHub Actions `schedule:` ดีเลย์ ~2-3 ชม. | GitHub เอง (ยืนยันจาก commit เก่า) | ย้ายไปใช้ Cloudflare Cron Trigger ยิง `workflow_dispatch` แทน (ดูหัวข้อ Cloudflare Worker) |
| มือถือแสดงข้อมูลไม่ครบ (ชื่อถูกตัด, คอลัมน์ New Member หลุดจอ) | `@media(max-width:640px)` เดิมบีบ `grid-template-columns` เหลือ 3 คอลัมน์แต่ซ่อนแค่ 2 ใน 4 metric ทำให้ตัวที่ 4 ล้น grid | เขียนใหม่เป็น layout การ์ดสแต็ก (`grid-template-areas`) + label กำกับแต่ละแถบ, สโคป media query เป็น `screen` แยกจาก `print` เด็ดขาด |
| print/PDF มี URL เว็บไซต์ติดมา | browser print dialog (โดยเฉพาะ iOS AirPrint) ควบคุม header/footer เอง แก้จาก CSS/JS ไม่ได้ | สร้าง PDF จริงฝั่ง client ด้วย html2canvas+jsPDF แทนการเรียก `window.print()` |
| LINE ส่งไฟล์ PDF แนบตรงๆไม่ได้ | LINE Messaging API ไม่มี message type สำหรับไฟล์ | ถ่าย screenshot เป็น PNG แล้วส่งเป็น image message แทน |
