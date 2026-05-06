from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import streamlit as st
from streamlit_js_eval import streamlit_js_eval


def get_browser_context() -> tuple[str, datetime]:
    browser_timezone = streamlit_js_eval(
        js_expressions="Intl.DateTimeFormat().resolvedOptions().timeZone",
        key="browser_timezone",
    ) or "UTC"
    browser_now_iso = streamlit_js_eval(
        js_expressions="new Date().toISOString()",
        key="browser_now_iso",
    )

    try:
        tzinfo = ZoneInfo(browser_timezone)
    except Exception:
        browser_timezone = "UTC"
        tzinfo = ZoneInfo("UTC")

    if browser_now_iso:
        try:
            browser_now = datetime.fromisoformat(browser_now_iso.replace("Z", "+00:00")).astimezone(tzinfo)
        except ValueError:
            browser_now = datetime.now(timezone.utc).astimezone(tzinfo)
    else:
        browser_now = datetime.now(timezone.utc).astimezone(tzinfo)

    return browser_timezone, browser_now


def add_local_time_column(frame, source_col: str, target_col: str, timezone_name: str, errors: str = "raise"):
    frame[target_col] = __import__('pandas').to_datetime(
        frame[source_col], utc=True, errors=errors
    ).dt.tz_convert(timezone_name)
    return frame
