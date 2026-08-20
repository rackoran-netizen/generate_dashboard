import json

with open("data.json", encoding="utf-8") as f:
    data = json.load(f)

updated_at   = data["updated_at"]
period       = data["period"]
conduct_rows = data["conduct"]["rows"]
sold_rows    = data["sold"]["rows"]
# ตัด BGPL_Ou_00936 ออกจาก membership (บัญชีกลาง ไม่ใช่เทรนเนอร์จริง)
EXCLUDE_MEM = {"BGPL_Ou_00936", "ecommerce_website", "Online"}
mem_summary  = [r for r in data["membership"]["summary"] if r["sold_by"] not in EXCLUDE_MEM]
mem_total    = sum(r["count"] for r in mem_summary)

# Goals
GOAL_PT_SOLD  = 2_400_000 * 1.07   # 2,568,000 (รวม VAT 7%)
GOAL_MEMBER   = 125                  # เป้ารวมคลับ
GOAL_MEM_EACH = 6                    # เป้ารายบุคคล

conduct_summary = next((r for r in conduct_rows if "Ratchaphruek" in r.get("Trainer","")), {})
sold_summary    = next((r for r in sold_rows    if "Ratchaphruek" in r.get("Trainer","")), {})
conduct_ind     = [r for r in conduct_rows if r.get("Trainer","") and "Ratchaphruek" not in r["Trainer"]]
sold_ind        = [r for r in sold_rows    if r.get("Trainer","") and "Ratchaphruek" not in r["Trainer"]]

def num(v):
    try: return float(str(v).replace(",",""))
    except: return 0.0

def fmt(v):
    try: return f"{num(v):,.0f}"
    except: return str(v)

def pcolor(pct):
    if pct >= 100: return "#0ca30c"
    if pct >= 80:  return "#eb6834"
    return "#d03b3b"

def display_name(raw):
    """RRA_Ae_02227 -> Ae   (ตัด prefix สาขา + ตัด ID ต่อท้าย)"""
    n = raw
    for pre in ("RRA_", "IBA_", "BGPL_"):
        if n.startswith(pre):
            n = n[len(pre):]
            break
    return n.split("_")[0] if "_" in n else n

def pos_tag(pos_rate):
    if not pos_rate:
        return ""
    return pos_rate.split("-")[0].strip().upper()

# ─────────────────────────────────────────────────────────────
# รวมข้อมูล 3 แหล่ง (conduct / sold / membership) เข้าเป็น 1 แถวต่อเทรนเนอร์
# conduct_rows คือ "รายชื่อหลัก" (มีเทรนเนอร์ครบ 23 คนเสมอ)
# ─────────────────────────────────────────────────────────────
sold_by_id = {r["Trainer"]: num(r.get("Total Amount", "0")) for r in sold_ind}
mem_by_id  = {r["sold_by"]: r["count"] for r in mem_summary}

trainers = []
for r in conduct_ind:
    tid = r.get("Trainer", "")
    trainers.append({
        "id": tid,
        "name": display_name(tid),
        "pos": pos_tag(r.get("Position Rate", "")),
        # PT Conducted = เซสชันที่เทรนจริง ไม่รวม Fitstart/Trial (แยกออกมาเป็นตัวชี้วัดของตัวเอง)
        "sessions": num(r.get("Total Session (Expept Fitstart and Trial)", "0")),
        # ชั่วโมงเทรน = บริการลูกค้าตอนต้นของการขาย (Fitstart + Trial Session)
        "trial": num(r.get("Fitstart", "0")) + num(r.get("Trial Session", "0")),
        "sold": sold_by_id.get(tid, 0.0),
        "members": mem_by_id.get(tid, 0),
    })

sold_max     = max((t["sold"] for t in trainers), default=0) or 1
sessions_max = max((t["sessions"] for t in trainers), default=0) or 1
trial_max    = max((t["trial"] for t in trainers), default=0) or 1
members_max  = max((t["members"] for t in trainers), default=0) or 1

# ลำดับแถว: composite score (ใช้จัดอันดับเท่านั้น ไม่ใช้วาดกราฟ — หลีกเลี่ยงการรวมหน่วยที่ต่างกัน)
for t in trainers:
    t["score"] = (t["sold"] / sold_max) + (t["sessions"] / sessions_max) \
               + (t["trial"] / trial_max) + (t["members"] / members_max)
