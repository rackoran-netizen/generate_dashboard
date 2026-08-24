import json

with open("nmall_data.json", encoding="utf-8") as f:
    src = json.load(f)

months           = src["months"]
monthly_total    = src["monthly_total"]
monthly_by_type  = src["monthly_by_type"]
pt_trainer_month = src["pt_trainer_month"]

full_months = months[:-1]          # ตัดเดือนล่าสุดออกเพราะข้อมูลยังไม่ครบเดือน
last12      = full_months[-12:]

def next_month_labels(last_ym, n=3):
    y, m = (int(x) for x in last_ym.split("-"))
    out = []
    for _ in range(n):
        m += 1
        if m > 12:
            m = 1
            y += 1
        out.append(f"{y:04d}-{m:02d}")
    return out

# เดือนพยากรณ์ = 3 เดือนถัดจากเดือนปัจจุบัน (ที่ยังไม่ครบ) ไม่ใช่ถัดจากเดือนล่าสุดที่ใช้ fit เทรนด์
# เช่นถ้าข้อมูลครบถึง ก.ค. 69 และเดือนปัจจุบัน (ยังไม่ครบ) คือ ส.ค. 69 -> พยากรณ์ ก.ย./ต.ค./พ.ย. 69
fc_months = next_month_labels(months[-1], 3)
HORIZON_START = len(months) - len(full_months) + 1   # จำนวนเดือนจาก last12[-1] ถึงเดือนพยากรณ์แรก

