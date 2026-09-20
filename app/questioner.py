"""AI가 담당자에게 '질문을 내는' 기능.
규칙 점검에서 발견된 공백·이상 징후를 담당자용 질문으로 바꾸어 ai_questions에 쌓고,
답변은 다시 지식베이스에 남아 이후 보고서·질의응답의 근거가 된다.
API 키가 없으면 템플릿 문장으로, 있으면 LLM이 맥락을 반영해 다듬는다."""
import json
from . import rules, storage
from .db import connect, settings


def _draft() -> list[dict]:
    a, out = rules.all_alerts(), []
    for r in a["기초선누락"]:
        out.append(dict(trigger_type="기초선누락", target_ref=r["indicator_id"], assignee="성과관리 전문가",
                        question=f"지표 {r['indicator_id']} '{r['name']}'의 {r['missing']}가 아직 정해지지 않았습니다. 어떤 자료원({r['data_source'] or '미정'})에서 언제 확정할 예정인가요?"))
    for r in a["기한"]:
        if r["D-day"] <= 14:
            out.append(dict(trigger_type="기한임박", target_ref=r["ref"], assignee=r["담당"] or "PL",
                            question=f"{r['구분']} '{r['항목']}'의 기한이 {r['기한']}({r['경보']})입니다. 현재 상태는 '{r['상태']}'인데, 기한 내 제출이 가능한가요? 어려우면 사유와 예상 일정을 알려주세요."))
    for r in a["이상치"]:
        out.append(dict(trigger_type="이상치", target_ref=f"{r['center_id']}|{r['metric']}|{r['month']}", assignee="PAO",
                        question=f"{r['name']}의 {r['month']} {r['metric']}가 전월 대비 {r['change_pct']}% 변동했습니다({r['prev']:.0f}→{r['value']:.0f}). 현장에서 파악된 원인이 있나요? (휴진·인력 공백·자료 누락 등)"))
    for r in a["후속조치"]:
        if r["overdue"]:
            out.append(dict(trigger_type="후속조치미이행", target_ref=f"action-{r['action_id']}", assignee=r["owner"] or "PL",
                            question=f"'{r['meeting']}' 후속조치 '{r['description']}'의 기한({r['due_date']})이 지났습니다. 진행 상황과 완료 예정일을 알려주세요."))
    return out


def _polish_with_llm(items: list[dict]) -> list[dict]:
    import anthropic
    cfg = settings()["llm"]
    prompt = ("아래는 ODA PMC 사업의 자동 점검에서 만들어진 담당자용 질문 초안이다. 각 질문을 담당자가 한 번에 답할 수 있게 "
              "정중하고 구체적인 한국어 1~2문장으로 다듬어라. 사실(수치·날짜·명칭)은 바꾸지 말 것. "
              "입력과 같은 순서의 JSON 문자열 배열만 출력하라.\n\n" + json.dumps([i["question"] for i in items], ensure_ascii=False))
    resp = anthropic.Anthropic().messages.create(model=cfg["model"], max_tokens=cfg["max_tokens"],
                                                 messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in resp.content if b.type == "text").replace("```json", "").replace("```", "").strip()
    polished = json.loads(text)
    if len(polished) == len(items):
        for i, q in zip(items, polished):
            i["question"] = q
    return items


def generate(use_llm: bool = False) -> int:
    """새 질문을 생성해 저장하고 신규 건수를 반환 (같은 트리거·대상은 중복 생성하지 않음)"""
    with connect() as con:
        seen = {(r[0], r[1]) for r in con.execute("SELECT trigger_type, target_ref FROM ai_questions")}
    items = [i for i in _draft() if (i["trigger_type"], i["target_ref"]) not in seen]
    if items and use_llm:
        try:
            items = _polish_with_llm(items)
        except Exception as e:
            print(f"[경고] LLM 다듬기 실패 → 템플릿 질문 사용: {e}")
    with connect() as con:
        con.executemany("INSERT OR IGNORE INTO ai_questions(trigger_type, target_ref, assignee, question) "
                        "VALUES (:trigger_type, :target_ref, :assignee, :question)", items)
    storage.export_table("ai_questions")
    return len(items)


def answer(qid: int, text: str) -> None:
    with connect() as con:
        con.execute("UPDATE ai_questions SET answer=?, answered_at=CURRENT_TIMESTAMP, status='답변완료' WHERE id=?", (text, qid))
    storage.export_table("ai_questions")
