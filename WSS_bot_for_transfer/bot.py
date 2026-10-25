"""Discord-бот: панель с выбором услуги и приватные тикеты.

Все тексты, услуги, цены и баннер лежат в config.json.
Токен берётся из переменной окружения DISCORD_TOKEN или из файла .env.
"""

import asyncio
import io
import json
import os
import re
import time
from pathlib import Path

import discord
from discord import app_commands, ui

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
DATA_PATH = BASE_DIR / "data" / "users.json"

# ---------------------------------------------------------------- config / data

_config_cache = {"mtime": None, "data": None}


def cfg() -> dict:
    """Читает config.json заново, если файл изменился (перезапуск не нужен)."""
    mtime = CONFIG_PATH.stat().st_mtime
    if _config_cache["mtime"] != mtime:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            _config_cache["data"] = json.load(f)
        _config_cache["mtime"] = mtime
    return _config_cache["data"]


def load_users() -> dict:
    if DATA_PATH.exists():
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_user(user_id: int, **fields):
    users = load_users()
    users.setdefault(str(user_id), {}).update(fields)
    DATA_PATH.parent.mkdir(exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def load_token() -> str:
    token = os.getenv("DISCORD_TOKEN")
    env_file = BASE_DIR / ".env"
    if not token and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DISCORD_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not token:
        raise SystemExit("No token: create a .env file with the line DISCORD_TOKEN=... (see README)")
    return token


def accent() -> discord.Colour:
    return discord.Colour(int(cfg().get("accent_color", "#5865F2").lstrip("#"), 16))


def get_service(service_id: str) -> dict | None:
    return next((s for s in cfg()["services"] if s["id"] == service_id), None)


def get_payment(method_id: str) -> dict | None:
    return next((m for m in cfg()["payment_methods"] if m["id"] == method_id), None)


def is_staff(member: discord.Member) -> bool:
    role_id = cfg().get("staff_role_id")
    return member.guild_permissions.administrator or any(r.id == role_id for r in member.roles)


# ---------------------------------------------------------------- panel

def build_panel() -> tuple[ui.LayoutView, discord.File | None]:
    """Собирает панель в стиле Components V2 из config.json."""
    c = cfg()
    p = c["panel"]
    view = ui.LayoutView(timeout=None)
    box = ui.Container(accent_colour=accent())
    file = None

    banner = p.get("banner", "")
    if banner:
        if banner.startswith("http"):
            box.add_item(ui.MediaGallery(discord.MediaGalleryItem(banner)))
        elif (BASE_DIR / banner).exists():
            # Локальная картинка рядом с bot.py, например banner.png
            file = discord.File(BASE_DIR / banner, filename="banner" + Path(banner).suffix)
            box.add_item(ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{file.filename}")))

    box.add_item(ui.TextDisplay(f"## {p['title']}\n{p['subtitle']}"))
    box.add_item(ui.Separator())

    for sec in p["sections"]:
        btn = sec.get("button")
        if not btn:
            box.add_item(ui.TextDisplay(sec["text"]))
            continue
        if btn["type"] == "link":
            accessory = ui.Button(label=btn["label"], emoji=btn.get("emoji"), url=btn["url"])
        elif btn["type"] == "payments":
            accessory = ui.Button(label=btn["label"], emoji=btn.get("emoji"), custom_id="panel:payments")
        else:
            accessory = ui.Button(label=btn["label"], emoji=btn.get("emoji"), custom_id=f"panel:info:{btn['id']}")
        box.add_item(ui.Section(sec["text"], accessory=accessory))

    box.add_item(ui.Separator())
    box.add_item(ui.TextDisplay(f"## {p['services_title']}"))

    # Кнопки услуг, по 5 в ряд (ограничение Discord)
    services = c["services"]
    for i in range(0, len(services), 5):
        row = ui.ActionRow()
        for s in services[i:i + 5]:
            row.add_item(ui.Button(label=s["name"], emoji=s.get("emoji"), custom_id=f"panel:svc:{s['id']}"))
        box.add_item(row)

    box.add_item(ui.Separator())
        box.add_item(ui.Separator())
    box.add_item(
        ui.ActionRow(
            ui.Button(
                label=p["fast_button_label"],
                emoji="⚡",
                style=discord.ButtonStyle.success,
                custom_id="panel:order:fast",
            ),
            ui.Button(
                label=p["bulk_button_label"],
                emoji="📦",
                custom_id="panel:order:bulk",
            ),
        )
    )
