"""Robust JSON parsing utilities for LLM output."""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def robust_json_parse(text: str, default: Any = None) -> Any:
    """
    Robustly parse JSON from LLM output with multiple fallback strategies.

    Args:
        text: Raw text that may contain JSON
        default: Default value if all parsing fails

    Returns:
        Parsed JSON or default value
    """
    if not text or not text.strip():
        return default

    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        ...

    try:
        start_obj = cleaned.find('{')
        start_arr = cleaned.find('[')

        if start_obj == -1 and start_arr == -1:
            return default

        if start_obj == -1:
            start = start_arr
            end_char = ']'
        elif start_arr == -1:
            start = start_obj
            end_char = '}'
        else:
            start = min(start_obj, start_arr)
            end_char = '}' if start == start_obj else ']'

        end = cleaned.rfind(end_char)
        if end <= start:
            return default

        json_str = cleaned[start:end + 1]
        json_str = _repair_json_string(json_str)

        return json.loads(json_str)
    except json.JSONDecodeError:
        ...

    try:
        result = {}
        kv_pattern = r'"([^"]+)"\s*:\s*("([^"\\]|\\.)*"|[\d.]+|true|false|null)'
        matches = re.findall(kv_pattern, cleaned)
        for key, value, _ in matches:
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                result[key] = value.strip('"')
        if result:
            return result
    except Exception:
        ...

    return default


def _repair_json_string(json_str: str) -> str:
    """Repair common JSON syntax errors from LLM output."""
    result = []
    in_string = False
    escape_next = False

    for char in json_str:
        if escape_next:
            result.append(char)
            escape_next = False
            continue

        if char == '\\':
            result.append(char)
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            result.append(char)
            continue

        if in_string:
            if char == '\n':
                result.append('\\n')
            elif char == '\r':
                result.append('\\r')
            elif char == '\t':
                result.append('\\t')
            else:
                result.append(char)
        else:
            result.append(char)

    json_str = ''.join(result)
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

    if json_str.count('"') % 2 == 1:
        json_str = json_str + '"'

    return json_str
