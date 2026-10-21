"""Idempotently register the installed app in the native sites volume."""
from pathlib import Path

path = Path("sites/apps.txt")
lines = path.read_text().splitlines() if path.exists() else []
if "frappe_soca" not in lines:
    lines.append("frappe_soca")
path.write_text("\n".join(lines) + "\n")