trainers.sort(key=lambda t: t["score"], reverse=True)

sold_actual = num(sold_summary.get("Total Amount", "0"))
sold_pct    = sold_actual / GOAL_PT_SOLD * 100
mem_pct     = mem_total / GOAL_MEMBER * 100
sc = pcolor(sold_pct)
mc = pcolor(mem_pct)

def compact(v):
    v = num(v)
    if v >= 1000:
        return f"{v/1000:.1f}k".replace(".0k", "k")
    return f"{v:,.0f}"

def grid_rows_html():
    rows = []
    for i, t in enumerate(trainers):
        sold_pct_w   = min(t["sold"] / sold_max * 100, 100)
        sess_pct_w   = min(t["sessions"] / sessions_max * 100, 100)
        trial_pct_w  = min(t["trial"] / trial_max * 100, 100)
        mem_pct_w    = min(t["members"] / GOAL_MEM_EACH * 100, 100)
        pos_html     = f'<span class="postag">{t["pos"]}</span>' if t["pos"] else ""
        sold_fill  = f'<div class="bar-fill sold" style="width:{sold_pct_w:.1f}%"></div>' if sold_pct_w > 0 else ""
        sess_fill  = f'<div class="bar-fill conduct" style="width:{sess_pct_w:.1f}%"></div>' if sess_pct_w > 0 else ""
        trial_fill = f'<div class="bar-fill trial" style="width:{trial_pct_w:.1f}%"></div>' if trial_pct_w > 0 else ""
        mem_fill   = f'<div class="bar-fill mem" style="width:{mem_pct_w:.1f}%"></div>' if mem_pct_w > 0 else ""
        rows.append(f"""<div class="grid-row">
          <div class="gr-rank">{i+1}</div>
          <div class="gr-name">{pos_html}{t['name']}</div>
          <div class="gr-metric m1">
            <span class="m-label">PT Sold</span>
            <div class="bar-track">{sold_fill}</div>
            <span class="bar-val">{fmt(t['sold'])}</span>
          </div>
          <div class="gr-metric m2">
            <span class="m-label">PT Conducted</span>
            <div class="bar-track">{sess_fill}</div>
            <span class="bar-val">{fmt(t['sessions'])}</span>
          </div>
          <div class="gr-metric m3">
            <span class="m-label">Fs+Ra</span>
            <div class="bar-track">{trial_fill}</div>
            <span class="bar-val">{fmt(t['trial'])}</span>
          </div>
          <div class="gr-metric m4">
            <span class="m-label">สมาชิกใหม่</span>
            <div class="bar-track">{mem_fill}</div>
            <span class="bar-val">{t['members']}/{GOAL_MEM_EACH}</span>
          </div>
        </div>""")
    return "".join(rows)

# ─────────────────────────────────────────────────────────────
# ปรับขนาดแถวในตารางอัตโนมัติตามจำนวนเทรนเนอร์ เพื่อให้พอดี A4 หน้าเดียวเสมอ
# (แถวยิ่งเยอะ ยิ่งย่อ แต่ไม่เล็กกว่า ROW_MIN เพื่อให้ยังอ่านออกเมื่อพิมพ์)
# งบประมาณอิงจากพื้นที่พิมพ์จริง A4 - margin 8mm ~ 1062px สูง วัดจริงแล้วส่วนอื่น
# (header/สรุป/เป้าหมาย/หัวตาราง/footnote) กินพื้นที่คงที่ ~352px โดยประมาณ
# วัดด้วย Chrome automation จริงก่อนปรับค่าคงที่เหล่านี้ (ดูรายงานท้ายไฟล์)
n_trainers   = len(trainers)
ROW_MIN      = 20.0   # px, แถวเล็กสุดที่ยังอ่านตัวเลขออกเมื่อพิมพ์
ROW_MAX      = 27.0   # px, แถวใหญ่สุด (ขนาดปัจจุบันที่ 23 คน)
PAGE_BUDGET  = 1000.0 # px, เผื่อ margin ปลอดภัยจากงบจริง ~1040px
FIXED_OVERHEAD = 352.0  # px, ส่วนที่ไม่ขึ้นกับจำนวนแถว (วัดจริงด้วย Chrome)

