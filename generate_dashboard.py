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
        "sessions": num(r.get("Total Session", "0")),
        "sold": sold_by_id.get(tid, 0.0),
        "members": mem_by_id.get(tid, 0),
    })

sold_max     = max((t["sold"] for t in trainers), default=0) or 1
sessions_max = max((t["sessions"] for t in trainers), default=0) or 1
members_max  = max((t["members"] for t in trainers), default=0) or 1

# ลำดับแถว: composite score (ใช้จัดอันดับเท่านั้น ไม่ใช้วาดกราฟ — หลีกเลี่ยงการรวมหน่วยที่ต่างกัน)
for t in trainers:
    t["score"] = (t["sold"] / sold_max) + (t["sessions"] / sessions_max) + (t["members"] / members_max)
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
        mem_pct_w    = min(t["members"] / GOAL_MEM_EACH * 100, 100)
        pos_html     = f'<span class="postag">{t["pos"]}</span>' if t["pos"] else ""
        sold_fill = f'<div class="bar-fill sold" style="width:{sold_pct_w:.1f}%"></div>' if sold_pct_w > 0 else ""
        sess_fill = f'<div class="bar-fill conduct" style="width:{sess_pct_w:.1f}%"></div>' if sess_pct_w > 0 else ""
        mem_fill  = f'<div class="bar-fill mem" style="width:{mem_pct_w:.1f}%"></div>' if mem_pct_w > 0 else ""
        rows.append(f"""<div class="grid-row">
          <div class="gr-rank">{i+1}</div>
          <div class="gr-name">{pos_html}{t['name']}</div>
          <div class="gr-metric">
            <div class="bar-track">{sold_fill}</div>
            <span class="bar-val">{fmt(t['sold'])}</span>
          </div>
          <div class="gr-metric">
            <div class="bar-track">{sess_fill}</div>
            <span class="bar-val">{fmt(t['sessions'])}</span>
          </div>
          <div class="gr-metric">
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
.topbar-right{{display:flex;align-items:center;gap:10px;}}
.print-hint{{font-size:9.5px;color:rgba(255,255,255,.8);max-width:260px;line-height:1.35;text-align:right;}}
.print-btn{{background:#fff;color:var(--brand);border:none;border-radius:7px;padding:6px 14px;font-size:11.5px;font-weight:700;cursor:pointer;white-space:nowrap;}}
.print-btn:hover{{background:#ffe9ee;}}

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
.sw.mem{{background:var(--member);}}

/* ─── Trainer grid (ตาราง + กราฟแท่งแนวนอนในตัว) ─── */
.grid-card{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 14px 6px;}}
.grid-head,.grid-row{{
  display:grid;
  grid-template-columns:20px 74px 1fr 1fr 1fr;
  column-gap:12px;
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
.bar-track{{flex:1;min-width:0;background:var(--line);border-radius:3px;overflow:hidden;}}
.bar-fill{{border-radius:3px;min-width:3px;}}
.bar-fill.sold{{background:var(--sold);}}
.bar-fill.conduct{{background:var(--conduct);}}
.bar-fill.mem{{background:var(--member);}}
.bar-val{{flex:0 0 auto;width:58px;text-align:right;font-weight:700;color:var(--ink-2);font-variant-numeric:tabular-nums;}}

/* ─── ขนาดแถวไดนามิก: คำนวณจากจำนวนเทรนเนอร์ (n_trainers={n_trainers}) ให้พอดี A4 เสมอ ─── */
.grid-row{{padding:{row_pad}px 2px;border-bottom:1px solid var(--line);}}
.gr-rank{{font-size:{rank_fs}px;color:var(--ink-muted);text-align:center;font-variant-numeric:tabular-nums;}}
.gr-name{{font-size:{name_fs}px;font-weight:700;color:var(--ink-1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.postag{{font-size:{postag_fs}px;}}
.bar-track,.bar-fill{{height:{bar_h}px;}}
.bar-val{{font-size:{val_fs}px;}}

.footnote{{margin-top:10px;font-size:9.5px;color:var(--ink-muted);text-align:center;line-height:1.5;}}

/* ════════════ PRINT ════════════ */
@media print{{
  @page{{size:A4 portrait;margin:8mm;}}
  html,body{{background:#fff!important;}}
  .topbar{{display:none!important;}}
  .a4{{max-width:100%;margin:0;padding:0;box-shadow:none!important;border-radius:0;}}
  .tile,.goal-tile,.grid-card{{border:1px solid #ddd!important;}}
  .grid-row:nth-child(even){{background:#f7f7f5!important;-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
  .bar-fill,.pbar-fill,.sw{{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
}}

/* ─── Mobile (จอเล็ก) ─── */
@media(max-width:640px){{
  .tile-row{{grid-template-columns:1fr 1fr;}}
  .goal-row{{grid-template-columns:1fr;}}
  .grid-head,.grid-row{{grid-template-columns:14px 50px 1fr;row-gap:2px;}}
  .grid-head .gh-c,.grid-head .gh-m2,.gr-metric.m2{{display:none;}}
}}
</style>
</head>
<body>

<div class="topbar no-print">
  <div class="brand">Jetts RRA — PT Performance Dashboard<small>Robinson Ratchaphruek</small></div>
  <div class="topbar-right">
    <div class="print-hint">เคล็ดลับ: ก่อนกดพิมพ์ ให้ปิดตัวเลือก "Headers and footers" ในหน้าต่างพิมพ์ของเบราว์เซอร์ เพื่อไม่ให้แสดง URL/วันที่บนกระดาษ</div>
    <button class="print-btn" onclick="window.print()">🖨 พิมพ์ A4</button>
  </div>
</div>

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
    <div class="st">ผลงานรายบุคคล — เรียงตามคะแนนรวม 3 ตัวชี้วัด</div>
    <div class="legend">
      <span><span class="sw sold"></span>PT Sold</span>
      <span><span class="sw conduct"></span>PT Conducted</span>
      <span><span class="sw mem"></span>New Member</span>
    </div>
  </div>
  <div class="grid-card">
    <div class="grid-head">
      <div class="gh-r">#</div>
      <div class="gh-n">เทรนเนอร์</div>
      <div class="gh-m gh-m1">PT Sold (฿)</div>
      <div class="gh-m gh-m2">PT Conducted (ครั้ง)</div>
      <div class="gh-m gh-m3">สมาชิกใหม่ (เป้า {GOAL_MEM_EACH})</div>
    </div>
    <div class="grid-body">{grid_rows_html()}</div>
  </div>

  <div class="footnote">ความยาวแท่งของ PT Sold และ PT Conducted เทียบกับค่าสูงสุดของแต่ละตัวชี้วัดในทีม &nbsp;·&nbsp; แท่งสมาชิกใหม่เทียบกับเป้าหมายรายบุคคล {GOAL_MEM_EACH} คน</div>

</div><!-- /a4 -->

</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("สร้าง index.html แล้ว")
