"""모듈③ AI 대화형 사업비서 — LLM + 도구 호출(정형 DB 조회 + 문서 검색) 루프"""
import json
import os
from datetime import date
from dotenv import load_dotenv
from . import storage, tools
from .db import ROOT, connect, schema_text, settings

load_dotenv(ROOT / ".env")


def has_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _system_prompt() -> str:
    tpl = (ROOT / "prompts" / "system_prompt.md").read_text(encoding="utf-8")
    return tpl.replace("{today}", date.today().isoformat()).replace("{schema}", schema_text())


def ask(question: str, history: list | None = None, user_id: str = "") -> dict:
    """질문 1건 처리. 반환: {answer, tool_calls, messages}"""
    import anthropic
    cfg = settings()["llm"]
    client = anthropic.Anthropic()
    messages = list(history or []) + [{"role": "user", "content": question}]
    calls, answer = [], ""

    for _ in range(cfg["max_tool_rounds"]):
        resp = client.messages.create(model=cfg["model"], max_tokens=cfg["max_tokens"],
                                      system=_system_prompt(), tools=tools.TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            answer = "\n".join(b.text for b in resp.content if b.type == "text")
            break
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = tools.execute(b.name, b.input)
                calls.append({"tool": b.name, "input": b.input, "output_preview": out[:500]})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
        messages.append({"role": "user", "content": results})
    else:
        answer = "도구 호출 한도를 초과했습니다. 질문을 더 구체적으로 나누어 주세요."

    with connect() as con:  # 답변 정확도 검증(전문가 평가)을 위한 로그
        con.execute("INSERT INTO chat_log(user_id, question, answer, tool_calls) VALUES (?,?,?,?)",
                    (user_id, question, answer, json.dumps(calls, ensure_ascii=False)))
    storage.export_table("chat_log")
    return {"answer": answer, "tool_calls": calls, "messages": messages}
