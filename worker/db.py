"""DB 연결. 공통 파일: A만 수정한다.

사용 예:
    from db import get_conn
    with get_conn() as conn:
        rows = conn.execute("SELECT 1").fetchall()
"""
import psycopg

from config import DATABASE_URL


def get_conn() -> psycopg.Connection:
    """새 연결을 돌려준다. `with` 로 쓰면 블록이 끝날 때 커밋(예외면 롤백)하고 닫는다."""
    return psycopg.connect(DATABASE_URL)


if __name__ == "__main__":
    # 연결 확인: python db.py
    with get_conn() as conn:
        n = conn.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
        ).fetchone()[0]
        print(f"DB 연결 OK, public 테이블 {n}개")
