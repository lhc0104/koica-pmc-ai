"""RFP의 '생산시점·제출시점' 문구(due_rule)를 실제 날짜로 바꾸는 규칙.

  계약 체결 후 3개월 이내 → 계약체결일 + 3개월        2차년도 2분기 → 2027-06-30 (1차년도 = 2026)
  매년 7월 15일 및 1월 15일 이전 → 다음 도래일         매 익월 10일 이전 → 다음 10일 / 차주 월요일 → 다음 월요일
  '모니터링 후 2주 이내'처럼 사건 기준인 문구는 날짜를 정할 수 없어 빈칸으로 둔다(사건 발생 시 직접 입력).
"""
import calendar
import re
from datetime import date, timedelta

FIRST_YEAR = 2026


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def quarter_end(year: int, q: int) -> date:
    m = q * 3
    return date(year, m, calendar.monthrange(year, m)[1])


def parse_q(text: str) -> tuple[int, int] | None:
    m = re.fullmatch(r"(\d{4})Q([1-4])", (text or "").strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def due_from_rule(rule: str, contract: date | None, today: date | None = None) -> date | None:
    rule, today = (rule or "").strip(), today or date.today()
    if not rule:
        return None
    if contract and contract > today:          # 반복 기한은 계약 이후부터 의미가 있다
        today = contract
    m = re.search(r"(\d{4})년 (\d{1,2})월 (\d{1,2})일", rule)                 # 날짜가 명시된 경우
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"계약 ?체결 후 (\d+) ?(주|개월)", rule)
    if m:
        if not contract:
            return None
        n = int(m.group(1))
        return contract + timedelta(weeks=n) if m.group(2) == "주" else _add_months(contract, n)
    if "계약 체결 전" in rule:
        return contract
    m = re.search(r"(\d)차년도 ?(\d)(?:/(\d))?분기", rule)                     # '4차년도 1/2분기' → 2분기 말
    if m:
        return quarter_end(FIRST_YEAR + int(m.group(1)) - 1, int(m.group(3) or m.group(2)))
    days = re.findall(r"(\d{1,2})월 (\d{1,2})일", rule)
    if "매년" in rule and days:                                               # 매년 반복: 다음 도래일
        cands = [date(y, int(mo), int(d)) for y in (today.year, today.year + 1) for mo, d in days]
        return min(c for c in cands if c >= today)
    if "익월 10일" in rule:
        return date(today.year, today.month, 10) if today.day <= 10 else _add_months(date(today.year, today.month, 10), 1)
    if "차주 월요일" in rule:
        return today + timedelta(days=(7 - today.weekday()) % 7 or 7)
    return None


def recalc(contract: date, today: date | None = None) -> dict:
    """due_rule이 있는 미완료 행의 기한을 다시 계산해 DB와 CSV에 반영. 반환: {표: 바뀐 행 수}"""
    from . import storage
    from .db import connect
    spec = {"sub_outputs": ("sub_output_id", "due_date", ("제출", "승인")),
            "management_docs": ("mdoc_id", "next_due", ("완료",)),
            "milestones": ("milestone_id", "due_date", ("완료",))}
    changed = {}
    for t, (pk, col, done) in spec.items():
        n = 0
        with connect() as con:
            for r in con.execute(f"SELECT {pk} AS k, {col} AS d, due_rule, status FROM {t} WHERE due_rule<>''").fetchall():
                if r["status"] in done:
                    continue
                new = due_from_rule(r["due_rule"], contract, today)
                if new and new.isoformat() != r["d"]:
                    con.execute(f"UPDATE {t} SET {col}=? WHERE {pk}=?", (new.isoformat(), r["k"]))
                    n += 1
        if n:
            storage.export_table(t)
        changed[t] = n
    return changed
