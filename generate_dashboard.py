import json

with open("data.json", encoding="utf-8") as f:
    data = json.load(f)

updated_at   = data["updated_at"]
period       = data["period"]
conduct_rows = data["conduct"]["rows"]
sold_rows    = data["sold"]["rows"]
# ตัด BGPL_Ou_00936 ออกจาก membership
EXCLUDE_MEM = {"BGPL_Ou_00936"}
mem_summary  = [r for r in data["membership"]["summary"] if r["sold_by"] not in EXCLUDE_MEM]
mem_total    = sum(r["count"] for r in mem_summary)

# Goals
GOAL_PT_SOLD  = 2_000_000 * 1.07   # 2,140,000 (รวม VAT 7%)
GOAL_MEMBER   = 100                  # เป้ารวมคลับ
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

conduct_sorted = sorted(conduct_ind, key=lambda r: num(r.get("Total Commission","0")), reverse=True)
sold_sorted    = sorted(sold_ind,    key=lambda r: num(r.get("Total Amount","0")), reverse=True)

sold_actual = num(sold_summary.get("Total Amount","0"))
sold_pct    = sold_actual / GOAL_PT_SOLD * 100
mem_pct     = mem_total / GOAL_MEMBER * 100

def pcolor(pct):
    if pct >= 100: return "#2e7d32"
    if pct >= 80:  return "#f57c00"
    return "#c0002a"

def badge(pos):
    cls = pos.lower().replace("-","")
    return f'<span class="bp {cls}">{pos}</span>'

def medal(i):
    return ["🥇","🥈","🥉"][i] if i < 3 else str(i+1)

def mem_bar(count):
    pct = min(count / GOAL_MEM_EACH * 100, 100)
    if count >= GOAL_MEM_EACH: c = "#2e7d32"
    elif count >= GOAL_MEM_EACH - 2: c = "#f57c00"
    else: c = "#c0002a"
    return f'''<div style="display:flex;align-items:center;gap:4px;">
      <span style="font-weight:700;color:{c};min-width:18px;">{count}</span>
      <div style="flex:1;height:5px;background:#eee;border-radius:3px;">
        <div style="width:{pct:.0f}%;height:5px;background:{c};border-radius:3px;"></div>
      </div>
      <span style="font-size:9px;color:#aaa;">/{GOAL_MEM_EACH}</span>
    </div>'''

def conduct_rows_html():
    rows = ""
    for i, r in enumerate(conduct_sorted):
        name = r.get("Trainer","").replace("RRA_","")
        rows += f"""<tr>
          <td class="tc">{medal(i)}</td>
          <td>{badge(r.get("Position Rate",""))} {name}</td>
          <td class="tr">{r.get("Fitstart","")}</td>
          <td class="tr">{r.get("Trial Session","")}</td>
          <td class="tr fw">{r.get("Total Session","")}</td>
        </tr>"""
    return rows

def sold_rows_html():
    rows = ""
    for i, r in enumerate(sold_sorted):
        name = r.get("Trainer","").replace("RRA_","")
        rows += f"""<tr>
          <td class="tc">{medal(i)}</td>
          <td>{badge(r.get("Position Rate",""))} {name}</td>
          <td class="tr fw">{fmt(r.get("Total Amount","0"))}</td>
          <td class="tr">{fmt(r.get("Amount Before VAT","0"))}</td>
        </tr>"""
    return rows

def mem_rows_html():
    rows = ""
    for i, r in enumerate(mem_summary):
        name = r["sold_by"].replace("RRA_","")
        rows += f"""<tr>
          <td class="tc">{medal(i)}</td>
          <td>{name}</td>
          <td>{mem_bar(r["count"])}</td>
        </tr>"""
    return rows

# Chart data — conduct ใช้ Total Session แทน Commission
c_names = [r.get("Trainer","").replace("RRA_","") for r in conduct_sorted[:12]]
c_vals  = [num(r.get("Total Session","0")) for r in conduct_sorted[:12]]
s_names = [r.get("Trainer","").replace("RRA_","") for r in sold_sorted[:12]]
s_vals  = [num(r.get("Total Amount","0")) for r in sold_sorted[:12]]
# จัดกลุ่ม membership: คนที่ยอดเท่ากันอยู่กลุ่มเดียวกัน
from collections import defaultdict as _dd
_count_groups = _dd(list)
for _r in mem_summary:
    _count_groups[_r["count"]].append(_r["sold_by"].replace("RRA_",""))
_grouped = sorted(_count_groups.items(), key=lambda x: x[0], reverse=True)
m_names = [", ".join(names) for count, names in _grouped]
m_vals  = [count for count, names in _grouped]

