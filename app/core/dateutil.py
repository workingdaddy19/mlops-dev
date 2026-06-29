"""리스트 기간 조회용 날짜 파싱 헬퍼."""
from datetime import date


def parse_date(s: str | None) -> date | None:
    """YYYY-MM-DD(또는 앞 10자) → date. 실패 시 None."""
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None
