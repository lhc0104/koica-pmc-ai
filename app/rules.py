"""규칙 기반 자동 점검 (LLM 없이 동작) — 기한 알림 / 기초선 누락 / 이상치 / 후속조치 미이행"""
from datetime import date, datetime
from .db import connect, settings


def days_left(d: str, today: date | None = None) -> int | None:
    """기한까지 남은 일수. 날짜가 비었거나 형식(YYYY-MM-DD)이 틀리면 None"""
    try:
        return (datetime.strptime((d or "").strip(), "%Y-%m-%d").date() - (today or date.today())).days
    except ValueError:
        return None


_days_left = days_left


def deadline_alerts(today: date | None = None) -> list[dict]:
    """보조산출물·관리문서·마일스톤 중 기한이 지났거나 D-30 이내인 항목"""
    today = today or date.today()
    horizon = max(settings()["alerts"]["notice_days"])
    queries = {
        "보조산출물": ("SELECT sub_output_id AS ref, name, due_date, owner, status FROM sub_outputs "
                   "WHERE status NOT IN ('제출','승인')"),
        "관리문서": ("SELECT mdoc_id AS ref, name, next_due AS due_date, owner, status FROM management_docs "
                  "WHERE status NOT IN ('제출','완료')"),
        "마일스톤": ("SELECT milestone_id AS ref, title AS name, due_date, owner, status FROM milestones "
                  "WHERE status<>'완료'"),
    }
    out = []
    with connect(readonly=True) as con:
        for kind, q in queries.items():
            for r in con.execute(q):
                left = _days_left(r["due_date"], today)
                if left is not None and left <= horizon:
                    out.append({"구분": kind, "ref": r["ref"], "항목": r["name"], "기한": r["due_date"],
                                "D-day": left, "담당": r["owner"], "상태": r["status"],
                                "경보": "기한경과" if left < 0 else f"D-{left}"})
    return sorted(out, key=lambda x: x["D-day"])


def missing_baselines() -> list[dict]:
    """기초선 또는 목표치가 아직 비어 있는 지표(기초선 조사에서 확정해야 할 것)"""
    with connect(readonly=True) as con:
        rows = con.execute("SELECT indicator_id, name, mov, data_source, "
                           "CASE WHEN baseline IS NULL OR baseline='' THEN 1 ELSE 0 END AS no_baseline, "
                           "CASE WHEN target IS NULL OR target='' THEN 1 ELSE 0 END AS no_target "
                           "FROM pdm_indicators WHERE baseline IS NULL OR baseline='' OR target IS NULL OR target=''").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["missing"] = " · ".join(k for k, v in (("기초선", d.pop("no_baseline")), ("목표치", d.pop("no_target"))) if v)
        out.append(d)
    return out


def anomalies() -> list[dict]:
    """센터별 최근월 값이 전월 대비 기준(%) 이상 감소한 경우"""
    thr = settings()["alerts"]["anomaly_drop_pct"]
    q = """
    WITH ranked AS (
      SELECT center_id, metric, month, value,
             LAG(value) OVER (PARTITION BY center_id, metric ORDER BY month) AS prev,
             ROW_NUMBER() OVER (PARTITION BY center_id, metric ORDER BY month DESC) AS rn
      FROM center_monthly)
    SELECT r.center_id, c.name, r.metric, r.month, r.prev, r.value,
           ROUND((r.value - r.prev) * 100.0 / r.prev, 1) AS change_pct
    FROM ranked r JOIN centers c USING(center_id)
    WHERE r.rn = 1 AND r.prev > 0 AND (r.value - r.prev) * 100.0 / r.prev <= ?
    """
    with connect(readonly=True) as con:
        return [dict(r) for r in con.execute(q, (-thr,))]


def open_actions(today: date | None = None) -> list[dict]:
    today = today or date.today()
    with connect(readonly=True) as con:
        rows = con.execute("SELECT a.action_id, a.description, a.owner, a.due_date, a.status, m.title AS meeting "
                           "FROM action_items a LEFT JOIN meetings m USING(meeting_id) "
                           "WHERE a.status<>'완료'").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["overdue"] = (_days_left(d["due_date"], today) or 0) < 0
        out.append(d)
    return out


def all_alerts(today: date | None = None) -> dict:
    return {"기한": deadline_alerts(today), "기초선누락": missing_baselines(),
            "이상치": anomalies(), "후속조치": open_actions(today)}
