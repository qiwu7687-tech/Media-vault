# 🎬 MediaVault

**Automated media library manager for Quark cloud drive — organize, classify, and manage your collection for Infuse / Plex / Jellyfin.**

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License MIT">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
</p>

---

## ✨ Features

- 📁 **Media library organizer** — Auto-organize files into Infuse / Plex / Jellyfin compatible structure
- 🎭 **Auto-classify** — Genre detection via OMDB API (optional); fallback to `--genre` manual override
- 🏷️ **Smart renaming** — Detect scene naming conventions, clean up messy filenames
- ☁️ **Cloud drive management** — Folder creation, file move/rename on Quark cloud drive
- 🔌 **Pluggable search** — Bring your own content sources via a simple plugin interface
- 📊 **Quality scoring** — Auto-rank by resolution, source, HDR, audio, codec

> 💡 The core value is **library management**. Search is an optional plugin — use the built-in plugins, write your own, or skip search entirely and manage existing files.

---

## 🚀 3-Minute Quick Start

```bash
# 1. Clone
git clone https://github.com/qiwu7687-tech/Media-vault.git
cd media-vault

# 2. Install (registers 'mediavault' command globally)
pip install .

# 3. First-run setup
mediavault init

# 4. Manage your library
mediavault organize <file_id> "Movie Name"
```

> 💡 Read below for plugin-based search if you need to discover new content.

---

## 📖 Usage

### Library Management (Core)

```bash
# Organize a single file into the library
$ mediavault organize <file_id> "天空之鱼"

Genre: 冒险
📁 已归档: 夸克影视/电影/冒险/天空之鱼 (2031)

# Organize a TV show
$ mediavault organize <file_id> "王国的纷争" --type tv --season 1 --episode 1
📁 已归档: 夸克影视/电视剧/奇幻/王国的纷争/Season 01
```

### Plugin-based Search (Optional)

```bash
# Search using configured plugins
$ mediavault search "天空之鱼"

找到 32 个结果，按评分排序：

  #   评分   画质   来源   标题
  ─── ───── ────── ────── ──────────────────────────────────
  1   150   4k     夸克   Sky Fish 2031 2160p REMUX HDR Atmos
  2   102   1080p  夸克   天空之鱼 2031 BluRay 1080p x265
  ...

# Save the one you want
$ mediavault save 1
✅ 保存成功！📁 已归档: 夸克影视/电影/冒险/天空之鱼 (2031)
```

### All Commands

| Command | Description |
|---------|-------------|
| `mediavault init` | First-run setup wizard |
| `mediavault organize <fid> <title>` | Organize file into media library |
| `mediavault organize <fid> <title> --genre 纪录片` | Organize with manual genre override |
| `mediavault search <query>` | Search via plugins, show scored table |
| `mediavault save <N>` | Save result #N from last search |
| `mediavault auto <query>` | Search + save + organize in one step |
| `mediavault auto <query> --genre 科幻` | Auto mode with manual genre |
| `mediavault login` | Authenticate with Quark cloud drive |
| `mediavault plugins` | List enabled plugins |

---

## 📁 Media Library Structure

Automatically organized for Infuse / Plex / Jellyfin:

```
夸克影视/
├── 电影/
│   ├── 动作/
│   │   └── 影子计划 (2032)/
│   │       └── Shadow.Plan.2032.2160p.WEB-DL.mkv
│   ├── 科幻/
│   │   └── 银河漫游 (2033)/
│   │       └── Galaxy.Voyage.2033.2160p.IMAX.mkv
│   └── 冒险/
│       └── 天空之鱼 (2031)/
│           └── Sky.Fish.2031.2160p.REMUX.mkv
├── 电视剧/
│   ├── 剧情/
│   │   └── 夏日回忆 (2034)/
│   │       └── Season 01/
│   └── 奇幻/
│       └── 王国的纷争 (2035)/
```

---

## 🔌 Plugin System

The built-in plugins demonstrate the interface. You can write your own, or use none at all — the library management features work independently.

| Plugin | Type | Setup |
|--------|------|-------|
| **PanSou** | Self-hosted aggregator | `docker compose up -d` |
| **365WP** | Online aggregator | No setup |

### Write Your Own Plugin

```bash
cp scripts/plugins/example.py scripts/plugins/your_source.py
```

```python
from plugins import ResourcePlugin, ResourceResult

class Plugin(ResourcePlugin):
    name = "your_source"
    display_name = "Your Content Source"

    def search(self, query: str, page: int = 1) -> list[ResourceResult]:
        # Return list of ResourceResult
        ...

    def extract_link(self, resource: ResourceResult) -> str | None:
        # Return Quark share URL or None
        ...
```

Enable in `config.json`: `"your_source": {"enabled": true}`

---

## 🏗️ Architecture

Each layer is independent — extend or replace any part without touching the rest.

```
┌─────────────────────────────────────┐
│              CLI (mediavault)            │  ← Unified interface
├─────────────────────────────────────┤
│  Search Plugins  │   Library Manager │  ← Independent modules
│  (pansou/wp365)  │   (organize/genre)│
├─────────────────────────────────────┤
│         Storage Provider             │  ← Currently: Quark
│         (quark.py)                   │     Future: AliDrive / 115 / Baidu
├─────────────────────────────────────┤
│         Metadata (OMDB)              │  ← Optional enrichment
└─────────────────────────────────────┘
```

To add a new storage provider (AliDrive, 115, Baidu Netdisk), implement the same interface as `quark.py`. To add a metadata source (Douban, TMDB), extend `library.py`. Plugin interface is defined in `plugins/__init__.py`.

---

## OMDB API (Optional)

MediaVault can use OMDB to auto-detect genres for better classification. Example: `Sky Fish` → Adventure → `电影/冒险/Sky Fish (2031)`.

**Without it:** search, save, and organize all work. Movies just go to a default folder, or use `--genre` to specify manually.

**Get a free key (30 seconds):**
1. Visit [omdbapi.com/apikey.aspx](http://www.omdbapi.com/apikey.aspx)
2. Choose **FREE** tier (1000 req/day)
3. Enter your email → receive key → paste into `mediavault init`

---

## ⚠️ Disclaimer

See [DISCLAIMER.md](DISCLAIMER.md) for full details. In short: this is a **media library manager** — it does not provide, host, or distribute any content. Users are responsible for their own usage.

This tool is a **media library manager** — it organizes files that you already have access to. The plugin system is an extensibility interface that users configure at their own discretion.

- This project does **not** provide, host, or distribute any media content.
- Users are responsible for complying with applicable laws in their jurisdiction.
- Plugin-based search features should only be used to access content that you have the right to access.
- The developers are not responsible for how users configure or use the plugin system.

---

## ❓ FAQ

**Q: Do I need the search plugins?**
A: No. The library management features (organize, rename, classify) work without any plugins. Search is entirely optional.

**Q: How does Quark integration work?**
A: `mediavault login` shows a QR code — scan with the Quark App. The tool manages folders and files via the official Quark API.

**Q: Cookie expires?**
A: Auto-detected — the tool prompts you to re-scan when needed.

---

## 📄 License

MIT — use it, fork it, share it.
