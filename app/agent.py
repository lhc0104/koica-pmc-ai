"""모듈③ AI 대화형 사업비서 — LLM + 도구 호출(정형 DB 조회 + 문서 검색) 루프 (v0.9: 공급자 선택·연결 설정)

공급자: anthropic(Claude, 기본) / openai(GPT).  설정 우선순위: 환경변수(.env 또는 Streamlit Secrets) > config/settings.yaml
  AIKME_LLM_PROVIDER = anthropic | openai
  AIKME_LLM_MODEL    = 모델 이름 (비우면 공급자별 기본값)
  ANTHROPIC_API_KEY / OPENAI_API_KEY
PC에서는 화면의 [AI 연결 설정]이 .env 에 적어 주고, Streamlit Cloud 에서는 앱 설정 › Secrets 에 같은 이름으로 넣는다.
"""
import json
import os
import re
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from . import storage, tools
from .db import ROOT, connect, schema_text, settings

ENV_FILE = ROOT / ".env"
load_dotenv(ENV_FILE)

PROVIDERS = {"anthropic": "Claude (Anthropic)", "openai": "GPT (OpenAI)"}
KEY_NAMES = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}
DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-5"}
MODEL_CHOICES = {"anthropic": ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5", "claude-sonnet-4-5"],
                 "openai": ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4o"]}


# ───────── 설정 ─────────
def provider() -> str:
    p = (os.getenv("AIKME_LLM_PROVIDER") or settings()["llm"].get("provider") or "anthropic").strip().lower()
    return p if p in PROVIDERS else "anthropic"


def model() -> str:
    m = (os.getenv("AIKME_LLM_MODEL") or "").strip()
    if m:
        return m
    cfg = settings()["llm"]
    if provider() == "anthropic":
        return cfg.get("model") or DEFAULT_MODELS["anthropic"]
    return cfg.get("openai_model") or DEFAULT_MODELS["openai"]


def key_name() -> str:
    return KEY_NAMES[provider()]


def has_key() -> bool:
    return bool((os.getenv(key_name()) or "").strip())


def masked_key() -> str:
    k = (os.getenv(key_name()) or "").strip()
    return f"{k[:7]}…{k[-4:]}" if len(k) > 14 else ("설정됨" if k else "없음")


def status() -> dict:
    return {"provider": provider(), "provider_label": PROVIDERS[provider()], "model": model(), "key_name": key_name(),
            "has_key": has_key(), "masked_key": masked_key(), "env_file": str(ENV_FILE), "env_exists": ENV_FILE.exists(),
            "sdk": _sdk_available(provider())}


def _sdk_available(p: str) -> bool:
    try:
        __import__("anthropic" if p == "anthropic" else "openai")
        return True
    except ImportError:
        return False


def save_env(values: dict) -> tuple[bool, str]:
    """.env 에 키=값을 적고(있으면 바꾸고) 현재 프로세스 환경에도 반영.  Cloud 에서는 재배포 때 사라지므로 Secrets 를 써야 한다"""
    storage.check_edit()
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    except OSError as e:
        return False, f".env 를 읽지 못했습니다: {e}"
    for k, v in values.items():
        v = (v or "").strip()
        if v == "":
            continue
        pat = re.compile(rf"^\s*{re.escape(k)}\s*=")
        line = f"{k}={v}"
        for i, ln in enumerate(lines):
            if pat.match(ln):
                lines[i] = line
                break
        else:
            lines.append(line)
        os.environ[k] = v
    try:
        ENV_FILE.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    except OSError as e:
        return False, f".env 에 쓰지 못했습니다: {e}"
    return True, f"{storage.rel(ENV_FILE)} 에 저장했습니다."


# ───────── 호출 ─────────
def _system_prompt() -> str:
    tpl = (ROOT / "prompts" / "system_prompt.md").read_text(encoding="utf-8")
    return tpl.replace("{today}", date.today().isoformat()).replace("{schema}", schema_text())


def _friendly(e: Exception) -> str:
    s = str(e)
    if "401" in s or "authentication" in s.lower() or "invalid x-api-key" in s.lower() or "Incorrect API key" in s:
        return "API 키가 틀렸거나 만료되었습니다. [AI 연결 설정]에서 키를 다시 넣어 주세요."
    if "404" in s and ("model" in s.lower() or "not_found" in s.lower()):
        return f"모델 이름 '{model()}' 을(를) 찾을 수 없습니다. [AI 연결 설정]에서 다른 모델을 고르세요."
    if "429" in s or "rate" in s.lower() and "limit" in s.lower():
        return "요청이 너무 많거나 사용 한도에 닿았습니다. 잠시 뒤 다시 시도하거나 결제 상태를 확인해 주세요."
    if "credit" in s.lower() or "billing" in s.lower() or "insufficient_quota" in s:
        return "API 사용 크레딧(결제)이 부족합니다. 공급자 콘솔에서 결제를 확인해 주세요."
    if "connection" in s.lower() or "timeout" in s.lower():
        return "API 서버에 연결하지 못했습니다. 네트워크를 확인해 주세요."
    return s


def test_connection() -> tuple[bool, str]:
    """짧은 호출로 키·모델이 맞는지 확인"""
    if not has_key():
        return False, f"{key_name()} 가 없습니다."
    try:
        if provider() == "anthropic":
            import anthropic
            r = anthropic.Anthropic().messages.create(model=model(), max_tokens=20, messages=[{"role": "user", "content": "한 단어로 인사해 주세요."}])
            txt = "".join(b.text for b in r.content if b.type == "text")
        else:
            import openai
            r = openai.OpenAI().chat.completions.create(model=model(), max_completion_tokens=20, messages=[{"role": "user", "content": "한 단어로 인사해 주세요."}])
            txt = r.choices[0].message.content or ""
        return True, f"연결 성공 — {PROVIDERS[provider()]} · {model()} · 응답: {txt.strip()[:40]}"
    except Exception as e:
        return False, _friendly(e)


def _ask_anthropic(question: str, history: list, cfg: dict) -> tuple[str, list, list]:
    import anthropic
    client = anthropic.Anthropic()
    messages = list(history) + [{"role": "user", "content": question}]
    calls, answer = [], ""
    for _ in range(cfg["max_tool_rounds"]):
        resp = client.messages.create(model=model(), max_tokens=cfg["max_tokens"], system=_system_prompt(), tools=tools.TOOLS, messages=messages)
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
    return answer, calls, messages


def _ask_openai(question: str, history: list, cfg: dict) -> tuple[str, list, list]:
    import openai
    client = openai.OpenAI()
    oa_tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}} for t in tools.TOOLS]
    messages = list(history) + [{"role": "user", "content": question}]
    calls, answer = [], ""
    for _ in range(cfg["max_tool_rounds"]):
        resp = client.chat.completions.create(model=model(), max_completion_tokens=cfg["max_tokens"], tools=oa_tools,
                                              messages=[{"role": "system", "content": _system_prompt()}] + messages)
        msg = resp.choices[0].message
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [tc.model_dump() for tc in (msg.tool_calls or [])]} if msg.tool_calls
                        else {"role": "assistant", "content": msg.content or ""})
        if not msg.tool_calls:
            answer = msg.content or ""
            break
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except ValueError:
                args = {}
            out = tools.execute(tc.function.name, args)
            calls.append({"tool": tc.function.name, "input": args, "output_preview": out[:500]})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})
    else:
        answer = "도구 호출 한도를 초과했습니다. 질문을 더 구체적으로 나누어 주세요."
    return answer, calls, messages


