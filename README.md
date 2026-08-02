# Wordle Leaderboard

Turn your iMessage group chat's Wordle scores into a monthly leaderboard.

Reads the macOS Messages database (`~/Library/Messages/chat.db`) locally,
finds shared Wordle results (e.g. `Wordle 1,234 3/6`), and prints a
leaderboard with emoji bars:

```
📊 Wordle Leaderboard — July 2026

🥇 Alice  🟩🟩⬛ 3.90 22g
🥈 Bob    🟩🟩⬛ 3.94 31g
🥉 Carol  🟩⬛⬛ 4.04 24g

— Occasional Players —

   Dave   🟩🟩🟩 3.00 8g
```

Everything runs locally — no data leaves your machine. Your participants'
names and phone numbers live in `config.json`, which is gitignored.

## Requirements

- macOS (the script reads the Messages app's local database)
- Python 3 (standard library only — no dependencies to install)
- **Full Disk Access** for your terminal: System Settings → Privacy &
  Security → Full Disk Access. Without it, `chat.db` is unreadable.

## Setup

```bash
python3 wordle_leaderboard.py --setup
```

This interactively asks for your name and your friends' phone numbers and
writes `config.json`. Alternatively, copy `config.example.json` to
`config.json` and edit it:

```json
{
  "name_map": {
    "Me": "YourName",
    "+15551234567": "Alice"
  },
  "qualifying_games": 10,
  "db_path": null
}
```

- `name_map` — maps phone numbers (as they appear in Messages) to display
  names. `"Me"` is your own messages. Unmapped senders show as their raw
  phone number.
- `qualifying_games` — minimum games per month to rank in the main list;
  players below it appear under "Occasional Players".
- `db_path` — leave `null` to use `~/Library/Messages/chat.db`, or set a
  path to read a copy of the database.

## Usage

```bash
python3 wordle_leaderboard.py               # current month
python3 wordle_leaderboard.py --last-month  # last month
python3 wordle_leaderboard.py -m 2          # two months ago
```

## How scoring works

- Each `N/6` result counts as `N`; a failed puzzle (`X/6`) counts as 7.
- Players are ranked by average score (lower is better), ties broken by
  most games played.
- The emoji bar maps the average onto a 3.0–5.0 range (full bar = 3.0
  average or better).
