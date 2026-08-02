# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Python script that reads the macOS Messages SQLite database (`~/Library/Messages/chat.db`) to extract Wordle scores shared in iMessage chats and print a monthly leaderboard.

No external dependencies — stdlib only (`sqlite3`, `re`, `json`, `datetime`, `collections`).

## Running

```bash
python3 wordle_leaderboard.py --setup       # interactively create config.json
python3 wordle_leaderboard.py               # current month
python3 wordle_leaderboard.py --last-month  # last month
python3 wordle_leaderboard.py -m 2          # two months ago
```

**macOS requirement:** The terminal (or IDE) running this script must have Full Disk Access permission in System Settings → Privacy & Security, otherwise `chat.db` will be unreadable.

## Architecture

- `wordle_leaderboard.py` — the entire app. Extracts scores from `chat.db`, builds the leaderboard, prints it with emoji bars (3 🟩⬛ blocks scaled to the 3.0–5.0 avg range), and splits players into qualifying and Occasional Players sections based on `qualifying_games`.
- `config.json` — per-user private config, **gitignored, never commit it**. Holds `name_map` (phone number → display name, with `"Me"` for the local user), `qualifying_games`, and optional `db_path`. `config.example.json` is the committed template.
- Legacy untracked files may exist in local working copies (`extract_wordle_scores*.py`, `WordleScoreScraper.py`, `old_versions/`, `wordle_leaderboard.png`); they contain hardcoded personal data and are excluded via `.gitignore`. Do not commit them or copy their `NAME_MAP` contents into tracked files.

### Key design decisions

- All personal data (names, phone numbers) lives only in `config.json`. Tracked files must never contain real participant info — use placeholder data like `+15551234567` in examples and docs.
- Candidate messages are prefiltered in SQL with `message.text LIKE 'Wordle %'`, then parsed in Python with `WORDLE_REGEX = r"Wordle\s+([\d,]+)\s+([X\d])/6"` (case-insensitive, handles comma-formatted puzzle numbers like "1,234"). Date filtering also happens in Python, not SQL.
- Failed puzzles (`X/6`) are stored as score `7` so they sort to the bottom and inflate the average naturally.
- `COALESCE(handle.id, 'Me')` captures the local user's own messages, which have no `handle_id`.
- The database is opened read-only (`file:...?mode=ro`) so the script can never touch Messages data.
- Messages timestamp uses Apple's epoch: `date / 1000000000 + strftime('%s','2001-01-01')`.
- Leaderboard sorts by `(avg_score ASC, games_played DESC)` — lower average is better, ties broken by most games played.
- If `config.json` is missing, an interactive terminal launches setup automatically; a non-interactive run exits with instructions instead.
