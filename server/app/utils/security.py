"""
Security utilities.
"""

from datetime import timedelta
from typing import Optional


def sanitize_input(input_string: str) -> str:
    """Basic input sanitization."""
    if not isinstance(input_string, str):
        return ""

    # Remove potential dangerous characters
    dangerous_chars = ["<", ">", "&", '"', "'", "/", "\\"]
    sanitized = input_string
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    return sanitized.strip()
