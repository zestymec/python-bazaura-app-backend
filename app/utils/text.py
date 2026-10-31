import re
import secrets
import unicodedata
from datetime import UTC, datetime

# No 0/O or 1/I so codes are easy to read over the phone.
_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def slugify(value: str, max_length: int = 180) -> str:
    """'Men's Winter Hoodie (Black)' -> 'mens-winter-hoodie-black'"""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"['’]", "", value.lower())
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:max_length].rstrip("-") or "item"


def human_reference(prefix: str) -> str:
    """Customer-facing reference such as `BZ-261031-7KQ2` (prefix-date-random)."""
    date_part = datetime.now(UTC).strftime("%y%m%d")
    random_part = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    return f"{prefix}-{date_part}-{random_part}"
