import sys
sys.path.insert(0, '/Users/oran_raurhotmail.com/Library/Python/3.9/lib/python/site-packages')

import os, json, time
from datetime import datetime
from playwright.sync_api import sync_playwright

USERNAME = os.getenv("JETTS_USERNAME", "00936")
PASSWORD = os.getenv("JETTS_PASSWORD", "Ou.oraya00936")

def get_date_range():
    today = datetime.now()
    start = today.replace(day=1).strftime("%d/%m/%Y")
    end = today.strftime("%d/%m/%Y")
    return start, end

def login(page):
    page.goto("https://jettsapp.jetts.co.th", timeout=60000)
    page.wait_for_selector("#txtUsername", timeout=60000)
    page.fill("#txtUsername", USERNAME)
    page.fill("#txtPassword", PASSWORD)
    page.click("#BtnSubmit")
    page.wait_for_load_state("load")
    time.sleep(3)

def scrape_table(page, url, start_date, end_date):
    page.goto(url, timeout=30000)
    page.wait_for_load_state("load")
    time.sleep(2)

    # ตั้งวันที่ผ่าน JS (field เป็น readonly datepicker)
    page.evaluate(f"""
        document.querySelector("input[name='ctl00$MainContent$TxtStartDate']").value = '{start_date}';
        document.querySelector("input[name='ctl00$MainContent$TxtEndDate']").value = '{end_date}';
    """)

    page.click("input[value='Search']")
    page.wait_for_load_state("load")
    time.sleep(3)

    # กด + เพื่อ expand รายบุคคล (ลอง selector หลายแบบ)
    for sel in [
        "i.fa-plus-circle",
        "i.fa-plus",
        "span.expand",
        "td:first-child i",
        "a[onclick*='expand']",
    ]:
        plus_btn = page.query_selector(sel)
        if plus_btn:
            try:
                plus_btn.click()
                time.sleep(3)
            except Exception:
                pass
            break
    # รอให้ expand เสร็จแล้วดึงข้อมูลอีกครั้ง
    time.sleep(1)

    # ดึงตารางหลัก (ตารางแรกที่ไม่ใช่ calendar)
    tables = page.query_selector_all("table")
    result = []
    headers = []

    for tbl in tables:
        ths = tbl.query_selector_all("th")
        header_texts = [h.inner_text().strip() for h in ths]
        if header_texts and header_texts not in [[], ['Su','Mo','Tu','We','Th','Fr','Sa']]:
            headers = header_texts
            rows = tbl.query_selector_all("tr")
            for row in rows[1:]:  # ข้าม header row
                cells = row.query_selector_all("td")
                cell_texts = [c.inner_text().strip() for c in cells]
                if cell_texts and any(cell_texts):
                    result.append(dict(zip(headers, cell_texts)))
            break  # ดึงแค่ตารางแรก

    return {"headers": headers, "rows": result}

def scrape_membership(page, start_date, end_date):
    page.goto("https://jettsapp.jetts.co.th/MemberRegisterReport", timeout=30000)
    page.wait_for_load_state("load")
    time.sleep(2)

    # เลือก Club (Jetts Robinson Ratchaphruek = value 46)
    page.evaluate("""
        var sel = document.querySelector("select[name='ctl00$MainContent$DdlClub']");
        for(var i=0; i<sel.options.length; i++){
            sel.options[i].selected = (sel.options[i].value === '46');
        }
        sel.dispatchEvent(new Event('change'));
    """)
    time.sleep(1)

    page.evaluate(f"""
        document.querySelector("input[name='ctl00$MainContent$TxtStartDate']").value = '{start_date}';
        document.querySelector("input[name='ctl00$MainContent$TxtEndDate']").value = '{end_date}';
    """)

    page.click("input[value='Search']")
    page.wait_for_load_state("load")
    time.sleep(3)

    all_rows = []
    page_num = 1

    while True:
        print(f"    หน้า {page_num}...")
        # ดึงตารางหลัก
        tables = page.query_selector_all("table")
        for tbl in tables:
            ths = tbl.query_selector_all("th")
            header_texts = [h.inner_text().strip() for h in ths]
            if "Sold by" in header_texts:
                rows = tbl.query_selector_all("tr")
                for row in rows[1:]:
                    cells = row.query_selector_all("td")
                    if len(cells) >= 11:
                        sold_by = cells[10].inner_text().strip()
                        sold_date = cells[1].inner_text().strip()
                        app_id_raw = cells[2].inner_text().strip()
                        app_id = app_id_raw.split("\n")[0].strip()
                        membership = app_id_raw.split("\n")[1].strip("()") if "\n" in app_id_raw else ""
                        client = cells[3].inner_text().strip()
                        if sold_by:
                            all_rows.append({
                                "sold_date": sold_date,
                                "app_id": app_id,
                                "membership": membership,
                                "client": client,
                                "sold_by": sold_by
                            })
                break

        # หา pagination ถัดไป — ใช้ <span page="N" class="page_inactive">
        next_span = page.query_selector(f'span[page="{page_num + 1}"].page_inactive')
        if next_span is None:
            break

        next_span.click()
        page.wait_for_load_state("load")
        time.sleep(2)
        page_num += 1

    # นับ sold_by ต่อคน
    from collections import Counter
    counts = Counter(r["sold_by"] for r in all_rows)
    summary = [{"sold_by": k, "count": v} for k, v in counts.most_common()]

    return {"rows": all_rows, "summary": summary}


def main():
    start_date, end_date = get_date_range()
    print(f"ช่วงวันที่: {start_date} - {end_date}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        print("กำลัง login...")
        login(page)
        print("Login สำเร็จ")

        print("ดึงข้อมูล PT Conduct Commission...")
        conduct = scrape_table(
            page,
            "https://jettsapp.jetts.co.th/PTConductCommissionReport",
            start_date, end_date
        )
        print(f"  ได้ {len(conduct['rows'])} แถว")

        print("ดึงข้อมูล PT Sold Commission...")
        sold = scrape_table(
            page,
            "https://jettsapp.jetts.co.th/PTSoldCommissionReport",
            start_date, end_date
        )
        print(f"  ได้ {len(sold['rows'])} แถว")

        print("ดึงข้อมูล Membership Report...")
        membership = scrape_membership(page, start_date, end_date)
        print(f"  ได้ {len(membership['rows'])} แถว จาก {len(membership['summary'])} คน")

        browser.close()

    output = {
        "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "period": {"start": start_date, "end": end_date},
        "conduct": conduct,
        "sold": sold,
        "membership": membership
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("บันทึก data.json แล้ว")

if __name__ == "__main__":
    main()
