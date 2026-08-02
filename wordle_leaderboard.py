#!/usr/bin/env python3
"""Wordle Leaderboard

Reads the macOS Messages database (~/Library/Messages/chat.db), extracts
Wordle scores shared in iMessage chats, and prints a monthly leaderboard.

Participant names and phone numbers live in config.json (never committed).
Run with --setup to create it interactively.
"""

import sqlite3
import re
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
EXAMPLE_CONFIG_PATH = SCRIPT_DIR / "config.example.json"

DEFAULT_DB_PATH = Path.home() / "Library/Messages/chat.db"

# Wordle score regex (matches e.g. "Wordle 765 3/6" and "Wordle 1,234 X/6")
WORDLE_REGEX = re.compile(r"Wordle\s+([\d,]+)\s+([X\d])/6", re.IGNORECASE)


def run_setup():
    """Interactively create config.json with the user's own participants."""
    print("Wordle Leaderboard setup")
    print("------------------------")
    my_name = input("Your name (used for messages you sent): ").strip() or "Me"
    name_map = {"Me": my_name}

    print("\nAdd participants. Enter each phone number exactly as it appears")
    print("in Messages (e.g. +15551234567). Leave blank to finish.\n")
    while True:
        phone = input("Phone number: ").strip()
        if not phone:
            break
        name = input(f"Name for {phone}: ").strip()
        if name:
            name_map[phone] = name

    config = {
        "name_map": name_map,
        "qualifying_games": 10,
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    print(f"\nSaved {CONFIG_PATH}")
    return config


def load_config():
    if not CONFIG_PATH.exists():
        if sys.stdin.isatty():
            print("No config.json found — let's create one.\n")
            return run_setup()
        sys.exit(
            "No config.json found. Run with --setup, or copy "
            "config.example.json to config.json and edit it."
        )
    try:
        config = json.loads(CONFIG_PATH.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"config.json is not valid JSON: {e}")
    if "name_map" not in config:
        sys.exit("config.json is missing the required \"name_map\" key.")
    return config


def get_month_range(months_ago=0):
    now = datetime.now()
    first_of_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    target_month = first_of_current
    for _ in range(months_ago):
        target_month = (target_month - timedelta(days=1)).replace(day=1)
    if target_month.month == 12:
        end_of_month = target_month.replace(year=target_month.year + 1, month=1)
    else:
        end_of_month = target_month.replace(month=target_month.month + 1)
    return target_month, end_of_month


def extract_wordle_scores(db_path, name_map, months_ago=0):
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT
            datetime(message.date / 1000000000 + strftime('%s','2001-01-01'), 'unixepoch') as msg_date,
            COALESCE(handle.id, 'Me') as sender,
            message.text
        FROM
            message
        LEFT JOIN
            handle ON message.handle_id = handle.ROWID
        WHERE
            message.text LIKE 'Wordle %'
        ORDER BY
            msg_date ASC;
        """)
        rows = cursor.fetchall()
        conn.close()
    except sqlite3.OperationalError as e:
        sys.exit(
            f"Could not read {db_path}: {e}\n"
            "On macOS, give your terminal Full Disk Access in "
            "System Settings → Privacy & Security."
        )

    wordle_data = []
    start_date, end_date = get_month_range(months_ago)

    for msg_date, sender, text in rows:
        match = WORDLE_REGEX.search(text)
        if match:
            date_obj = datetime.strptime(msg_date, "%Y-%m-%d %H:%M:%S")
            if date_obj < start_date or date_obj >= end_date:
                continue
            puzzle_num = int(match.group(1).replace(",", ""))
            score = match.group(2)
            score = 7 if score == 'X' else int(score)
            name = name_map.get(sender, sender)
            wordle_data.append({
                "date": msg_date,
                "sender": name,
                "puzzle": puzzle_num,
                "score": score,
            })

    return wordle_data, start_date, end_date


def build_leaderboard(data):
    scores = defaultdict(list)

    for entry in data:
        scores[entry["sender"].strip()].append(entry["score"])

    leaderboard = []
    for person, person_scores in scores.items():
        games = len(person_scores)
        fails = person_scores.count(7)
        best = min(person_scores)
        avg = sum(person_scores) / games

        leaderboard.append({
            "name": person,
            "games": games,
            "avg_score": round(avg, 2),
            "best": best,
            "fails": fails,
        })

    leaderboard.sort(key=lambda x: (x["avg_score"], -x["games"]))
    return leaderboard


def emoji_bar(avg_score, min_score=3.0, max_score=5.0, blocks=3):
    clamped = max(min_score, min(max_score, avg_score))
    filled = round(blocks * (max_score - clamped) / (max_score - min_score))
    return '🟩' * filled + '⬛' * (blocks - filled)


def print_leaderboard(leaderboard, month_label, qualifying_games):
    qualifying = [p for p in leaderboard if p["games"] >= qualifying_games]
    casual = [p for p in leaderboard if p["games"] < qualifying_games]

    name_width = max((len(p["name"]) for p in leaderboard), default=6)
    print(f"\n📊 Wordle Leaderboard — {month_label}\n")

    medals = ['🥇', '🥈', '🥉']

    for i, p in enumerate(qualifying):
        medal = medals[i] if i < 3 else '  '
        bar = emoji_bar(p["avg_score"])
        print(f"{medal} {p['name']:<{name_width}} {bar} {p['avg_score']:.2f} {p['games']}g")

    if casual:
        print("\n— Occasional Players —\n")
        for p in casual:
            bar = emoji_bar(p["avg_score"])
            print(f"   {p['name']:<{name_width}} {bar} {p['avg_score']:.2f} {p['games']}g")


def main():
    parser = argparse.ArgumentParser(
        description="Extract Wordle scores from Messages and build a leaderboard."
    )
    parser.add_argument(
        "-m", "--months-ago",
        type=int,
        default=0,
        help="How many months back to analyze (0=current month, 1=last month, etc.)"
    )
    parser.add_argument(
        "--last-month",
        action="store_true",
        help="Shortcut for --months-ago 1"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Interactively (re)create config.json"
    )
    args = parser.parse_args()

    if args.setup:
        run_setup()
        return

    config = load_config()
    name_map = config["name_map"]
    qualifying_games = config.get("qualifying_games", 10)
    db_path = Path(config.get("db_path") or DEFAULT_DB_PATH).expanduser()

    months_ago = 1 if args.last_month else args.months_ago

    data, start_date, _ = extract_wordle_scores(db_path, name_map, months_ago)

    if not data:
        print(f"No Wordle scores found for {start_date.strftime('%B %Y')}.")
        return

    leaderboard = build_leaderboard(data)
    print_leaderboard(leaderboard, start_date.strftime("%B %Y"), qualifying_games)


if __name__ == "__main__":
    main()