avail_for_rows = max(PAGE_BUDGET - FIXED_OVERHEAD, ROW_MIN)
row_h = (avail_for_rows / n_trainers) if n_trainers else ROW_MAX
row_h = max(ROW_MIN, min(ROW_MAX, row_h))
_t = (row_h - ROW_MIN) / (ROW_MAX - ROW_MIN)  # 0 (แน่นสุด) .. 1 (โปร่งสุด)

name_fs  = round(9.5 + _t * (12.0 - 9.5), 2)
rank_fs  = round(8.5 + _t * (9.5 - 8.5), 2)
val_fs   = round(9.0 + _t * (10.5 - 9.0), 2)
bar_h    = round(8.0 + _t * (11.0 - 8.0), 2)
row_pad  = round(max((row_h - name_fs * 1.3) / 2.0, 1.0), 2)  # เนื้อหาในแถวสูงตามบรรทัดชื่อ (line-height ~1.3x)
postag_fs = round(max(7.0, val_fs * 0.76), 2)

# ─────────────────────────────────────────────────────────────
# กฎ CSS สำหรับโหมดพิมพ์/PDF เท่านั้น (ไม่แตะ layout หน้าจอ)
# ใช้ generate ซ้ำ 2 ที่: @media print (Ctrl+P ปกติ) และ .pdf-export
# (คลาสที่ JS ใส่ชั่วคราวตอน capture ด้วย html2canvas สำหรับปุ่ม "ดาวน์โหลด PDF")
# เขียนเป็น list of (selector, declaration) แล้ว generate ทั้งสองแบบ
# เพื่อไม่ให้ค่าที่คำนวณไดนามิกด้านบนหลุด sync กันระหว่างสองโหมด
# ─────────────────────────────────────────────────────────────
_PRINT_RULES = [
    ("body", "background:#fff!important;"),
    (".topbar", "display:none!important;"),
    (".a4", "max-width:100%!important;margin:0!important;padding:0!important;box-shadow:none!important;border-radius:0!important;background:#fff!important;"),
    (".tile,.goal-tile,.grid-card", "border:1px solid #ddd!important;background:#fff!important;"),
    (".grid-row", f"padding:{row_pad}px 2px!important;"),
    (".gr-rank", f"font-size:{rank_fs}px!important;"),
    (".gr-name", f"font-size:{name_fs}px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;"),
    (".postag", f"font-size:{postag_fs}px!important;"),
    (".bar-track,.bar-fill", f"height:{bar_h}px!important;"),
    (".bar-val", f"font-size:{val_fs}px!important;width:48px!important;"),
    (".m-label", "display:none!important;"),
    (".grid-row:nth-child(even)", "background:#f7f7f5!important;-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;"),
    (".bar-fill,.pbar-fill,.sw", "-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;"),
]

def _print_rules_css(prefix):
    # prefix ว่าง = ใช้ตรงๆ ใน @media print, prefix = ".pdf-export " = ใช้กับคลาสที่ JS ใส่ให้ <body>
    # กรณี selector เป็น "body" เอง ต้องจับคู่ตัว body ที่มีคลาสนั้นตรงๆ (ไม่ใช่ descendant)
    lines = []
    for sel, decl in _PRINT_RULES:
        if sel.strip() == "body" and prefix:
            scoped = prefix.strip()
        else:
            scoped = ", ".join(f"{prefix}{s.strip()}" for s in sel.split(","))
        lines.append(f"  {scoped}{{{decl}}}")
    return "\n".join(lines)

html = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Jetts RRA — PT Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Thai:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}

:root{{
  --ink-1:#0b0b0b;
  --ink-2:#52514e;
  --ink-muted:#898781;
  --surface:#fcfcfb;
  --page:#f2f1ec;
  --line:#e1e0d9;
  --border:rgba(11,11,11,.10);
  --brand:#c0002a;
  --brand-dark:#8f0020;
  --gold:#c8952a;
  --sold:#d6342f;
  --conduct:#2a78d6;
  --trial:#8fcfc6;
  --member:#f2b705;
}}

