"""
Reusable field types with validation built in.
"""

from typing import Annotated

from pydantic import AfterValidator, StringConstraints

from app.core.security import normalize_pakistan_phone

PakistanPhone = Annotated[str, AfterValidator(normalize_pakistan_phone)]
"""Accepts 03001234567 / +92 300 1234567 / 923001234567 and stores +923001234567."""

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
