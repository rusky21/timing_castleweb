import re
from typing import Optional


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """
    Приводит телефонные номера РФ к единому международному формату (+7XXXXXXXXXX).
    Если номер не соответствует 10 или 11 цифрам, возвращает исходную непустую строку или None.
    """
    if not raw or not isinstance(raw, str):
        return None
    raw_str = raw.strip()
    digits = re.sub(r"\D", "", raw_str)
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return f"+7{digits[1:]}"
    elif len(digits) == 10:
        return f"+7{digits}"
    return raw_str if raw_str else None