body{{
  font-family:'Inter','Noto Sans Thai',system-ui,-apple-system,sans-serif;
  font-size:12px;color:var(--ink-1);
  background:var(--page);
  min-height:100vh;
}}

/* ─── Topbar (ไม่พิมพ์) ─── */
.topbar{{background:linear-gradient(100deg,var(--brand),var(--brand-dark));padding:9px 16px;display:flex;justify-content:space-between;align-items:center;}}
.topbar .brand{{font-size:14px;font-weight:800;color:#fff;letter-spacing:.2px;}}
.topbar .brand small{{display:block;font-weight:500;font-size:9.5px;color:rgba(255,255,255,.75);margin-top:1px;}}
.topbar-right{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end;}}
.print-btn{{background:#fff;color:var(--brand);border:none;border-radius:7px;padding:6px 14px;font-size:11.5px;font-weight:700;cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;font-family:inherit;}}
.print-btn:hover{{background:#ffe9ee;}}
.print-btn:disabled{{opacity:.6;cursor:default;}}
.refresh-status{{font-size:10px;color:rgba(255,255,255,.8);white-space:nowrap;}}

/* ─── Wrapper (หน้า A4) ─── */
.a4{{max-width:800px;margin:16px auto;padding:20px 24px;background:var(--surface);border-radius:10px;box-shadow:0 4px 24px rgba(0,0,0,.12);}}

/* ─── Header ─── */
.doc-header{{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid var(--brand);padding-bottom:11px;margin-bottom:14px;}}
.doc-title{{font-size:19px;font-weight:800;color:var(--brand);letter-spacing:.1px;}}
.doc-sub{{font-size:11px;color:var(--ink-muted);margin-top:3px;}}
.doc-meta{{text-align:right;font-size:11px;color:var(--ink-muted);line-height:1.55;}}
.doc-meta b{{color:var(--ink-2);font-weight:700;}}

/* ─── Stat / Goal tiles ─── */
.tile-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px;}}
.tile{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 14px;}}
.tile .lbl{{font-size:9.5px;color:var(--ink-muted);font-weight:600;text-transform:uppercase;letter-spacing:.3px;}}
.tile .val{{font-size:20px;font-weight:800;color:var(--ink-1);line-height:1.4;font-variant-numeric:tabular-nums;}}
.tile .val .unit{{font-size:11px;color:var(--ink-muted);font-weight:600;margin-left:3px;}}

.goal-row{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;}}
.goal-tile{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:10px 14px;}}
.goal-tile .gtitle{{font-size:10.5px;font-weight:700;color:var(--ink-2);margin-bottom:5px;}}
.goal-nums{{display:flex;align-items:baseline;gap:8px;}}
.goal-pct{{font-size:24px;font-weight:800;line-height:1;font-variant-numeric:tabular-nums;}}
.goal-actual{{font-size:10.5px;color:var(--ink-muted);font-variant-numeric:tabular-nums;}}
.pbar{{height:6px;background:var(--line);border-radius:3px;margin:7px 0 4px;overflow:hidden;}}
.pbar-fill{{height:6px;border-radius:3px;}}
.goal-note{{font-size:10px;color:var(--ink-muted);}}

/* ─── Section title + legend ─── */
.st-row{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:7px;}}
.st{{font-size:13px;font-weight:700;color:var(--ink-1);}}
.legend{{display:flex;gap:12px;font-size:10px;color:var(--ink-2);}}
.legend span{{display:inline-flex;align-items:center;gap:4px;}}
.sw{{width:9px;height:9px;border-radius:2px;display:inline-block;}}
.sw.sold{{background:var(--sold);}}
.sw.conduct{{background:var(--conduct);}}
.sw.trial{{background:var(--trial);}}
.sw.mem{{background:var(--member);}}