def ask(question: str, history: list | None = None, user_id: str = "") -> dict:
    """질문 1건 처리. 반환: {answer, tool_calls, messages}.  오류는 읽기 쉬운 문장으로 RuntimeError"""
    cfg = settings()["llm"]
    if not has_key():
        raise RuntimeError(f"{key_name()} 가 설정되어 있지 않습니다. 관리자가 [AI 연결 설정]에서 키를 넣어야 합니다.")
    try:
        answer, calls, messages = (_ask_anthropic if provider() == "anthropic" else _ask_openai)(question, history or [], cfg)
    except Exception as e:
        raise RuntimeError(_friendly(e)) from e
    with connect() as con:  # 답변 정확도 검증(전문가 평가)을 위한 로그
        con.execute("INSERT INTO chat_log(user_id, question, answer, tool_calls) VALUES (?,?,?,?)",
                    (user_id, question, answer, json.dumps(calls, ensure_ascii=False)))
    storage.export_table("chat_log")
    return {"answer": answer, "tool_calls": calls, "messages": messages}


def simple(prompt: str, max_tokens: int = 1200) -> str:
    """도구 없이 한 번 묻기 (AI 점검 질문 다듬기 등)"""
    if provider() == "anthropic":
        import anthropic
        r = anthropic.Anthropic().messages.create(model=model(), max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in r.content if b.type == "text")
    import openai
    r = openai.OpenAI().chat.completions.create(model=model(), max_completion_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
    return r.choices[0].message.content or ""
