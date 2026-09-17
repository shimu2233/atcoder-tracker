import re


EVERGREEN_CONTENTS = {
    "practice": "practice contest",
    "APG4b": "C++入門 APG4b",
    "APG4bPython": "Python入門 APG4bPython",
    "abs": "AtCoder Beginners Selection",
    "practice2": "AtCoder Library Practice Contest",
    "typical90": "競プロ典型90問",
    "math-and-algorithm": "アルゴリズムと数学 演習問題集",
    "tessoku-book": "競技プログラミングの鉄則",
}

SERIES_LABELS = {
    "ABC": "ABC",
    "ARC": "ARC",
    "AGC": "AGC",
    "AHC": "AHC",
    "HEURISTIC_OTHER": "AHC形式（AHC以外）",
    "ADT": "AtCoder Daily Training",
    "AWC": "AtCoder Weekday Contest",
    "PAST": "PAST",
    "JOI": "JOI",
    "JAG": "JAG",
    "LEARNING": "常設教材",
    "OTHER": "その他",
}

SERIES_ORDER = [
    "ABC",
    "ARC",
    "AGC",
    "AHC",
    "HEURISTIC_OTHER",
    "AWC",
    "PAST",
    "JOI",
    "JAG",
    "OTHER",
]


def classify_contest(contest_id, heuristic_contest_ids=None):
    """Return (series, format, is_evergreen) for an AtCoder contest ID."""
    heuristic_contest_ids = heuristic_contest_ids or set()

    if contest_id in EVERGREEN_CONTENTS:
        return "LEARNING", "ALGORITHM", True
    if re.fullmatch(r"abc\d{3}", contest_id):
        return "ABC", "ALGORITHM", False
    if re.fullmatch(r"arc\d{3}", contest_id):
        return "ARC", "ALGORITHM", False
    if re.fullmatch(r"agc\d{3}", contest_id):
        return "AGC", "ALGORITHM", False
    if re.fullmatch(r"ahc\d{3}", contest_id):
        return "AHC", "HEURISTIC", False
    if contest_id in heuristic_contest_ids:
        return "HEURISTIC_OTHER", "HEURISTIC", False
    if re.fullmatch(
        r"adt_(easy|medium|hard|all)_\d{8}_[1-9]\d*", contest_id
    ):
        return "ADT", "ALGORITHM", False
    if re.fullmatch(r"awc\d{4}", contest_id):
        return "AWC", "ALGORITHM", False
    if contest_id.startswith("past"):
        return "PAST", "ALGORITHM", False
    if contest_id.startswith("joi"):
        return "JOI", "ALGORITHM", False
    if re.match(r"^(jag|JAG)", contest_id):
        return "JAG", "ALGORITHM", False
    return "OTHER", "ALGORITHM", False


def tessoku_section(problem_index):
    match = re.fullmatch(r"([ABC])\d+", problem_index)
    return match.group(1) if match else "OTHER"
