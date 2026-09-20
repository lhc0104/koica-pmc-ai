"""규칙 점검 결과 출력 + AI 점검 질문 생성. 매일 1회 스케줄러(cron 등)로 실행 권장.
사용: python scripts/check_alerts.py [--llm]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import questioner, rules
from app.agent import has_key

if __name__ == "__main__":
    a = rules.all_alerts()
    print("■ 기한 임박·경과")
    for r in a["기한"]:
        print(f"  [{r['경보']:>6}] {r['구분']} {r['ref']} {r['항목']} (기한 {r['기한']}, {r['상태']})")
    print(f"■ 기초선 누락 지표: {len(a['기초선누락'])}건")
    print("■ 이상치")
    for r in a["이상치"]:
        print(f"  {r['center_id']} {r['month']} {r['metric']} {r['change_pct']}%")
    print(f"■ 미완료 후속조치: {len(a['후속조치'])}건")
    n = questioner.generate(use_llm="--llm" in sys.argv and has_key())
    print(f"→ AI 점검 질문 {n}건 신규 생성")
