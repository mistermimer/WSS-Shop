"""Ставит avatar.png (или .jpg) из этой папки аватаркой бота. Запуск: python set_avatar.py"""

import base64
import json
import urllib.request
from pathlib import Path

from bot import BASE_DIR, load_token

img = next((BASE_DIR / n for n in ("avatar.png", "avatar.jpg", "avatar.jpeg") if (BASE_DIR / n).exists()), None)
if img is None:
    raise SystemExit("Put avatar.png next to bot.py")
mime = "image/png" if img.suffix == ".png" else "image/jpeg"
data = f"data:{mime};base64," + base64.b64encode(img.read_bytes()).decode()
req = urllib.request.Request(
    "https://discord.com/api/v10/users/@me", method="PATCH",
    data=json.dumps({"avatar": data}).encode(),
    headers={"Authorization": "Bot " + load_token(), "Content-Type": "application/json",
             "User-Agent": "DiscordBot (setup, 1.0)"})
print("Avatar set for", json.load(urllib.request.urlopen(req))["username"])
