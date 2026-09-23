import json

with open("nmall_data.json", encoding="utf-8") as f:
    src = json.load(f)

months              = src["months"]
pt_trainer_month    = src["pt_trainer_month"]
pt_month_newrenew   = src["pt_month_newrenew"]
pt_package_month    = src["pt_package_month"]
nm_month_newrenew   = src["nm_month_newrenew"]
nm_package_month    = src["nm_package_month"]
nm_count_month      = src["nm_month_total"]

full_months = months[:-1]
last12 = full_months[-12:]

# ระดับเทรนเนอร์ — มาจากรายชื่อที่คลับให้มา ไม่ได้อยู่ในชีต
TRAINER_TIER = {
    'Lekza': 'senior', 'Deaw': 'senior', 'Bos': 'elite', 'Ice': 'gx', 'Nine': 'junior',
    'Miw': 'elite', 'Baifern': 'junior', 'Golf': 'elite', 'Tiger': 'junior', 'Zico': 'junior',
    'Man': 'junior', 'Peet': 'elite', 'Ae': 'elite', 'Paul': 'senior', 'Lion': 'elite',
    'Ford': 'junior', 'Put': 'junior', 'Nill': 'junior', 'Yean': 'junior', 'Poom': 'junior',
    'Benz': 'junior', 'Stamp': 'junior',
}
TIER_LABEL = {'elite': 'Elite', 'senior': 'Senior', 'junior': 'Junior', 'gx': 'GX', 'unknown': 'ไม่ระบุ'}
TIER_ORDER = ['elite', 'senior', 'junior', 'gx', 'unknown']

def sum_last12(d):
    return {k: sum(v.get(m, 0.0) for m in last12) for k, v in d.items()}

# PT New/Renew รายเดือน (12 เดือนล่าสุด)
pt_nr_monthly = {m: pt_month_newrenew.get(m, {}) for m in last12}

# PT ตามแพ็กเกจ รวม 12 เดือนล่าสุด
pt_package_last12 = sum_last12(pt_package_month)
PACKAGE_ORDER = ["1 ครั้ง (Walk-in/VIP)", "3-12 ครั้ง", "20-24 ครั้ง", "30-36 ครั้ง", "50-60 ครั้ง", "100 ครั้ง", "อื่นๆ/ราคาพิเศษ"]
pt_package_last12 = {k: pt_package_last12.get(k, 0.0) for k in PACKAGE_ORDER if pt_package_last12.get(k, 0.0) > 0}

# PT ตามระดับเทรนเนอร์ รวม 12 เดือนล่าสุด (จาก pt_trainer_month + ตารางระดับ)
pt_tier_last12 = {t: 0.0 for t in TIER_ORDER}
for name, series in pt_trainer_month.items():
    tier = TRAINER_TIER.get(name, 'unknown')
    pt_tier_last12[tier] += sum(series.get(m, 0.0) for m in last12)
pt_tier_last12 = {TIER_LABEL[t]: v for t, v in pt_tier_last12.items() if v > 0}

# NM New/Renew รายเดือน (12 เดือนล่าสุด)
nm_nr_monthly = {m: nm_month_newrenew.get(m, {}) for m in last12}

# NM ตามแพ็กเกจ รวม 12 เดือนล่าสุด
nm_package_last12 = sum_last12(nm_package_month)
NM_PACKAGE_ORDER = ["Monthly", "Yearly", "6 Months", "3 Months", "ไม่ระบุ"]
nm_package_last12 = {k: nm_package_last12.get(k, 0.0) for k in NM_PACKAGE_ORDER if nm_package_last12.get(k, 0.0) > 0}

# จำนวนสมาชิกใหม่ต่อเดือน (24 เดือนล่าสุด)
nm_count_24 = full_months[-24:]
nm_count_series = {m: nm_count_month.get(m, 0) for m in nm_count_24}

report_data = {
    "last12": last12,
    "nm_count_months": nm_count_24,
    "pt_nr_monthly": pt_nr_monthly,
    "pt_package_last12": pt_package_last12,
    "pt_tier_last12": pt_tier_last12,
    "nm_nr_monthly": nm_nr_monthly,
    "nm_package_last12": nm_package_last12,
    "nm_count_series": nm_count_series,
}