sc = pcolor(sold_pct)
mc = pcolor(mem_pct)

html = f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>Jetts RRA — PT Dashboard</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{
  font-family:'Segoe UI',sans-serif;font-size:12px;color:#222;
  min-height:100vh;
  /* พื้นหลัง: ดำ + เส้น Red & Gold */
  background-color:#0d0d0d;
  background-image:
    repeating-linear-gradient(45deg,  transparent, transparent 60px, rgba(192,0,42,.12) 60px,  rgba(192,0,42,.12) 61px),
    repeating-linear-gradient(-45deg, transparent, transparent 80px, rgba(200,149,42,.08) 80px, rgba(200,149,42,.08) 81px),
    linear-gradient(160deg, rgba(192,0,42,.06) 0%, transparent 40%, rgba(200,149,42,.06) 100%);
}}

/* ─── Navbar ─── */
.topbar{{background:#c0002a;padding:7px 14px;display:flex;justify-content:space-between;align-items:center;}}
.topbar .brand{{font-size:14px;font-weight:700;color:white;}}
.topbar .upd{{font-size:10px;color:rgba(255,255,255,.7);}}
.print-btn{{background:white;color:#c0002a;border:none;border-radius:6px;padding:4px 12px;font-size:11px;font-weight:700;cursor:pointer;}}
.print-btn:hover{{background:#ffe;}}

/* ─── Wrapper ─── */
.a4{{max-width:980px;margin:0 auto;padding:12px 14px;}}

/* ─── Header ─── */
.doc-header{{display:flex;justify-content:space-between;align-items:flex-start;background:white;border-radius:10px;padding:10px 14px;border-left:4px solid #c0002a;margin-bottom:10px;box-shadow:0 2px 8px rgba(0,0,0,.3);}}
.doc-title{{font-size:15px;font-weight:800;color:#c0002a;}}
.doc-sub{{font-size:10px;color:#888;margin-top:2px;}}
.doc-meta{{text-align:right;font-size:10px;color:#aaa;}}

/* ─── Summary strip ─── */
.sum-strip{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;}}
.sum-box{{background:white;border-radius:10px;padding:10px 12px;box-shadow:0 2px 8px rgba(0,0,0,.25);border-top:3px solid #c0002a;}}
.sum-box .lbl{{font-size:9px;color:#999;}}
.sum-box .val{{font-size:15px;font-weight:800;color:#c0002a;line-height:1.3;}}
.sum-box .unit{{font-size:9px;color:#bbb;}}

/* ─── Goal cards ─── */
.goal-row{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;}}
.goal-box{{background:white;border-radius:10px;padding:10px 14px;box-shadow:0 2px 8px rgba(0,0,0,.25);}}
.goal-box .gtitle{{font-size:10px;font-weight:700;color:#555;margin-bottom:5px;}}
.goal-nums{{display:flex;align-items:baseline;gap:8px;}}
.goal-pct{{font-size:24px;font-weight:900;line-height:1;}}
.goal-actual{{font-size:10px;color:#999;}}
.pbar{{height:6px;background:#eee;border-radius:3px;margin:6px 0 4px;}}
.pbar-fill{{height:6px;border-radius:3px;}}
.goal-note{{font-size:9px;color:#aaa;}}

/* ─── Section title ─── */
.st{{font-size:11px;font-weight:700;color:#c0002a;border-left:3px solid #c0002a;padding-left:6px;margin-bottom:6px;}}

/* ─── Cards ─── */
.card-wrap{{background:white;border-radius:10px;padding:10px 12px;box-shadow:0 2px 8px rgba(0,0,0,.25);}}
.tbox{{margin-bottom:10px;}}

/* ─── Tables ─── */
table{{width:100%;border-collapse:collapse;}}
thead th{{background:#c0002a;color:white;font-size:10px;font-weight:600;padding:4px 6px;white-space:nowrap;}}
tbody td{{font-size:11px;padding:4px 6px;border-bottom:1px solid #f0f0f0;vertical-align:middle;}}
tbody tr:last-child td{{border-bottom:none;}}
tbody tr:nth-child(even){{background:#fafafa;}}
tbody tr:hover td{{background:#fff5f7;}}
.tc{{text-align:center;width:22px;}}
.tr{{text-align:right;}}
.fw{{font-weight:700;}}
.green{{color:#2e7d32;font-weight:600;}}
.bp{{display:inline-block;padding:1px 4px;border-radius:5px;font-size:9px;font-weight:700;margin-right:2px;}}
.etred{{background:#ffe0e0;color:#c0002a;}}
.stred{{background:#fff0e0;color:#c06000;}}
.ptred{{background:#e0eeff;color:#1565c0;}}

/* ─── Charts ─── */
.chart-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px;}}
.chart-box{{background:white;border-radius:10px;padding:10px 12px;box-shadow:0 2px 8px rgba(0,0,0,.25);}}
.chart-inner{{position:relative;}}

/* ─── Table layout ─── */
.table-row-3{{display:grid;grid-template-columns:3fr 2fr;gap:8px;margin-bottom:10px;}}

/* ════════════ PRINT ════════════ */
@media print{{
  @page{{size:A4 portrait;margin:8mm;}}
  body{{background:#fff!important;background-image:none!important;font-size:10px;}}
  .topbar{{display:none!important;}}
  .a4{{max-width:100%;padding:0;}}
  .sum-box,.goal-box,.card-wrap,.chart-box,.doc-header{{
    box-shadow:none!important;border:1px solid #ddd!important;}}
  .chart-inner{{height:160px!important;}}
  tbody td{{font-size:9.5px!important;padding:2px 5px!important;}}
  thead th{{font-size:9px!important;padding:3px 5px!important;}}
}}

/* ─── Mobile ─── */
@media(max-width:600px){{
  .sum-strip{{grid-template-columns:repeat(2,1fr);gap:6px;}}
  .goal-row,.chart-row,.table-row-3{{grid-template-columns:1fr;}}
  .a4{{padding:8px;}}
}}
@media(min-width:601px) and (max-width:860px){{
  .chart-row{{grid-template-columns:1fr 1fr;}}
  .table-row-3{{grid-template-columns:1fr;}}
}}
</style>
</head>
<body>

<div class="topbar no-print">
  <span class="brand">Jetts RRA — PT Dashboard</span>
  <button class="print-btn" onclick="window.print()">🖨 พิมพ์ A4</button>
</div>

<div class="a4">

  <!-- Doc Header -->
  <div class="doc-header">
    <div>
      <div class="doc-title">Report — Jetts Robinson Ratchaphruek</div>
      <div class="doc-sub">ช่วงเวลา: {period['start']} — {period['end']} &nbsp;|&nbsp; อัพเดต: {updated_at}</div>
    </div>
    <div style="text-align:right;font-size:10px;color:#aaa;">
      Conduct: {len(conduct_sorted)} Trainers<br>
      Sold: {len(sold_sorted)} Trainers
    </div>
  </div>

  <!-- Summary Strip (4 การ์ด) -->
  <div class="sum-strip">
    <div class="sum-box">
      <div class="lbl">Total Session</div>
      <div class="val">{conduct_summary.get('Total Session','—')}</div>
      <div class="unit">ครั้ง</div>
    </div>
    <div class="sum-box">
      <div class="lbl">PT Sold</div>
      <div class="val">{fmt(sold_actual)}</div>
      <div class="unit">฿</div>
    </div>
    <div class="sum-box">
      <div class="lbl">Comm Sold</div>
      <div class="val">{fmt(sold_summary.get('Commission Price','0'))}</div>
      <div class="unit">฿</div>
    </div>
    <div class="sum-box">
      <div class="lbl">สมาชิกใหม่</div>
      <div class="val">{mem_total}</div>
      <div class="unit">คน</div>
    </div>
  </div>

  <!-- Goal Cards -->
  <div class="goal-row">
    <div class="goal-box">
      <div class="gtitle">เป้าหมาย PT Sold (2,000,000 + VAT 7%)</div>
      <div class="goal-nums">
        <div class="goal-pct" style="color:{sc};">{sold_pct:.1f}%</div>
        <div class="goal-actual">{fmt(sold_actual)} / {fmt(GOAL_PT_SOLD)} ฿</div>
      </div>
      <div class="pbar"><div class="pbar-fill" style="width:{min(sold_pct,100):.1f}%;background:{sc};"></div></div>
      <div class="goal-note">เป้า: {fmt(GOAL_PT_SOLD)} ฿ &nbsp;|&nbsp; {'✅ บรรลุเป้าแล้ว' if sold_pct >= 100 else f'คงเหลือ {fmt(GOAL_PT_SOLD - sold_actual)} ฿'}</div>
    </div>
    <div class="goal-box">
      <div class="gtitle">เป้าหมายสมาชิก (เป้ารายคน {GOAL_MEM_EACH} คน)</div>
      <div class="goal-nums">
        <div class="goal-pct" style="color:{mc};">{mem_pct:.1f}%</div>
        <div class="goal-actual">{mem_total} / {GOAL_MEMBER} คน</div>
      </div>
      <div class="pbar"><div class="pbar-fill" style="width:{min(mem_pct,100):.1f}%;background:{mc};"></div></div>
      <div class="goal-note">เป้ารวม: {GOAL_MEMBER} คน &nbsp;|&nbsp; {'✅ บรรลุเป้าแล้ว' if mem_pct >= 100 else f'คงเหลือ {GOAL_MEMBER - mem_total} คน'}</div>
    </div>
  </div>

  <!-- Charts: ★ height บน .chart-inner div → Chart.js ใช้ fillParent ★ -->
  <div class="chart-row">
    <div class="chart-box">
      <div class="st">PT Conduct — Sessions รายคน</div>
      <div class="chart-inner" style="height:{max(len(c_names)*24+20,160)}px;">
        <canvas id="cChart"></canvas>
      </div>
    </div>
    <div class="chart-box">
      <div class="st">PT Sold — ยอดขายรายคน</div>
      <div class="chart-inner" style="height:{max(len(s_names)*24+20,160)}px;">
        <canvas id="sChart"></canvas>
      </div>
    </div>
    <div class="chart-box">
      <div class="st">Membership รายคน (เป้า {GOAL_MEM_EACH})</div>
      <div class="chart-inner" style="height:{max(len(m_names)*30+20,160)}px;">
        <canvas id="mChart"></canvas>
      </div>
    </div>
  </div>

  <!-- Conduct + Membership -->
  <div class="table-row-3">
    <div class="tbox card-wrap">
      <div class="st">PT Conduct — Sessions รายบุคคล</div>
      <table>
        <thead><tr>
          <th>#</th><th>Trainer</th>
          <th class="tr">Fitstart</th><th class="tr">Trial</th>
          <th class="tr">Total Session</th>
        </tr></thead>
        <tbody>{conduct_rows_html()}</tbody>
      </table>
    </div>
    <div class="tbox card-wrap">
      <div class="st">Membership รายบุคคล (เป้า {GOAL_MEM_EACH})</div>
      <table>
        <thead><tr><th>#</th><th>Sold by</th><th>จำนวน / เป้า</th></tr></thead>
        <tbody>{mem_rows_html()}</tbody>
      </table>
    </div>
  </div>

  <!-- PT Sold -->
  <div class="tbox card-wrap">
    <div class="st">PT Sold — รายบุคคล</div>
    <table>
      <thead><tr>
        <th>#</th><th>Trainer</th>
        <th class="tr">Total Amount ฿</th>
        <th class="tr">Before VAT ฿</th>
      </tr></thead>
      <tbody>{sold_rows_html()}</tbody>
    </table>
  </div>

</div><!-- /a4 -->

<script>
const red  = ['#c0002a','#d42040','#e84060','#f06080','#f585a0','#f8a0b5','#fabdcc','#fcd5e0','#fee8ef','#fff0f5','#fff5f8','#fff8fa'];
const blue = ['#1565c0','#1976d2','#1e88e5','#2196f3','#42a5f5','#64b5f6','#90caf9','#bbdefb','#e3f2fd','#eef5ff','#f5f9ff','#fafcff'];
const goalLine = {GOAL_MEM_EACH};

const opts = () => ({{
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins:{{ legend:{{display:false}}, tooltip:{{
    backgroundColor:'rgba(0,0,0,.85)',
    titleColor:'#ffd',
    bodyColor:'#fff',
    callbacks:{{ label: ctx => '  ' + ctx.raw.toLocaleString() }}
  }} }},
  scales:{{
    x:{{
      ticks:{{ color:'#666', font:{{size:9}}, callback: v => v>=1000?Math.round(v/1000)+'k':v }},
      grid:{{ color:'#f0f0f0' }}
    }},
    y:{{
      ticks:{{ color:'#333', font:{{size:10}}, padding:4 }},
      grid:{{ display:false }}
    }}
  }}
}});

new Chart('cChart', {{ type:'bar', data:{{
  labels:{json.dumps(c_names, ensure_ascii=False)},
  datasets:[{{ data:{json.dumps(c_vals)}, backgroundColor:red, borderRadius:3 }}]
}}, options:opts() }});

new Chart('sChart', {{ type:'bar', data:{{
  labels:{json.dumps(s_names, ensure_ascii=False)},
  datasets:[{{ data:{json.dumps(s_vals)}, backgroundColor:red, borderRadius:3 }}]
}}, options:opts() }});

new Chart('mChart', {{ type:'bar', data:{{
  labels:{json.dumps(m_names, ensure_ascii=False)},
  datasets:[{{
    data:{json.dumps(m_vals)},
    backgroundColor: {json.dumps(m_vals)}.map(v => v >= goalLine ? '#2e7d32' : v >= goalLine-2 ? '#f57c00' : '#c0002a'),
    borderRadius:3
  }}]
}}, options:opts() }});
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("สร้าง index.html แล้ว")
