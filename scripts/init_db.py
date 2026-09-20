"""DB 준비.  원본은 pmc/ 폴더의 파일이고, DB는 그 파일로 언제든 다시 만들 수 있다.

  python scripts/init_db.py              폴더·DB 준비(없는 것만 채움)
  python scripts/init_db.py --reset      DB를 지우고 pmc/ 폴더의 파일로 다시 만듦 (입력한 내용 유지)
  python scripts/init_db.py --from-seed  pmc/ 의 CSV를 초기 예시값(data/seed)으로 되돌림 ※입력한 내용이 지워짐
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import storage
from app.db import connect, data_dir, db_path

if __name__ == "__main__":
    if "--reset" in sys.argv or "--from-seed" in sys.argv:
        if db_path().exists():
            db_path().unlink()
        storage.STATE.unlink(missing_ok=True)
    for m in storage.bootstrap(from_seed="--from-seed" in sys.argv):
        print(" ", m)
    with connect(readonly=True) as con:
        for t, (f, fn, _) in storage.TABLES.items():
            print(f"  - {f}/{fn}: {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}행")
    print(f"완료\n  데이터 폴더: {data_dir()}\n  DB(캐시)   : {db_path()}")