def linreg(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if denom == 0:
        return 0.0, (sy / n if n else 0.0)
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept

def series_and_forecast(vals_by_month, month_list, horizon=3):
    ys = [vals_by_month.get(m, 0.0) for m in month_list]
    xs = list(range(len(ys)))
    slope, intercept = linreg(xs, ys)
    preds = [max(0.0, slope * (len(ys) - 1 + h) + intercept)
             for h in range(HORIZON_START, HORIZON_START + horizon)]
    return ys, slope, intercept, preds

overall_full_hist = [monthly_total.get(m, 0.0) for m in full_months]
_, slope_o, _, overall_fc = series_and_forecast(monthly_total, last12, 3)

TYPES_ORDER = ["PT Revenue", "Membership - Direct Debit", "PIA Collections", "Other Income"]
mix_last12 = {}
for t in TYPES_ORDER:
    series = {m: monthly_by_type.get(m, {}).get(t, 0.0) for m in last12}
    ys, slope, intercept, preds = series_and_forecast(series, last12, 3)
    mix_last12[t] = {"hist": ys, "slope": slope, "fc": preds, "total": sum(ys)}

trainer_rows = []
for name, series in pt_trainer_month.items():
    active_cnt = sum(1 for m in last12 if series.get(m, 0) > 0)
    if active_cnt < 6:
        continue
    ys, slope, intercept, preds = series_and_forecast(series, last12, 3)
    mean = sum(ys) / len(ys) if ys else 0
    slope_pct = (slope / mean * 100) if mean else 0
    status = "growing" if slope_pct >= 3 else ("declining" if slope_pct <= -3 else "flat")
    trainer_rows.append({
        "name": name, "hist12": ys, "total12": sum(ys), "active": active_cnt,
        "slope": slope, "slope_pct": slope_pct, "fc": preds, "status": status,
    })
trainer_rows.sort(key=lambda r: -r["total12"])

report_data = {
    "full_months": full_months,
    "last12": last12,
    "fc_months": fc_months,
    "overall": {
        "hist_full": overall_full_hist, "hist_months": full_months,
        "slope": slope_o, "fc": overall_fc,
        "aug_partial": monthly_total.get(months[-1], 0.0),
    },
    "mix_last12": mix_last12,
    "trainers": trainer_rows,
}

DATA_JSON = json.dumps(report_data, ensure_ascii=False, separators=(",", ":"))

HTML = r'''<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>พยากรณ์ยอดขาย RRA — nmall</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Kanit:wght@600;700&family=Sarabun:wght@400;500;600;700&display=swap">
<style>
:root{
  color-scheme: light;
  --page:#f3f0e6; --surface:#fffdf8; --surface-2:#faf6ec;
  --ink:#18140f; --ink-2:#5b5346; --muted:#948c78;
  --border:rgba(24,20,15,0.11); --border-strong:rgba(24,20,15,0.18);
  --accent:#a3721f; --accent-ink:#6b4c17; --accent-soft:rgba(163,114,31,0.13);
  --good:#0ca30c; --good-soft:rgba(12,163,12,0.12);
  --critical:#c8372f; --critical-soft:rgba(200,55,47,0.11);
  --warning:#9c6b0a; --warning-soft:rgba(250,178,25,0.20);
  --grid:#e4dfd0;
  --shadow: 0 1px 2px rgba(24,20,15,.06), 0 8px 24px -12px rgba(24,20,15,.18);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --page:#14120d; --surface:#1d1a13; --surface-2:#231f17;
    --ink:#f5f0e3; --ink-2:#c7bfa9; --muted:#8c8571;
    --border:rgba(255,255,255,0.10); --border-strong:rgba(255,255,255,0.18);
    --accent:#dba847; --accent-ink:#eecb84; --accent-soft:rgba(219,168,71,0.16);
    --good:#2fbf3e; --good-soft:rgba(47,191,62,0.16);
    --critical:#e8695f; --critical-soft:rgba(232,105,95,0.16);
    --warning:#f0b429; --warning-soft:rgba(240,180,41,0.18);
    --grid:#2e2a20;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 28px -12px rgba(0,0,0,.5);
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --page:#14120d; --surface:#1d1a13; --surface-2:#231f17;
  --ink:#f5f0e3; --ink-2:#c7bfa9; --muted:#8c8571;
  --border:rgba(255,255,255,0.10); --border-strong:rgba(255,255,255,0.18);
  --accent:#dba847; --accent-ink:#eecb84; --accent-soft:rgba(219,168,71,0.16);
  --good:#2fbf3e; --good-soft:rgba(47,191,62,0.16);
  --critical:#e8695f; --critical-soft:rgba(232,105,95,0.16);
  --warning:#f0b429; --warning-soft:rgba(240,180,41,0.18);
  --grid:#2e2a20;
  --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 28px -12px rgba(0,0,0,.5);
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{background:var(--page);color:var(--ink);font-family:"Sarabun","Noto Sans Thai",system-ui,sans-serif;font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased;}
.wrap{max-width:1000px;margin:0 auto;padding:28px 20px 80px;}
.hero{margin-bottom:28px;}
.eyebrow{font-family:"Kanit",sans-serif;font-weight:600;font-size:12.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent-ink);margin:0 0 8px;}
h1{font-family:"Kanit",sans-serif;font-weight:700;font-size:clamp(26px,4vw,36px);line-height:1.15;margin:0 0 8px;text-wrap:balance;letter-spacing:-.01em;}
.hero p{margin:0;color:var(--ink-2);font-size:14.5px;max-width:60ch;}
.hero .meta{margin-top:10px;font-size:13px;color:var(--muted);}
.kpi-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:22px;}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:16px 18px;box-shadow:var(--shadow);}
.kpi .lbl{font-size:12px;color:var(--muted);margin-bottom:6px;}
.kpi .val{font-family:"Kanit",sans-serif;font-weight:700;font-size:24px;font-variant-numeric:tabular-nums;letter-spacing:-.01em;}
.kpi .sub{font-size:12.5px;color:var(--ink-2);margin-top:4px;}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;padding:2px 9px 2px 7px;border-radius:999px;line-height:1.7;}
.chip.good{background:var(--good-soft);color:var(--good);}
.chip.declining{background:var(--critical-soft);color:var(--critical);}
.chip.flat{background:var(--surface-2);color:var(--ink-2);border:1px solid var(--border);}
.chip.growing{background:var(--good-soft);color:var(--good);}
.chip::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;}
section{margin-bottom:26px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:20px 22px;box-shadow:var(--shadow);}
h2{font-family:"Kanit",sans-serif;font-weight:600;font-size:18px;margin:0 0 4px;letter-spacing:-.005em;}
.section-note{font-size:13px;color:var(--ink-2);margin:0 0 16px;max-width:70ch;}
.chart-wrap{overflow-x:auto;}
svg.linechart{display:block;min-width:640px;width:100%;height:auto;}
.axis-label{font-size:10.5px;fill:var(--muted);font-family:"Sarabun",sans-serif;}
.legend{display:flex;gap:18px;flex-wrap:wrap;margin-top:10px;font-size:12.5px;color:var(--ink-2);}
.legend span{display:inline-flex;align-items:center;gap:6px;}
.legend i{width:14px;height:2px;border-radius:2px;display:inline-block;}
.mix-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;}
.mix-card{background:var(--surface-2);border:1px solid var(--border);border-radius:12px;padding:14px 16px;}
.mix-card .t{font-size:12.5px;color:var(--ink-2);margin-bottom:2px;}
.mix-card .v{font-family:"Kanit",sans-serif;font-weight:600;font-size:19px;font-variant-numeric:tabular-nums;}
.mix-card .d{font-size:12px;margin-top:5px;}
.mix-card svg{margin-top:8px;display:block;width:100%;height:28px;}
table{width:100%;border-collapse:collapse;font-size:13.5px;}
thead th{text-align:left;font-weight:600;color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;padding:0 10px 10px;border-bottom:1px solid var(--border-strong);}
thead th.num,tbody td.num{text-align:right;}
tbody td{padding:9px 10px;border-bottom:1px solid var(--border);vertical-align:middle;font-variant-numeric:tabular-nums;}
tbody tr:last-child td{border-bottom:none;}
tbody tr:hover td{background:var(--surface-2);}
td.name{font-weight:600;font-variant-numeric:normal;}
td.spark svg{display:block;}
.tbl-wrap{overflow-x:auto;}
.issues{display:flex;flex-direction:column;gap:10px;}
.issue{display:flex;gap:12px;padding:13px 15px;border-radius:12px;border:1px solid var(--border);background:var(--surface-2);}
.issue .tag{flex:none;font-family:"Kanit",sans-serif;font-weight:600;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;padding:3px 8px;border-radius:6px;height:fit-content;white-space:nowrap;}
.issue .tag.high{background:var(--critical-soft);color:var(--critical);}
.issue .tag.med{background:var(--warning-soft);color:var(--warning);}
.issue .tag.low{background:var(--accent-soft);color:var(--accent-ink);}
.issue .body{font-size:13.5px;color:var(--ink-2);}
.issue .body .h{color:var(--ink);font-weight:600;display:block;margin-bottom:2px;font-size:14px;}
footer{margin-top:8px;padding-top:16px;border-top:1px solid var(--border);font-size:12px;color:var(--muted);}
footer p{margin:0 0 6px;max-width:75ch;}
@media (max-width:640px){.kpi-row{grid-template-columns:1fr;}.card{padding:16px;}}
</style>
</head>
<body>
<div class="wrap">

  <div class="hero">
    <p class="eyebrow">Jetts Robinson Ratchaphruek &middot; nmall sales ledger</p>
    <h1>พยากรณ์ยอดขาย 3 เดือนข้างหน้า</h1>
    <p>วิเคราะห์จากข้อมูลธุรกรรมจริงในชีต <b>nmall</b> แยกภาพรวมทั้งสาขา, รายประเภทรายได้ และรายเทรนเนอร์ พร้อมจุดข้อมูลที่ควรแก้ไข</p>
    <p class="meta">อัพเดตข้อมูลถึง ''' + src.get("data_through", "-") + r''' &nbsp;&middot;&nbsp; คำนวณแนวโน้มจาก 12 เดือนล่าสุดที่ข้อมูลครบ</p>
  </div>

  <div class="kpi-row" id="kpiRow"></div>

  <section class="card">
    <h2>ภาพรวมยอดขายทั้งหมด</h2>
    <p class="section-note">รวมทุกประเภทรายได้ (PT Revenue, Membership, PIA Collections, Other Income) รายเดือนตั้งแต่เปิดข้อมูล เส้นทึบคือยอดจริง เส้นประคือค่าพยากรณ์จากแนวโน้ม 12 เดือนล่าสุด</p>
    <div class="chart-wrap"><svg class="linechart" id="overallChart" viewBox="0 0 960 300"></svg></div>
    <div class="legend">
      <span><i style="background:var(--accent)"></i>ยอดขายจริงรายเดือน</span>
      <span><i style="background:var(--accent);opacity:.55;border-top:2px dashed var(--accent)"></i>พยากรณ์ 3 เดือนถัดไป</span>
    </div>
  </section>

  <section class="card">
    <h2>แยกตามประเภทรายได้ (12 เดือนล่าสุด)</h2>
    <p class="section-note">รายได้หลักยังมาจากค่าสมาชิกและ PT แต่มีสองเส้นที่กำลังหดตัวชัดเจน — ดูรายละเอียดในหัวข้อ "จุดที่ต้องแก้ไข" ด้านล่าง</p>
    <div class="mix-grid" id="mixGrid"></div>
  </section>

  <section class="card">
    <h2>พยากรณ์รายเทรนเนอร์ (PT Revenue)</h2>
    <p class="section-note">เฉพาะเทรนเนอร์ที่มียอดขายอย่างน้อย 6 ใน 12 เดือนล่าสุด เรียงตามยอดขาย 12 เดือน &middot; แนวโน้ม/เดือน คำนวณจากเส้นถดถอยเชิงเส้นของ 12 เดือนล่าสุด</p>
    <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>เทรนเนอร์</th><th>แนวโน้ม</th><th class="num">ยอด 12 เดือน (฿)</th>
        <th class="num">แนวโน้ม/เดือน</th><th>กราฟ 12 เดือน</th><th class="num">พยากรณ์ 3 เดือนถัดไป รวม (฿)</th>
      </tr></thead>
      <tbody id="trainerBody"></tbody>
    </table>
    </div>
  </section>

  <section class="card">
    <h2>จุดที่ต้องแก้ไข</h2>
    <p class="section-note">ปัญหาคุณภาพข้อมูลและสัญญาณธุรกิจที่พบระหว่างวิเคราะห์ เรียงตามความสำคัญ</p>
    <div class="issues" id="issuesList"></div>
  </section>

  <footer>
    <p><b>วิธีคำนวณ:</b> พยากรณ์ใช้การถดถอยเชิงเส้น (least-squares linear regression) บนยอดขายรายเดือนของ 12 เดือนล่าสุดที่ข้อมูลครบ แล้วต่อแนวโน้มไปข้างหน้า 3 เดือน เป็นโมเดลอย่างง่าย ไม่รวมผลตามฤดูกาล โปรโมชั่น หรือจำนวนวันทำการต่อเดือน — เหมาะสำหรับดูทิศทาง ไม่ใช่ตัวเลขที่แม่นยำระดับบาท</p>
    <p>ชื่อเทรนเนอร์ "Lakza" ถูกรวมเข้ากับ "Lekza" ในกราฟและตารางนี้ (ดูเหตุผลในจุดที่ต้องแก้ไข) สร้างจาก generate_nmall_forecast.py</p>
  </footer>

</div>

<script id="report-data" type="application/json">__DATA_JSON__</script>
<script>
const DATA = JSON.parse(document.getElementById('report-data').textContent);
const THB = v => '฿' + Math.round(v).toLocaleString('th-TH');
const THB0 = v => Math.round(v).toLocaleString('th-TH');
const monthTH = ['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'];
function fmtM(ym){ const [y,m] = ym.split('-'); return monthTH[parseInt(m,10)-1] + ' ' + (parseInt(y,10)+543-2500); }

(function(){
  const hist = DATA.overall.hist_full;
  const lastActual = hist[hist.length-1];
  const fcAvg = DATA.overall.fc.reduce((a,b)=>a+b,0)/DATA.overall.fc.length;
  const mean12 = hist.slice(-12).reduce((a,b)=>a+b,0)/12;
  const slopePct = DATA.overall.slope/mean12*100;
  const trendWord = slopePct <= -1 ? 'ลดลงเล็กน้อย' : (slopePct >= 1 ? 'เพิ่มขึ้นเล็กน้อย' : 'ค่อนข้างทรงตัว');
  const trendClass = slopePct <= -1 ? 'declining' : (slopePct >= 1 ? 'growing' : 'flat');
  const fcLabel = DATA.fc_months.map(fmtM).join(' / ');
  const kpis = [
    {lbl:`ยอดขายจริง ${fmtM(DATA.overall.hist_months[DATA.overall.hist_months.length-1])} (เดือนล่าสุดที่ครบ)`, val: THB(lastActual), sub: `เดือนก่อนหน้า: ${THB(hist[hist.length-2])}`},
    {lbl:`พยากรณ์เฉลี่ย ${fcLabel}`, val: THB(fcAvg), sub: `${THB(DATA.overall.fc[0])} / ${THB(DATA.overall.fc[1])} / ${THB(DATA.overall.fc[2])}`},
    {lbl:'แนวโน้ม 12 เดือนล่าสุด', val: (slopePct>=0?'+':'') + slopePct.toFixed(1) + '%/เดือน', sub:null, chip:trendWord, chipClass:trendClass},
  ];
  document.getElementById('kpiRow').innerHTML = kpis.map(k => `
    <div class="kpi">
      <div class="lbl">${k.lbl}</div>
      <div class="val">${k.val}</div>
      ${k.sub ? `<div class="sub">${k.sub}</div>` : `<div class="sub"><span class="chip ${k.chipClass}">${k.chip}</span></div>`}
    </div>`).join('');
})();

(function(){
  const svg = document.getElementById('overallChart');
  const W=960,H=300,padL=54,padR=16,padT=16,padB=34;
  const months = DATA.overall.hist_months.concat(DATA.fc_months);
  const actual = DATA.overall.hist_full;
  const fc = DATA.overall.fc;
  const allVals = actual.concat(fc);
  const maxV = Math.max(...allVals)*1.08, minV = 0;
  const n = months.length;
  const x = i => padL + (W-padL-padR) * (i/(n-1));
  const y = v => H-padB - (H-padT-padB) * ((v-minV)/(maxV-minV));
  let g = '';
  const steps=4;
  for(let s=0; s<=steps; s++){
    const v = maxV/steps*s;
    const yy = y(v);
    g += `<line x1="${padL}" y1="${yy}" x2="${W-padR}" y2="${yy}" stroke="var(--grid)" stroke-width="1"/>`;
    g += `<text class="axis-label" x="${padL-8}" y="${yy+4}" text-anchor="end">${(v/1e6).toFixed(1)}M</text>`;
  }
  months.forEach((m,i)=>{
    if(i%3===0 || i===n-1){
      g += `<text class="axis-label" x="${x(i)}" y="${H-padB+16}" text-anchor="middle">${fmtM(m)}</text>`;
    }
  });
  const actualPts = actual.map((v,i)=>[x(i),y(v)]);
  const dActual = actualPts.map((p,i)=> (i===0?'M':'L')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ');
  g += `<path d="${dActual}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
  const fcStartIdx = actual.length-1;
  const fcPts = [[x(fcStartIdx), y(actual[actual.length-1])]].concat(fc.map((v,i)=>[x(fcStartIdx+1+i), y(v)]));
  const dFc = fcPts.map((p,i)=> (i===0?'M':'L')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ');
  g += `<path d="${dFc}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-dasharray="6 5" stroke-linejoin="round" stroke-linecap="round" opacity=".75"/>`;
  const lastP = actualPts[actualPts.length-1];
  g += `<circle cx="${lastP[0]}" cy="${lastP[1]}" r="4" fill="var(--surface)" stroke="var(--accent)" stroke-width="2.5"/>`;
  fcPts.slice(1).forEach(p=>{
    g += `<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="var(--surface)" stroke="var(--accent)" stroke-width="2" opacity=".85"/>`;
  });
  svg.innerHTML = g;
})();

(function(){
  const labels = {
    'PT Revenue':'PT Revenue',
    'Membership - Direct Debit':'Membership (Direct Debit)',
    'PIA Collections':'PIA Collections',
    'Other Income':'Other Income'
  };
  let html = '';
  Object.keys(labels).forEach(key=>{
    const d = DATA.mix_last12[key];
    if(!d) return;
    const hist = d.hist;
    const mean = d.total/12;
    const slopePct = mean ? d.slope/mean*100 : 0;
    const cls = slopePct<=-3?'declining':(slopePct>=3?'growing':'flat');
    const arrow = slopePct<=-3?'▼':(slopePct>=3?'▲':'▪');
    const maxV = Math.max(...hist)*1.15 || 1;
    const wStep = 100/(hist.length-1);
    const pts = hist.map((v,i)=>[ (i*wStep), 28-(v/maxV*24)-2 ]);
    const dPath = pts.map((p,i)=>(i===0?'M':'L')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ');
    html += `<div class="mix-card">
      <div class="t">${labels[key]}</div>
      <div class="v">${THB(d.total)}</div>
      <div class="d"><span class="chip ${cls}">${arrow} ${(slopePct>=0?'+':'')+slopePct.toFixed(1)}%/เดือน</span></div>
      <svg viewBox="0 0 100 28" preserveAspectRatio="none"><path d="${dPath}" fill="none" stroke="var(--accent)" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>
    </div>`;
  });
  document.getElementById('mixGrid').innerHTML = html;
})();

(function(){
  const statusLabel = {growing:'เติบโต', declining:'ลดลง', flat:'ทรงตัว'};
  let html = '';
  DATA.trainers.forEach(t=>{
    const maxV = Math.max(...t.hist12)*1.15 || 1;
    const wStep = 100/(t.hist12.length-1);
    const pts = t.hist12.map((v,i)=>[ (i*wStep), 24-(v/maxV*20)-2 ]);
    const dPath = pts.map((p,i)=>(i===0?'M':'L')+p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ');
    const fcSum = t.fc.reduce((a,b)=>a+b,0);
    const color = t.status==='declining' ? 'var(--critical)' : (t.status==='growing' ? 'var(--good)' : 'var(--muted)');
    html += `<tr>
      <td class="name">${t.name}</td>
      <td><span class="chip ${t.status}">${statusLabel[t.status]}</span></td>
      <td class="num">${THB0(t.total12)}</td>
      <td class="num" style="color:${color}">${(t.slope_pct>=0?'+':'')+t.slope_pct.toFixed(1)}%</td>
      <td class="spark"><svg viewBox="0 0 100 24" width="90" height="22" preserveAspectRatio="none"><path d="${dPath}" fill="none" stroke="${color}" stroke-width="2.2" vector-effect="non-scaling-stroke"/></svg></td>
      <td class="num">${THB0(fcSum)}</td>
    </tr>`;
  });
  document.getElementById('trainerBody').innerHTML = html;
})();

(function(){
  const issues = [
    {tag:'high', h:'ยอดสมาชิกใหม่ (Membership – Direct Debit) กำลังลดลงต่อเนื่อง', b:'เป็นสายรายได้ใหญ่ที่สุดใน 12 เดือนล่าสุด แต่แนวโน้มติดลบ และ PIA Collections ลดแรงกว่ามาก — ควรตรวจสอบว่าเป็นผลจากแคมเปญ/ราคาที่เปลี่ยน หรือทีมขายสมาชิกที่มีปัญหา ก่อนที่จะกระทบยอดรวมทั้งสาขาในไตรมาสหน้า'},
    {tag:'high', h:'ยอดรวมทั้งสาขาทรงตัว/ทรุดตัวเล็กน้อย แม้ PT Revenue ยังโต', b:'ยอดรวม 12 เดือนล่าสุดแทบไม่โต เพราะ PT Revenue ที่โตไม่พอชดเชยการลดลงของ Membership และ PIA Collections รวมกัน — ถ้าปล่อยไว้ ยอดรวมมีแนวโน้มลดลงต่อในไตรมาสหน้า'},
    {tag:'high', h:'เทรนเนอร์หลักบางคนกำลังลดลงต่อเนื่อง', b:'ดูคอลัมน์ "แนวโน้ม" ในตารางรายเทรนเนอร์ด้านบน — คนที่มีป้าย "ลดลง" ต่อเนื่องหลายเดือนควรได้รับการตรวจสอบตารางสอน จำนวนลูกค้าเก่าที่หมดสัญญา หรือปัญหาส่วนตัว ก่อนยอดขายไตรมาสหน้าหลุดจากกลุ่มนำ'},
    {tag:'med', h:'ชื่อเทรนเนอร์ "Lakza" กับ "Lekza" น่าจะเป็นคนเดียวกัน', b:'ช่วงเวลาที่มียอดขายต่อเนื่องกันพอดี (มีคาบเกี่ยวกันสั้น ๆ) — รายงานนี้รวมสองชื่อเป็นคนเดียวแล้ว แต่ควรแก้ไขการสะกดชื่อในชีตต้นทางให้ตรงกันเพื่อไม่ให้ระบบอื่นนับแยกกัน'},
    {tag:'med', h:'ชื่อ "Deaw" กับ "Daew" สะกดใกล้เคียงกันมาก แต่ช่วงเวลาไม่ต่อเนื่อง', b:'"Deaw" หายไปนานหลายเดือนก่อน "Daew" จะเริ่มมียอดขาย — อาจเป็นคนเดิมที่กลับมาทำงาน (สะกดผิด) หรือเป็นเทรนเนอร์คนละคนที่บังเอิญชื่อคล้ายกัน ควรตรวจสอบกับทีมก่อนรวมข้อมูล เพราะรายงานนี้ยังแยกสองชื่อไว้ต่างหาก'},
    {tag:'med', h:'พบ "tiger" ตัวพิมพ์เล็กปนกับ "Tiger"', b:'มีธุรกรรมที่บันทึกชื่อผู้ขายเป็นตัวพิมพ์เล็กทั้งหมด ต่างจาก "Tiger" ที่ใช้ตลอด — เป็นความผิดพลาดจากการพิมพ์ ควรแก้ไขในชีตต้นทางและตรวจสอบทั้งคอลัมน์ Cashier หาความคลาดเคลื่อนแบบเดียวกันที่ยังไม่ถูกจับได้'},
    {tag:'med', h:'ยอดขายเดือน ม.ค. 2568 ต่ำผิดปกติเมื่อเทียบกับเดือนข้างเคียง', b:'จำนวนธุรกรรมเดือนนั้นน้อยกว่าเดือนก่อนและหลังเกือบครึ่ง — ลักษณะนี้เหมือนข้อมูลตกหล่นมากกว่ายอดขายตกจริง ควรตรวจสอบกับต้นทางระบบขายว่ามีการบันทึกข้อมูลครบทุกวันในเดือนนั้นหรือไม่ ก่อนใช้เดือนนี้อ้างอิงในการวางแผนฤดูกาล'},
    {tag:'low', h:'คอลัมน์ Branch ว่างเปล่าตั้งแต่ ก.พ. 2567 เป็นต้นมา', b:'ช่วงแรกมีค่า "RRA" ครบทุกแถว แต่หลังจากนั้นว่างเปล่าทั้งหมด — ไม่กระทบรายงานนี้เพราะข้อมูลทั้งหมดเป็นสาขาเดียว แต่ถ้าจะรวมข้อมูลหลายสาขาในอนาคต ต้องเติมคอลัมน์นี้ให้ครบก่อน'},
    {tag:'low', h:'คอลัมน์ "Membership Type" ซ้ำกัน 2 คอลัมน์ในหัวตาราง', b:'ต้นฉบับมีคอลัมน์ชื่อ "Membership Type" ปรากฏสองครั้งท้ายตาราง และมีคอลัมน์ว่างอีกหลายคอลัมน์ต่อท้าย (ไม่มีหัวคอลัมน์) — เป็นร่องรอยจากการแก้ไขชีตในอดีต ควรทำความสะอาดโครงสร้างคอลัมน์เพื่อลดความสับสนเวลาทำรายงานอัตโนมัติ'},
  ];
  document.getElementById('issuesList').innerHTML = issues.map(i => `
    <div class="issue">
      <span class="tag ${i.tag}">${i.tag==='high'?'ควรดูก่อน':i.tag==='med'?'ควรแก้ไข':'ไม่เร่งด่วน'}</span>
      <div class="body"><span class="h">${i.h}</span>${i.b}</div>
    </div>`).join('');
})();
</script>
</body>
</html>
'''

HTML = HTML.replace("__DATA_JSON__", DATA_JSON)

with open("nmall_forecast.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("สร้าง nmall_forecast.html แล้ว")
