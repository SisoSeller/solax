"""Copy .bat attachments from the Discord plugin channel into the public store."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANNEL_ID = "1539741772035522681"
API = "https://discord.com/api/v10"
MAX_BYTES = 200 * 1024
UA = "SolaXStore (https://github.com/SisoSeller/solax, 1.1)"
STORE_DIRS = [ROOT / "docs" / "store", ROOT / "website" / "store"]
STORE_JSON = [ROOT / "docs" / "store.json", ROOT / "website" / "store.json"]
CDN_HOSTS = {"cdn.discordapp.com", "media.discordapp.net"}


def slugify(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
    return text or "plugin"


def parse_price(text: str) -> int:
    t = (text or "").lower()
    match = re.search(r"(?:€\s*|eur\s*)(\d{1,2})|(\d{1,2})\s*(?:€|eur)", t)
    if match:
        return max(0, min(20, int(match.group(1) or match.group(2))))
    return 0


def api_get(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": UA,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_bat(url: str, dest: Path) -> None:
    host = urllib.parse.urlparse(url).hostname or ""
    if host not in CDN_HOSTS:
        raise ValueError("host non consentito")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("file troppo grande")
    if b"\x00" in data:
        raise ValueError("file non valido")
    dest.write_bytes(data)


def load_catalog() -> dict:
    path = STORE_JSON[0]
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("plugins"), list):
            return data
    return {"plugins": []}


def save_catalog(catalog: dict) -> None:
    text = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    for path in STORE_JSON:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def notify(webhook: str, name: str) -> None:
    if not webhook:
        return
    payload = json.dumps(
        {
            "username": "SolaX",
            "content": f"Plugin **{name}** è online: https://sisoseller.github.io/solax/plugins.html",
            "allowed_mentions": {"parse": []},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=20).read()
    except Exception:
        pass


def fetch_messages(token: str) -> list:
    messages: list = []
    before = None
    for _ in range(4):
        url = f"{API}/channels/{CHANNEL_ID}/messages?limit=50"
        if before:
            url += f"&before={before}"
        try:
            batch = api_get(url, token)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Discord {exc.code}: {detail[:300]}") from exc
        if not isinstance(batch, list) or not batch:
            break
        messages.extend(batch)
        before = batch[-1]["id"]
        if len(batch) < 50:
            break
    return messages


def main() -> int:
    token = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
    webhook = (os.environ.get("DISCORD_PLUGIN_WEBHOOK") or "").strip()
    if not token:
        print("skip: DISCORD_BOT_TOKEN secret is empty")
        return 0
    catalog = load_catalog()
    plugins = list(catalog.get("plugins") or [])
    seen_msg = {str(item.get("discord_message_id")) for item in plugins if item.get("discord_message_id")}
    added: list[str] = []
    for msg in reversed(fetch_messages(token)):
        mid = str(msg.get("id") or "")
        if mid and mid in seen_msg:
            continue
        content = str(msg.get("content") or "").strip()
        for att in msg.get("attachments") or []:
            filename = str(att.get("filename") or "")
            if not filename.lower().endswith(".bat"):
                continue
            pid = slugify(Path(filename).stem)
            url = str(att.get("url") or "")
            size = int(att.get("size") or 0)
            if size > MAX_BYTES:
                print(f"skip {filename}: too large")
                continue
            safe_file = f"{pid}.bat"
            try:
                for folder in STORE_DIRS:
                    folder.mkdir(parents=True, exist_ok=True)
                    download_bat(url, folder / safe_file)
            except Exception as exc:
                print(f"skip {filename}: {exc}")
                continue
            desc = re.sub(r"https?://\S+", "", content).strip()[:280] or "Plugin SolaX."
            plugin = {
                "id": pid,
                "name": Path(filename).stem.replace("_", " ").strip() or pid,
                "description": desc,
                "price": parse_price(content),
                "file": safe_file,
                "discord_message_id": mid,
            }
            plugins = [item for item in plugins if item.get("id") != pid]
            plugins.append(plugin)
            if mid:
                seen_msg.add(mid)
            added.append(plugin["name"])
            break
    plugins.sort(key=lambda item: str(item.get("discord_message_id") or ""), reverse=True)
    catalog["plugins"] = plugins
    save_catalog(catalog)
    for name in added:
        notify(webhook, name)
        print(f"added {name}")
    if not added:
        print("no new .bat plugins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