/* ─── Trainer grid (ตาราง + กราฟแท่งแนวนอนในตัว) — ใช้ค่าคงที่ที่อ่านง่ายบนจอ ─── */
.grid-card{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 14px 6px;}}
.grid-head,.grid-row{{
  display:grid;
  grid-template-columns:20px 76px 1fr 1fr 1fr 1fr;
  column-gap:9px;
  align-items:center;
}}
.grid-head{{padding:4px 2px 7px;border-bottom:1.5px solid var(--ink-1);}}
.grid-head > div{{font-size:9.5px;font-weight:700;color:var(--ink-2);text-transform:uppercase;letter-spacing:.2px;}}
.grid-head .gh-m{{display:flex;align-items:center;gap:4px;}}
.grid-body{{display:flex;flex-direction:column;}}
.grid-row:last-child{{border-bottom:none;}}
.grid-row:nth-child(even){{background:#faf9f6;}}
.postag{{display:inline-block;font-weight:700;color:var(--ink-muted);border:1px solid var(--line);border-radius:3px;padding:0 3px;margin-right:4px;vertical-align:middle;}}
.gr-metric{{display:flex;align-items:center;gap:7px;}}
.m-label{{display:none;flex:0 0 auto;font-size:10px;color:var(--ink-muted);}}
.bar-track{{flex:1;min-width:0;background:var(--line);border-radius:3px;overflow:hidden;}}
.bar-fill{{border-radius:3px;min-width:3px;}}
.bar-fill.sold{{background:var(--sold);}}
.bar-fill.conduct{{background:var(--conduct);}}
.bar-fill.trial{{background:var(--trial);}}
.bar-fill.mem{{background:var(--member);}}
.bar-val{{flex:0 0 auto;width:52px;text-align:right;font-weight:700;color:var(--ink-2);font-variant-numeric:tabular-nums;}}

.grid-row{{padding:8px 2px;border-bottom:1px solid var(--line);}}
.gr-rank{{font-size:11px;color:var(--ink-muted);text-align:center;font-variant-numeric:tabular-nums;}}
.gr-name{{font-size:13px;font-weight:700;color:var(--ink-1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.postag{{font-size:9.5px;}}
.bar-track,.bar-fill{{height:10px;}}
.bar-val{{font-size:11.5px;}}

.footnote{{margin-top:10px;font-size:9.5px;color:var(--ink-muted);text-align:center;line-height:1.5;}}

/* ════════════════════════════════════════════════════════════════
   PRINT / PDF EXPORT — แยกจากหน้าจอโดยสิ้นเชิง
   ใช้ขนาดไดนามิกที่คำนวณจากจำนวนเทรนเนอร์ (n_trainers={n_trainers})
   ให้พอดี A4 หนึ่งหน้าเสมอ ไม่ยุ่งกับ layout หน้าจอ/มือถือเลย
   .pdf-export = คลาสที่ JS ใส่ชั่วคราวตอน capture ด้วย html2canvas
   (ปุ่ม "ดาวน์โหลด PDF") ส่วน @media print ใช้ตอนกด Ctrl+P ปกติ
   ═══════════════════════════════════════════════════════════════ */
@media print{{
  @page{{size:A4 portrait;margin:8mm;}}
{_print_rules_css("")}
}}
{_print_rules_css(".pdf-export ")}

/* ─── Mobile screen (จอเล็ก) — เฉพาะตอนดูบนจอ ไม่เกี่ยวกับพิมพ์/PDF ─── */
@media screen and (max-width:640px){{
  .a4{{margin:10px auto;padding:14px 12px;border-radius:8px;}}
  .topbar{{flex-wrap:wrap;row-gap:8px;padding:10px 12px;}}
  .doc-header{{flex-direction:column;gap:8px;}}
  .doc-meta{{text-align:left;}}
  .tile-row{{grid-template-columns:1fr 1fr;}}
  .goal-row{{grid-template-columns:1fr;}}
  .st-row{{flex-direction:column;align-items:flex-start;gap:6px;}}
  .legend{{flex-wrap:wrap;gap:8px 12px;}}

  .grid-head{{display:none;}}
  .grid-row{{
    display:grid;
    grid-template-columns:22px 1fr;
    grid-template-areas:
      "rank name"
      "m1 m1"
      "m2 m2"
      "m3 m3"
      "m4 m4";
    row-gap:6px;
    padding:12px 4px;
  }}
  .gr-rank{{grid-area:rank;font-size:12px;}}
  .gr-name{{grid-area:name;font-size:14.5px;white-space:normal;overflow:visible;text-overflow:unset;}}
  .gr-metric.m1{{grid-area:m1;}}
  .gr-metric.m2{{grid-area:m2;}}
  .gr-metric.m3{{grid-area:m3;}}
  .gr-metric.m4{{grid-area:m4;}}
  .m-label{{display:inline-block;width:76px;}}
  .bar-val{{width:auto;min-width:56px;font-size:12.5px;}}
  .bar-track,.bar-fill{{height:11px;}}
}}
</style>
</head>
<body>

<div class="topbar no-print">
  <div class="brand">Jetts RRA — PT Performance Dashboard<small>Robinson Ratchaphruek</small></div>
  <div class="topbar-right">
    <span id="refreshStatus" class="refresh-status"></span>
    <button class="print-btn" id="refreshBtn" onclick="triggerRefresh()" title="สั่งดึงข้อมูลใหม่ 1 คลิก">
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
      Refresh ข้อมูล
    </button>
    <button class="print-btn" id="pdfBtn" onclick="downloadPDF()" title="ดาวน์โหลดไฟล์ PDF สำหรับพิมพ์/แชร์ (ไม่มี URL เว็บไซต์ติดมา)">
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M5 20h14v-2H5v2zM19 9h-4V3H9v6H5l7 7 7-7z"/></svg>
      ดาวน์โหลด PDF
    </button>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js"></script>
<script>
async function triggerRefresh() {{
  const btn = document.getElementById('refreshBtn');
  const status = document.getElementById('refreshStatus');
  btn.disabled = true;
  status.textContent = 'กำลังสั่งดึงข้อมูล...';
  try {{
    const res = await fetch('https://jetts-rra-refresh.rackoran.workers.dev/', {{ method: 'POST' }});
    if (res.ok) {{
      status.textContent = 'สั่งแล้ว รอ ~1-2 นาทีแล้วรีเฟรชหน้านี้';
    }} else {{
      status.textContent = 'สั่งไม่สำเร็จ (' + res.status + ')';
    }}
  }} catch (e) {{
    status.textContent = 'เชื่อมต่อไม่ได้ ลองใหม่อีกครั้ง';
  }}
  btn.disabled = false;
}}

// สร้างไฟล์ PDF จริงฝั่ง client (html2canvas + jsPDF) แทนการเรียก window.print()
// เพราะ browser/OS print dialog (โดยเฉพาะ AirPrint บน iPhone) ควบคุม header/footer
// (URL, วันที่) เองไม่สามารถปิดจากโค้ดหน้าเว็บได้ — วิธีนี้จึงการันตีว่าไม่มี URL ติดมา
async function downloadPDF() {{
  const btn = document.getElementById('pdfBtn');
  const status = document.getElementById('refreshStatus');
  const prevStatus = status.textContent;
  btn.disabled = true;
  status.textContent = 'กำลังสร้าง PDF...';
  document.body.classList.add('pdf-export');
  await new Promise(r => setTimeout(r, 60)); // ให้ browser reflow ด้วยสไตล์โหมดพิมพ์ก่อน capture
  try {{
    const target = document.querySelector('.a4');
    const canvas = await html2canvas(target, {{
      scale: 2,
      backgroundColor: '#ffffff',
      windowWidth: 900,   // บังคับให้ render เท่าจอเดสก์ท็อป ไม่ให้ mobile layout มาปน
      useCORS: true
    }});
    const {{ jsPDF }} = window.jspdf;
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const imgW = pageW;
    const imgH = Math.min(canvas.height * imgW / canvas.width, pageH);
    pdf.addImage(canvas.toDataURL('image/jpeg', 0.95), 'JPEG', 0, 0, imgW, imgH);
    pdf.save('Jetts_RRA_Report.pdf');
    status.textContent = 'ดาวน์โหลด PDF แล้ว';
  }} catch (e) {{
    console.error(e);
    status.textContent = 'สร้าง PDF ไม่สำเร็จ ลองใหม่อีกครั้ง';
  }}
  document.body.classList.remove('pdf-export');
  btn.disabled = false;
  setTimeout(() => {{ status.textContent = prevStatus; }}, 4000);
}}
</script>

<div class="a4">

  <!-- Doc Header -->
  <div class="doc-header">
    <div>
      <div class="doc-title">Report — Jetts Robinson Ratchaphruek</div>
      <div class="doc-sub">ช่วงเวลา {period['start']} – {period['end']}</div>
    </div>
    <div class="doc-meta">
      อัพเดต <b>{updated_at}</b><br>
      เทรนเนอร์ทั้งหมด <b>{len(trainers)}</b> คน
    </div>
  </div>

  <!-- KPI tiles -->
  <div class="tile-row">
    <div class="tile">
      <div class="lbl">Total Session</div>
      <div class="val">{conduct_summary.get('Total Session','—')}<span class="unit">ครั้ง</span></div>
    </div>
    <div class="tile">
      <div class="lbl">PT Sold</div>
      <div class="val">{fmt(sold_actual)}<span class="unit">฿</span></div>
    </div>
    <div class="tile">
      <div class="lbl">สมาชิกใหม่</div>
      <div class="val">{mem_total}<span class="unit">คน</span></div>
    </div>
  </div>

  <!-- Goal tiles -->
  <div class="goal-row">
    <div class="goal-tile">
      <div class="gtitle">เป้าหมาย PT Sold (2,400,000 + VAT 7%)</div>
      <div class="goal-nums">
        <div class="goal-pct" style="color:{sc};">{sold_pct:.1f}%</div>
        <div class="goal-actual">{fmt(sold_actual)} / {fmt(GOAL_PT_SOLD)} ฿</div>
      </div>
      <div class="pbar"><div class="pbar-fill" style="width:{min(sold_pct,100):.1f}%;background:{sc};"></div></div>
      <div class="goal-note">{'✅ บรรลุเป้าแล้ว' if sold_pct >= 100 else f'คงเหลือ {fmt(GOAL_PT_SOLD - sold_actual)} ฿'}</div>
    </div>
    <div class="goal-tile">
      <div class="gtitle">เป้าหมายสมาชิกรวมคลับ ({GOAL_MEMBER} คน)</div>
      <div class="goal-nums">
        <div class="goal-pct" style="color:{mc};">{mem_pct:.1f}%</div>
        <div class="goal-actual">{mem_total} / {GOAL_MEMBER} คน</div>
      </div>
      <div class="pbar"><div class="pbar-fill" style="width:{min(mem_pct,100):.1f}%;background:{mc};"></div></div>
      <div class="goal-note">{'✅ บรรลุเป้าแล้ว' if mem_pct >= 100 else f'คงเหลือ {GOAL_MEMBER - mem_total} คน'}</div>
    </div>
  </div>

  <!-- Trainer grid: PT Sold + PT Conducted + New Member รวมรายคน -->
  <div class="st-row">
    <div class="st">ผลงานรายบุคคล — เรียงตามคะแนนรวม 4 ตัวชี้วัด</div>
    <div class="legend">
      <span><span class="sw sold"></span>PT Sold</span>
      <span><span class="sw conduct"></span>PT Conducted</span>
      <span><span class="sw trial"></span>Fs+Ra</span>
      <span><span class="sw mem"></span>New Member</span>
    </div>
  </div>
  <div class="grid-card">
    <div class="grid-head">
      <div class="gh-r">#</div>
      <div class="gh-n">เทรนเนอร์</div>
      <div class="gh-m gh-m1">PT Sold (฿)</div>
      <div class="gh-m gh-m2">PT Conducted (ครั้ง)</div>
      <div class="gh-m gh-m3">Fs+Ra (ครั้ง)</div>
      <div class="gh-m gh-m4">สมาชิกใหม่ (เป้า {GOAL_MEM_EACH})</div>
    </div>
    <div class="grid-body">{grid_rows_html()}</div>
  </div>

  <div class="footnote">ความยาวแท่งของ PT Sold, PT Conducted และ Fs+Ra เทียบกับค่าสูงสุดของแต่ละตัวชี้วัดในทีม &nbsp;·&nbsp; แท่งสมาชิกใหม่เทียบกับเป้าหมายรายบุคคล {GOAL_MEM_EACH} คน &nbsp;·&nbsp; PT Conducted ไม่รวม Fitstart/Trial (แยกเป็น Fs+Ra)</div>

</div><!-- /a4 -->

</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("สร้าง index.html แล้ว")
