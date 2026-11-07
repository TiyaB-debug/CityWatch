"""Rank locations by cyclist injury counts in recent history."""

HISTORY_WINDOWS = {"13-week baseline": "injury_13", "52-week baseline": "injury_52"}


def add_scores(rows):
    for name, column in HISTORY_WINDOWS.items():
        rows[name] = rows[column]
