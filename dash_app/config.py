import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()


def read_secret_file(path: str) -> str:
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8") as secret_file:
            return secret_file.read().strip()
    except OSError:
        return ""


DATABASE_URL = os.getenv("DATABASE_URL") or read_secret_file(os.getenv("DATABASE_URL_FILE", ""))
CHALLENGE_START = date(2026, 5, 4)
CHALLENGE_END = date(2026, 7, 26)
REVIEW_GATES = [date(2026, 5, 31), date(2026, 6, 28), date(2026, 7, 26)]
STEP_GOAL = 8_000
PROTEIN_GOAL_G = 150
HYDRATION_GOAL_L = 3.0
