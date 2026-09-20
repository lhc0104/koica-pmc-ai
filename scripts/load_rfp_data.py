"""RFP·PDM 기준 데이터 적용.  현재 pmc/ 의 표를 _백업 에 남긴 뒤 data/seed 의 RFP 기반 자료로 바꾼다.
(질의응답 기록·AI 점검 질문 답변·문제보고 메모는 건드리지 않는다)

  python scripts/load_rfp_data.py            적용
  python scripts/load_rfp_data.py --no-demo  [예시] 회의·실적 자료 없이 적용
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import storage
from app.db import ROOT, connect, data_dir, db_path

DEMO = {"meetings", "action_items", "center_monthly", "weekly_reports", "weekly_entries"}
KEEP = {"chat_log", "ai_questions", "issue_reports", "users"}

if __name__ == "__main__":
    storage.bootstrap()                                              # 폴더·DB가 없으면 먼저 만든다
    bak = data_dir() / "_백업" / f"RFP적용전_{datetime.now():%Y%m%d_%H%M%S}"
    bak.mkdir(parents=True, exist_ok=True)
    for t in storage.TABLES:
        if storage.csv_path(t).exists():
            shutil.copy(storage.csv_path(t), bak / storage.csv_path(t).name)
    if storage.overview_path().exists():
        shutil.copy(storage.overview_path(), bak / storage.overview_path().name)
    shutil.copy(ROOT / "config" / "overview.yaml", storage.overview_path())

    for t in storage.TABLES:
        if t in KEEP:
            continue
        seed = ROOT / "data" / "seed" / f"{t}.csv"
        if not seed.exists():
            continue
        shutil.copy(seed, storage.csv_path(t))
        if t in DEMO and "--no-demo" in sys.argv:                    # 머리글만 남긴다
            head = seed.read_text(encoding="utf-8-sig").splitlines()[0]
            storage.csv_path(t).write_text(head + "\n", encoding="utf-8-sig")
    with connect() as con:                                           # 예시 자료에서 만들어진 미답변 질문은 정리
        con.execute("DELETE FROM ai_questions WHERE status='대기'")
    storage.export_table("ai_questions")

    if db_path().exists():
        db_path().unlink()                                           # 캐시 DB는 새 파일로 다시 만든다
    storage.STATE.unlink(missing_ok=True)
    storage.bootstrap()
    with connect(readonly=True) as con:
        for t, (f, fn, _) in storage.TABLES.items():
            print(f"  - {f}/{fn}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}행")
        print(f"  - 검색 색인 문서: {con.execute('SELECT COUNT(*) FROM documents').fetchone()[0]}건, "
              f"{con.execute('SELECT COUNT(*) FROM doc_chunks').fetchone()[0]}개 구간")
    print(f"완료. 이전 자료는 {bak} 에 있습니다.")