DATA_JSON = json.dumps(report_data, ensure_ascii=False, separators=(",", ":"))

HTML = r'''<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>สรุปยอดขาย PT & สมาชิกใหม่</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Kanit:wght@600;700&family=Sarabun:wght@400;500;600;700&display=swap">
<style>
:root{
  color-scheme: light;
  --page:#f3f0e6; --surface:#fffdf8; --surface-2:#faf6ec;
  --ink:#18140f; --ink-2:#5b5346; --muted:#948c78;
  --border:rgba(24,20,15,0.11); --border-strong:rgba(24,20,15,0.18);
  --accent:#a3721f; --accent-ink:#6b4c17;
  --grid:#e4dfd0;
  --shadow: 0 1px 2px rgba(24,20,15,.06), 0 8px 24px -12px rgba(24,20,15,.18);
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4; --s6:#008300; --s7:#4a3aa7; --s8:#e34948;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --page:#14120d; --surface:#1d1a13; --surface-2:#231f17;
    --ink:#f5f0e3; --ink-2:#c7bfa9; --muted:#8c8571;
    --border:rgba(255,255,255,0.10); --border-strong:rgba(255,255,255,0.18);
    --accent:#dba847; --accent-ink:#eecb84;
    --grid:#2e2a20;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 28px -12px rgba(0,0,0,.5);
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --page:#14120d; --surface:#1d1a13; --surface-2:#231f17;
  --ink:#f5f0e3; --ink-2:#c7bfa9; --muted:#8c8571;
  --border:rgba(255,255,255,0.10); --border-strong:rgba(255,255,255,0.18);
  --accent:#dba847; --accent-ink:#eecb84;
  --grid:#2e2a20;
  --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 28px -12px rgba(0,0,0,.5);
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{background:var(--page);color:var(--ink);font-family:"Sarabun","Noto Sans Thai",system-ui,sans-serif;font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased;}
.wrap{max-width:1040px;margin:0 auto;padding:28px 20px 80px;}
.hero{margin-bottom:26px;}
.eyebrow{font-family:"Kanit",sans-serif;font-weight:600;font-size:12.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent-ink);margin:0 0 8px;}
h1{font-family:"Kanit",sans-serif;font-weight:700;font-size:clamp(24px,4vw,32px);line-height:1.15;margin:0 0 8px;text-wrap:balance;letter-spacing:-.01em;}
.hero p{margin:0;color:var(--ink-2);font-size:14.5px;max-width:68ch;}
.hero .meta{margin-top:10px;font-size:13px;color:var(--muted);}
section{margin-bottom:24px;}
.section-head{margin-bottom:12px;}
.section-head h2{font-family:"Kanit",sans-serif;font-weight:700;font-size:19px;margin:0 0 4px;color:var(--accent-ink);}
.section-head p{margin:0;font-size:13px;color:var(--ink-2);max-width:70ch;}
.chart-row{display:grid;grid-template-columns:1.3fr 1fr;gap:14px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:18px 20px;box-shadow:var(--shadow);}
.card h3{font-family:"Kanit",sans-serif;font-weight:600;font-size:14.5px;margin:0 0 3px;}
.card .note{font-size:12px;color:var(--muted);margin:0 0 12px;}
.chart-wrap{overflow-x:auto;}
svg.chart{display:block;min-width:480px;width:100%;height:auto;}
.axis-label{font-size:10px;fill:var(--muted);font-family:"Sarabun",sans-serif;}
.bar-label{font-size:10.5px;fill:var(--ink-2);font-family:"Sarabun",sans-serif;}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:10px;font-size:12px;color:var(--ink-2);}
.legend span{display:inline-flex;align-items:center;gap:6px;}
.legend i{width:11px;height:11px;border-radius:3px;display:inline-block;}
@media (max-width:760px){.chart-row{grid-template-columns:1fr;}}
footer{margin-top:8px;padding-top:16px;border-top:1px solid var(--border);font-size:12px;color:var(--muted);}
footer p{margin:0 0 6px;max-width:80ch;}
</style>
</head>
<body>
<div class="wrap">

  <div class="hero">
    <p class="eyebrow">Jetts Robinson Ratchaphruek &middot; สำหรับที่ประชุม</p>
    <h1>สรุปยอดขาย PT &amp; สมาชิกใหม่ แยกหมวด</h1>
    <p>ข้อมูลจากชีต <b>nmall</b> ช่วง 12 เดือนล่าสุด แยกยอด PT ตาม New/Renew, แพ็กเกจ และระดับเทรนเนอร์ &middot; แยกยอดสมาชิกใหม่ตาม New/Renew และแพ็กเกจ &middot; จำนวนสมาชิกใหม่ต่อเดือน</p>
    <p class="meta">ข้อมูลถึง ''' + src.get("data_through", "-") + r'''</p>
  </div>

  <section>
    <div class="section-head">
      <h2>1. ยอดขาย PT</h2>
      <p>แยกตาม New/Renew รายเดือน, แพ็กเกจ (จับคู่ราคากับชีต TPice) และระดับเทรนเนอร์</p>
    </div>
    <div class="chart-row" style="margin-bottom:14px;">
      <div class="card">
        <h3>PT Revenue: New vs Renew รายเดือน</h3>
        <p class="note">12 เดือนล่าสุด &middot; หน่วย บาท</p>
        <div class="chart-wrap"><svg class="chart" id="ptNrChart" viewBox="0 0 700 280"></svg></div>
        <div class="legend"><span><i style="background:var(--s1)"></i>New</span><span><i style="background:var(--s2)"></i>Renew</span></div>
      </div>
      <div class="card">
        <h3>PT Revenue: ตามระดับเทรนเนอร์</h3>
        <p class="note">รวม 12 เดือนล่าสุด</p>
        <div class="chart-wrap"><svg class="chart" id="ptTierChart" viewBox="0 0 460 280"></svg></div>
      </div>
    </div>
    <div class="card">
      <h3>PT Revenue: ตามแพ็กเกจ (จำนวนครั้ง)</h3>
      <p class="note">รวม 12 เดือนล่าสุด &middot; จับคู่จากราคาที่ขายจริงกับตารางราคาในชีต TPice</p>
      <div class="chart-wrap"><svg class="chart" id="ptPkgChart" viewBox="0 0 900 260"></svg></div>
    </div>
  </section>

  <section>
    <div class="section-head">
      <h2>2. ยอดสมาชิกใหม่ (NM)</h2>
      <p>แยกตาม New/Renew รายเดือน และแพ็กเกจสมาชิก</p>
    </div>
    <div class="chart-row">
      <div class="card">
        <h3>NM Revenue: New vs Renew รายเดือน</h3>
        <p class="note">12 เดือนล่าสุด &middot; หน่วย บาท</p>
        <div class="chart-wrap"><svg class="chart" id="nmNrChart" viewBox="0 0 700 280"></svg></div>
        <div class="legend"><span><i style="background:var(--s1)"></i>New</span><span><i style="background:var(--s2)"></i>Renew</span></div>
      </div>
      <div class="card">
        <h3>NM Revenue: ตามแพ็กเกจ</h3>
        <p class="note">รวม 12 เดือนล่าสุด &middot; "ไม่ระบุ" คือแถวที่ชีตไม่ได้กรอกประเภทแพ็กเกจไว้ (ดูจุดที่ต้องแก้ไขในรายงานพยากรณ์)</p>
        <div class="chart-wrap"><svg class="chart" id="nmPkgChart" viewBox="0 0 460 280"></svg></div>
      </div>
    </div>
  </section>

  <section>
    <div class="section-head">
      <h2>3. จำนวนสมาชิกใหม่ต่อเดือน</h2>
      <p>นับเฉพาะสมาชิกใหม่ (New) ไม่รวม Renew</p>
    </div>
    <div class="card">
      <div class="chart-wrap"><svg class="chart" id="nmCountChart" viewBox="0 0 900 260"></svg></div>
    </div>
  </section>

  <footer>
    <p><b>หมายเหตุ:</b> ระดับเทรนเนอร์ (Elite/Senior/Junior/GX) มาจากรายชื่อที่คลับให้มา ไม่ใช่ข้อมูลในชีต nmall โดยตรง &middot; แพ็กเกจ PT จับคู่จากราคาขายจริงเทียบกับตารางราคาในชีต TPice (คู่ตรงหรือใกล้เคียงในช่วง ±15%) รายการที่ไม่ตรงเลยจัดเป็น "อื่นๆ/ราคาพิเศษ"</p>
    <p>สร้างจาก generate_nmall_breakdown.py</p>
  </footer>

</div>

<script id="report-data" type="application/json">__DATA_JSON__</script>
<script>
const DATA = JSON.parse(document.getElementById('report-data').textContent);
const THB = v => '฿' + Math.round(v).toLocaleString('th-TH');
const monthTH = ['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'];
function fmtM(ym){ const [y,m] = ym.split('-'); return monthTH[parseInt(m,10)-1] + ' ' + (parseInt(y,10)+543-2500); }
const SERIES = ['--s1','--s2','--s3','--s4','--s5','--s6','--s7','--s8'].map(v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim());

function stackedMonthlyChart(svgId, monthlyObj, months, keys, keyColors){
  const svg = document.getElementById(svgId);
  const W=700,H=280,padL=54,padR=16,padT=16,padB=40;
  const totals = months.map(m => keys.reduce((s,k)=>s+(monthlyObj[m]?.[k]||0),0));
  const maxV = Math.max(...totals)*1.1 || 1;
  const n = months.length;
  const bw = (W-padL-padR)/n*0.62;
  const x = i => padL + (W-padL-padR)*(i/n) + (W-padL-padR)/n*0.19;
  const y = v => H-padB - (H-padT-padB)*(v/maxV);
  let g='';
  const steps=4;
  for(let s=0;s<=steps;s++){
    const v=maxV/steps*s, yy=y(v);
    g+=`<line x1="${padL}" y1="${yy}" x2="${W-padR}" y2="${yy}" stroke="var(--grid)" stroke-width="1"/>`;
    g+=`<text class="axis-label" x="${padL-8}" y="${yy+3}" text-anchor="end">${(v/1e6).toFixed(1)}M</text>`;
  }
  months.forEach((m,i)=>{
    g+=`<text class="axis-label" x="${x(i)+bw/2}" y="${H-padB+16}" text-anchor="middle">${fmtM(m)}</text>`;
    let acc=0;
    keys.forEach((k,ki)=>{
      const v=monthlyObj[m]?.[k]||0;
      if(v<=0) return;
      const y0=y(acc), y1=y(acc+v);
      g+=`<rect x="${x(i)}" y="${y1}" width="${bw}" height="${Math.max(0,y0-y1)}" fill="${keyColors[ki]}" rx="2"/>`;
      acc+=v;
    });
  });
  svg.innerHTML=g;
}

function hbarChart(svgId, dataObj, colorFn){
  const svg = document.getElementById(svgId);
  const W=460,H=280,padL=14,padR=70,padT=10,padB=10;
  const entries = Object.entries(dataObj);
  const maxV = Math.max(...entries.map(e=>e[1]))*1.05 || 1;
  const rowH = (H-padT-padB)/entries.length;
  const barH = rowH*0.56;
  const labelW = 128;
  const plotL = padL+labelW, plotR = W-padR;
  let g='';
  entries.forEach(([label,val],i)=>{
    const yc = padT + rowH*i + rowH/2;
    const w = (val/maxV)*(plotR-plotL);
    g+=`<text class="bar-label" x="${plotL-8}" y="${yc+4}" text-anchor="end">${label}</text>`;
    g+=`<rect x="${plotL}" y="${yc-barH/2}" width="${Math.max(2,w)}" height="${barH}" fill="${colorFn(i,label)}" rx="3"/>`;
    g+=`<text class="bar-label" x="${plotL+w+8}" y="${yc+4}" text-anchor="start" font-weight="600">${THB(val)}</text>`;
  });
  svg.innerHTML=g;
}

function barChart(svgId, dataObj, color){
  const svg = document.getElementById(svgId);
  const W=900,H=260,padL=60,padR=16,padT=16,padB=50;
  const entries = Object.entries(dataObj);
  const maxV = Math.max(...entries.map(e=>e[1]))*1.15 || 1;
  const n = entries.length;
  const bw = (W-padL-padR)/n*0.62;
  const x = i => padL + (W-padL-padR)*(i/n) + (W-padL-padR)/n*0.19;
  const y = v => H-padB - (H-padT-padB)*(v/maxV);
  let g='';
  const steps=4;
  for(let s=0;s<=steps;s++){
    const v=maxV/steps*s, yy=y(v);
    g+=`<line x1="${padL}" y1="${yy}" x2="${W-padR}" y2="${yy}" stroke="var(--grid)" stroke-width="1"/>`;
    g+=`<text class="axis-label" x="${padL-8}" y="${yy+3}" text-anchor="end">${v>=1e6?(v/1e6).toFixed(1)+'M':Math.round(v).toLocaleString('th-TH')}</text>`;
  }
  entries.forEach(([label,val],i)=>{
    const y0=y(0), y1=y(val);
    g+=`<rect x="${x(i)}" y="${y1}" width="${bw}" height="${Math.max(0,y0-y1)}" fill="${color}" rx="3"/>`;
    g+=`<text class="bar-label" x="${x(i)+bw/2}" y="${y1-6}" text-anchor="middle" font-weight="600">${typeof val==='number' && val<1000 ? Math.round(val) : THB(val)}</text>`;
    const lbl = String(label).length>10 ? label : label;
    g+=`<text class="axis-label" x="${x(i)+bw/2}" y="${H-padB+16}" text-anchor="middle">${label}</text>`;
  });
  svg.innerHTML=g;
}

stackedMonthlyChart('ptNrChart', DATA.pt_nr_monthly, DATA.last12, ['New','Renew'], [SERIES[0],SERIES[1]]);
stackedMonthlyChart('nmNrChart', DATA.nm_nr_monthly, DATA.last12, ['New','Renew'], [SERIES[0],SERIES[1]]);
hbarChart('ptTierChart', DATA.pt_tier_last12, (i)=>SERIES[i%SERIES.length]);
hbarChart('nmPkgChart', DATA.nm_package_last12, (i,label)=> label==='ไม่ระบุ' ? 'var(--muted)' : SERIES[i%SERIES.length]);
barChart('ptPkgChart', DATA.pt_package_last12, SERIES[0]);

(function(){
  const svg = document.getElementById('nmCountChart');
  const W=900,H=260,padL=44,padR=16,padT=16,padB=34;
  const months = DATA.nm_count_months;
  const vals = months.map(m=>DATA.nm_count_series[m]||0);
  const maxV = Math.max(...vals)*1.15 || 1;
  const n = months.length;
  const bw = (W-padL-padR)/n*0.66;
  const x = i => padL + (W-padL-padR)*(i/n) + (W-padL-padR)/n*0.17;
  const y = v => H-padB - (H-padT-padB)*(v/maxV);
  let g='';
  const steps=4;
  for(let s=0;s<=steps;s++){
    const v=maxV/steps*s, yy=y(v);
    g+=`<line x1="${padL}" y1="${yy}" x2="${W-padR}" y2="${yy}" stroke="var(--grid)" stroke-width="1"/>`;
    g+=`<text class="axis-label" x="${padL-8}" y="${yy+3}" text-anchor="end">${Math.round(v)}</text>`;
  }
  months.forEach((m,i)=>{
    const v=vals[i];
    const y0=y(0), y1=y(v);
    g+=`<rect x="${x(i)}" y="${y1}" width="${bw}" height="${Math.max(0,y0-y1)}" fill="var(--accent)" rx="2"/>`;
    if(i%2===0 || i===n-1) g+=`<text class="axis-label" x="${x(i)+bw/2}" y="${H-padB+16}" text-anchor="middle">${fmtM(m)}</text>`;
    g+=`<text class="bar-label" x="${x(i)+bw/2}" y="${y1-5}" text-anchor="middle">${v}</text>`;
  });
  svg.innerHTML=g;
})();
</script>
</body>
</html>
'''

HTML = HTML.replace("__DATA_JSON__", DATA_JSON)

with open("nmall_breakdown.html", "w", encoding="utf-8") as f:
    f.write(HTML)

print("สร้าง nmall_breakdown.html แล้ว")
