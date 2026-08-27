"""
ค่าคงที่ + ฟังก์ชันช่วยที่ generate_dashboard.py และ send_telegram.py ใช้ร่วมกัน
(เดิมสองไฟล์นิยาม GOAL / EXCLUDE_MEM / num / fmt / การแยกแถวสรุปคลับ ซ้ำกันคนละชุด)
"""

# เป้าหมาย
GOAL_PT_SOLD = 2_400_000 * 1.07   # 2,568,000 ฿ (รวม VAT 7%)
GOAL_MEMBER = 125                  # เป้าสมาชิกรวมคลับ
GOAL_MEM_EACH = 6                  # เป้าสมาชิกรายบุคคล

# บัญชีกลาง/ช่องทางออนไลน์ ไม่นับเป็นสมาชิกใหม่ของเทรนเนอร์
EXCLUDE_MEM = {"BGPL_Ou_00936", "ecommerce_website", "Online"}

# ชื่อคลับที่ใช้ระบุแถว "สรุปรวม" ในตาราง conduct/sold (แถวอื่นคือรายบุคคล)
CLUB_KEY = "Ratchaphruek"


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def fmt(v):
    try:
        return f"{num(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def split_club(rows):
    """แยกแถวสรุประดับคลับ ออกจากแถวรายบุคคล -> (club_row, [individual_rows])"""
    club = next((r for r in rows if CLUB_KEY in r.get("Trainer", "")), {})
    individuals = [r for r in rows if r.get("Trainer", "") and CLUB_KEY not in r["Trainer"]]
    return club, individuals


def active_mem_summary(data):
    """สรุป membership รายเทรนเนอร์ ตัดบัญชีกลาง/ช่องทางออนไลน์ออกแล้ว"""
    return [r for r in data["membership"]["summary"] if r["sold_by"] not in EXCLUDE_MEM]
