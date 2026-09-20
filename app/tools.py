"""LLM에 제공하는 도구 정의와 실행기"""
import json
import re
from . import rules
from .db import connect
from .search import search_documents

TOOLS = [
    {
        "name": "run_sql",
        "description": "사업 지식베이스(SQLite)에 읽기 전용 SELECT 쿼리를 실행한다. 기한·상태·지표값·센터 실적 등 정형 데이터 조회·집계·비교에 사용. 최대 200행 반환.",
        "input_schema": {"type": "object",
                         "properties": {"query": {"type": "string", "description": "단일 SELECT 문"}},
                         "required": ["query"]},
    },
    {
        "name": "search_documents",
        "description": "회의록·보고서·공문·기준문서(RFP, R/D, PDM, POD/OD)·2차자료의 본문을 검색한다. 결과에는 출처(doc_id, 제목, 일자)가 포함된다.",
        "input_schema": {"type": "object",
                         "properties": {"query": {"type": "string", "description": "핵심 키워드(공백 구분)"},
                                        "doc_type": {"type": "string", "description": "선택: 기준문서/회의록/보고서/공문/2차자료/주간보고"}},
                         "required": ["query"]},
    },
    {
        "name": "get_alerts",
        "description": "규칙 기반 자동 점검 결과를 반환한다: 기한 임박·경과 항목, 기초선 누락 지표, 센터 실적 이상치, 미이행 후속조치.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _run_sql(query: str):
    q = query.strip().rstrip(";")
    if not re.match(r"(?is)^\s*(select|with)\b", q) or ";" in q:
        return {"error": "단일 SELECT 문만 허용됩니다."}
    try:
        with connect(readonly=True) as con:
            rows = con.execute(q).fetchmany(200)
        return [dict(r) for r in rows]
    except Exception as e:  # 오류를 LLM에 돌려주어 스스로 수정하게 함
        return {"error": str(e)}


def execute(name: str, args: dict) -> str:
    if name == "run_sql":
        res = _run_sql(args.get("query", ""))
    elif name == "search_documents":
        res = search_documents(args.get("query", ""), args.get("doc_type"))
    elif name == "get_alerts":
        res = rules.all_alerts()
    else:
        res = {"error": f"알 수 없는 도구: {name}"}
    return json.dumps(res, ensure_ascii=False, default=str)
