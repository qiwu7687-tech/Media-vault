#!/usr/bin/env python3
"""
MediaVault — Automated media library manager for Quark cloud drive.
Organize, classify, and manage your collection for Infuse/Plex/Jellyfin.

Usage:
    mediavault init                        First-run setup wizard
    mediavault organize <fid> <title>      Organize file into media library (core)
    mediavault search <query>              Plugin-based search (optional)
    mediavault save <N>                    Save result #N from last search
    mediavault auto <query> [--type tv]    Search + save + organize in one step

Options:
    --type movie|tv        Content type
    --genre <genre>        Genre override (e.g. 纪录片, 科幻)
    --folder <name>        Quark cloud folder name
    --season N --episode N TV season/episode numbers
    mediavault login                       Quark cloud drive authentication
    mediavault plugins                     List enabled plugins

Examples:
    mediavault init
    mediavault search "天空之鱼"
    mediavault save 1
    mediavault auto "银河漫游"
    mediavault auto "王国的纷争" --type tv
"""

import json
import os
import sys
import importlib
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from plugins import ResourcePlugin, ResourceResult
from quark import QuarkClient
from library import LibraryManager

CONFIG_PATH = PROJECT_DIR / "config.json"
EXAMPLE_CONFIG_PATH = PROJECT_DIR / "config.example.json"
LAST_SEARCH_CACHE = PROJECT_DIR / ".cache" / "last_search.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    if EXAMPLE_CONFIG_PATH.exists():
        with open(EXAMPLE_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "quark": {"username": "", "password": "", "cookie": ""},
        "plugins": {"wp365": {"enabled": True}},
        "save_folder": "夸克影视",
        "omdb_api_key": "",
    }


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_plugins(config: dict) -> list:
    plugins = []
    plugin_configs = config.get("plugins", {})
    plugin_dir = SCRIPT_DIR / "plugins"

    for f in sorted(plugin_dir.glob("*.py")):
        if f.name.startswith("_") or f.name == "base.py":
            continue
        module_name = f.stem
        plugin_conf = plugin_configs.get(module_name, {})
        default_enabled = False if module_name == "example" else True
        if not plugin_conf.get("enabled", default_enabled):
            continue
        try:
            mod = importlib.import_module(f"plugins.{module_name}")
            if hasattr(mod, "Plugin"):
                plugins.append(mod.Plugin(config=plugin_conf))
        except Exception as e:
            print(f"  ⚠️  Failed to load plugin {module_name}: {e}", file=sys.stderr)

    return plugins


def check_cookie_health(config: dict) -> bool:
    """Check if Quark cookie is still valid. Returns True if valid."""
    quark_conf = config.get("quark", {})
    if not quark_conf.get("cookie"):
        print("❌ 未检测到夸克登录信息", file=sys.stderr)
        print("   运行: mediavault login", file=sys.stderr)
        return False
    client = QuarkClient(cookie=quark_conf.get("cookie", ""))
    if client.check_cookie():
        return True
    print("⚠️  夸克 Cookie 已过期！", file=sys.stderr)
    choice = input("是否重新登录？[Y/n]: ").strip().lower()
    if choice in ("", "y", "yes"):
        if client.qr_login():
            config["quark"]["cookie"] = client.cookie
            save_config(config)
            return True
    print("   手动运行 mediavault login 重新登录", file=sys.stderr)
    return False


def get_quark_client(config: dict) -> QuarkClient:
    quark_conf = config.get("quark", {})
    client = QuarkClient(
        username=quark_conf.get("username", ""),
        password=quark_conf.get("password", ""),
        cookie=quark_conf.get("cookie", ""),
    )
    return client


# ── Quality Scoring ──

QUALITY_SCORES = {"2160p": 100, "4k": 100, "uhd": 100, "1080p": 50, "1080i": 45, "720p": 20, "480p": 5}
SOURCE_SCORES = {"bluray": 90, "remux": 85, "bdrip": 80, "web-dl": 70, "webdl": 70, "webrip": 65, "hdtv": 40, "cam": 5}
HDR_SCORES = {"dolby.vision": 30, "dv": 30, "hdr10+": 25, "hdr10": 20, "hdr": 15}
AUDIO_SCORES = {"atmos": 15, "truehd": 12, "dts-hd": 10, "dts": 8, "eac3": 7, "ddp": 7, "ac3": 3, "aac": 2}
CODEC_SCORES = {"h265": 10, "hevc": 10, "x265": 10, "h264": 5, "x264": 5}
SUB_KW = ["字幕", "subtitle", "chs", "cht", "中英", "中字", "双语"]


def score_resource(res: ResourceResult) -> int:
    t = res.title.lower()
    s = 0
    for table in [QUALITY_SCORES, SOURCE_SCORES, HDR_SCORES, AUDIO_SCORES, CODEC_SCORES]:
        for k, v in table.items():
            if k in t:
                s += v
                break
    if any(kw in t for kw in SUB_KW):
        s += 5
    if res.source == "quark":
        s += 15
    return s


def _detect_quality(res: ResourceResult) -> str:
    """Detect brief quality label for display."""
    t = res.title.lower()
    for tag in ["2160p", "4k", "uhd", "1080p", "720p", "480p"]:
        if tag in t:
            return tag.upper().replace("P", "p").replace("K", "k")
    return "-"


def _detect_content_type(query: str) -> str:
    """Auto-detect if the query is a TV show or movie."""
    import re
    tv_patterns = [r'S\d{2}', r'E\d{2}', r'第\s*\d+\s*[集季]', r'[全共]\d+[集季]', r'season', r'series']
    for p in tv_patterns:
        if re.search(p, query, re.I):
            return "tv"
    return "movie"


# ── Commands ──

def cmd_init(config: dict):
    """Interactive first-run setup wizard."""
    print()
    print("=" * 50)
    print("  🎬 MediaVault — 首次配置向导")
    print("=" * 50)
    print()

    # Step 1: Quark login
    print("📁 第一步：夸克网盘登录")
    print()
    print("  夸克网盘用于保存影视文件。需要登录后才能使用。")
    print()
    print("  [1] 扫码登录（推荐）— 终端显示二维码，夸克 App 一扫即可")
    print("  [2] 手动输入 Cookie — 从浏览器复制，约 7 天过期")
    print()

    cookie_set = False
    while not cookie_set:
        choice = _safe_input("选择登录方式 [1/2] (默认 1): ").strip() or "1"
        if choice == "1":
            print()
            print("  正在获取二维码...")
            print()
            client = QuarkClient()
            if client.qr_login():
                config["quark"] = config.get("quark", {})
                config["quark"]["cookie"] = client.cookie
                config["quark"]["username"] = ""
                config["quark"]["password"] = ""
                cookie_set = True
            else:
                print()
                print("  ⚠️  扫码登录失败（可能网络问题或夸克 API 变动）。")
                print("  试试方式 2：手动输入 Cookie。")
                print()
        elif choice == "2":
            print()
            print("  获取 Cookie 的步骤：")
            print("  1. 浏览器打开 https://pan.quark.cn 并登录")
            print("  2. 按 F12 → Application → Cookies → pan.quark.cn")
            print("  3. 复制所有 Cookie 内容，粘贴到下面")
            print()
            cookie = _safe_input("Cookie: ").strip()
            if cookie:
                config["quark"] = config.get("quark", {})
                config["quark"]["cookie"] = cookie
                config["quark"]["username"] = ""
                config["quark"]["password"] = ""
                print("  ✅ Cookie 已保存")
                cookie_set = True
            else:
                print("  ⚠️  Cookie 为空，请重试或选择扫码登录。")
                print()
        else:
            print("  请输入 1 或 2")
    print()

    # Step 2: Search engines
    print("-" * 50)
    print("🔍 第二步：搜索引擎配置")
    print()
    print("  [1] PanSou — 自建搜索引擎，18个搜索源，速度快")
    print("      需要 Docker: docker run -d --name pansou -p 8888:8888 ghcr.io/fish2018/pansou:latest")
    print()
    print("  [2] 365聚合资源站 — 免费在线搜索，无需额外配置")
    print()

    if "plugins" not in config:
        config["plugins"] = {}

    choice = input("启用 PanSou？需要本地 Docker [y/N]: ").strip().lower()
    config["plugins"]["pansou"] = {
        "enabled": choice in ("y", "yes"),
        "endpoint": "http://localhost:8888",
        "timeout": 15,
    }

    choice = input("启用 365聚合资源站？免费无需配置 [Y/n]: ").strip().lower()
    config["plugins"]["wp365"] = {"enabled": choice in ("", "y", "yes")}

    # Step 3: OMDB
    print("-" * 50)
    print("🎭 第三步：自动分类（可选）")
    print()
    print("  通过 OMDB API 自动识别电影类型（动作/科幻/剧情...）")
    print("  免费，每天 1000 次。在 https://www.omdbapi.com/apikey.aspx 获取 Key。")
    print()

    omdb_key = _safe_input("OMDB API Key（可选，用于自动识别电影类型，直接回车跳过）: ").strip()
    config["omdb_api_key"] = omdb_key

    # Step 4: Save folder
    print("-" * 50)
    print("📂 第四步：保存目录")
    print()

    folder = input(f"夸克网盘中的保存文件夹名 [{config.get('save_folder', '夸克影视')}]: ").strip()
    if folder:
        config["save_folder"] = folder
    elif "save_folder" not in config:
        config["save_folder"] = "夸克影视"

    # Save
    save_config(config)

    print()
    print("=" * 50)
    print("  ✅ 配置完成！")
    print()
    print("  试试看：")
    print(f"    mediavault search \"天空之鱼\"")
    print(f"    mediavault auto \"银河漫游\"")
    print()
    print("  其他命令：")
    print("    mediavault login    — 重新登录夸克")
    print("    mediavault plugins  — 查看搜索引擎")
    print("    mediavault --help   — 查看所有命令")
    print("=" * 50)
    print()


def cmd_search(query: str, config: dict):
    """Search and display results table. Caches results for 'save N'."""
    plugins = load_plugins(config)
    if not plugins:
        print("❌ 没有启用的搜索引擎。运行 mediavault init 配置。")
        return

    all_results = []
    for plugin in plugins:
        print(f"🔍 正在搜索 {plugin.display_name}...", file=sys.stderr)
        try:
            results = plugin.search(query)
            for r in results:
                r.site = plugin.name
                r.extra["score"] = score_resource(r)
            all_results.extend(results)
        except Exception as e:
            print(f"  ⚠️  {plugin.name} 出错: {e}", file=sys.stderr)

    if not all_results:
        print("❌ 未找到任何资源，换个关键词试试？")
        return

    # Sort by score
    all_results.sort(key=lambda r: r.extra.get("score", 0), reverse=True)

    # Cache results for 'save N'
    LAST_SEARCH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    LAST_SEARCH_CACHE.write_text(json.dumps([
        {"title": r.title, "source": r.source, "site": r.site,
         "score": r.extra.get("score", 0), "url": r.url,
         "extra": r.extra}
        for r in all_results[:20]
    ], ensure_ascii=False, indent=2), encoding='utf-8')

    # Display table
    print()
    print(f"找到 {len(all_results)} 个资源，按评分排序：")
    print()
    print(f"  {'#':<3} {'评分':<5} {'画质':<6} {'类型':<6} {'标题'}")
    print(f"  {'─'*3} {'─'*5} {'─'*6} {'─'*6} {'─'*50}")

    for i, r in enumerate(all_results[:20], 1):
        quality = _detect_quality(r)
        source_tag = "夸克" if r.source == "quark" else r.source.upper()
        title = r.title[:55] + "..." if len(r.title) > 55 else r.title
        score = r.extra.get("score", 0)
        print(f"  {i:<3} {score:<5} {quality:<6} {source_tag:<6} {title}")

    print()
    quark_count = sum(1 for r in all_results[:20] if r.source == "quark")
    if quark_count > 0:
        print(f"💡 {quark_count} 个夸克资源可直接保存。使用方法: mediavault save <序号>")
        print(f"   或者: mediavault auto \"{query}\"  一键保存最佳版本")
    print()


def cmd_save_by_index(index: int, config: dict, folder: str = ""):
    """Save a result from the last search by its table index."""
    if not LAST_SEARCH_CACHE.exists():
        print("❌ 没有搜索结果缓存。请先运行 mediavault search <关键词>")
        return

    results = json.loads(LAST_SEARCH_CACHE.read_text(encoding='utf-8'))
    if index < 1 or index > len(results):
        print(f"❌ 序号超出范围 (1-{len(results)})")
        return

    if not check_cookie_health(config):
        return

    target = results[index - 1]
    print(f"\n已选择: {target['title']}")
    print(f"评分: {target['score']}")

    if target["source"] != "quark":
        print(f"⚠️  该资源来源是 {target['source']}，非夸克网盘，暂不支持自动保存。")
        return

    # Load plugin to extract link
    plugins = load_plugins(config)
    plugin = next((p for p in plugins if p.name == target["site"]), None)
    if not plugin:
        print("❌ 无法加载对应插件")
        return

    # Rebuild ResourceResult
    res = ResourceResult(
        title=target["title"], source=target["source"],
        url=target["url"], site=target["site"], extra=target.get("extra", {}),
    )

    share_url = plugin.extract_link(res)
    if not share_url:
        print("❌ 无法提取夸克分享链接")
        return

    print(f"链接: {share_url}")

    client = get_quark_client(config)
    if not folder:
        folder = config.get("save_folder", "夸克影视")

    print(f"☁️  正在保存到夸克网盘/{folder}...")
    result = client.save_share(share_url, folder_name=folder)
    status = result.get("status", 0) or result.get("code", 0)

    if status == 200:
        print(f"✅ 保存成功！")
        # Try organizing
        _organize_saved(result, target["title"], folder, config, "")
    else:
        msg = result.get("message", result.get("error", "unknown"))
        print(f"❌ 保存失败: {msg}")


def cmd_auto(query: str, config: dict, folder: str = "", content_type: str = "",
             genre: str = ""):
    """Search + auto-save best Quark resource. Optionally specify --genre."""
    if not check_cookie_health(config):
        return

    plugins = load_plugins(config)
    if not plugins:
        print("❌ 没有启用的搜索引擎。运行 mediavault init 配置。")
        return

    # Search
    all_results = []
    for plugin in plugins:
        print(f"🔍 正在搜索 {plugin.display_name}...", file=sys.stderr)
        try:
            results = plugin.search(query)
            for r in results:
                r.site = plugin.name
                r.extra["score"] = score_resource(r)
            all_results.extend(results)
        except Exception as e:
            print(f"  ⚠️  {plugin.name} 出错: {e}", file=sys.stderr)

    if not all_results:
        print("❌ 未找到任何资源")
        return

    all_results.sort(key=lambda r: r.extra.get("score", 0), reverse=True)
    quark_results = [r for r in all_results if r.source == "quark"]

    # Also show a quick summary
    print()
    print(f"找到 {len(all_results)} 个资源，其中 {len(quark_results)} 个夸克资源")
    for i, r in enumerate(all_results[:5], 1):
        score = r.extra.get("score", 0)
        source_icon = "☁️" if r.source == "quark" else "🔗"
        print(f"  {source_icon} [{score:>3}] {r.title[:60]}")

    if not quark_results:
        print()
        print("❌ 未找到夸克网盘资源，尝试其他关键词或搜索引擎。")
        return

    client = get_quark_client(config)
    if not folder:
        folder = config.get("save_folder", "夸克影视")

    best = None
    share_url = None
    result = None

    for candidate in quark_results:
        plugin = next((p for p in plugins if p.name == candidate.site), None)
        if not plugin:
            continue
        print(f"\n🔗 尝试: {candidate.title}")
        print(f"   评分: {candidate.extra.get('score', 0)}")
        url = plugin.extract_link(candidate)
        if not url:
            print(f"   ⚠️  提取链接失败，尝试下一个...")
            continue

        print(f"   ✅ 提取成功: {url}")
        print(f"☁️  保存到 夸克/{folder}...")
        result = client.save_share(url, folder_name=folder)
        status = result.get("status", 0) or result.get("code", 0)

        if status == 200:
            best = candidate
            share_url = url
            print(f"   ✅ 保存成功！")
            break
        else:
            msg = result.get("message", result.get("error", "unknown"))
            print(f"   ⚠️  保存失败 ({msg})，尝试下一个...")
            continue

    if not best or not share_url or not result:
        print("❌ 所有结果保存失败")
        return

    # Organize into library
    _organize_saved(result, best.title, folder, config, content_type, genre)

    print(f"\n✅ 完成！")
    print(json.dumps({"movie": best.title, "share_url": share_url, "result": result},
                     indent=2, ensure_ascii=False))


def _organize_saved(save_result: dict, title: str, folder: str,
                    config: dict, content_type: str, genre: str = ""):
    """Organize a successfully saved file into the library."""
    task_data = save_result.get("task_result", {}).get("data", {})
    save_as = task_data.get("save_as", {})
    saved_fids = save_as.get("save_as_top_fids", [])

    if not saved_fids:
        return

    from library import extract_movie_info
    info = extract_movie_info(title)
    lib = LibraryManager(
        QuarkClient(cookie=config.get("quark", {}).get("cookie", "")),
        library_root=folder,
        omdb_key=config.get("omdb_api_key", ""),
    )

    if not content_type:
        content_type = _detect_content_type(title)

    for fid in saved_fids:
        org_result = lib.organize_movie(
            fid, title, info.get("year", ""), "", content_type=content_type,
            genre=genre,
        )
        if org_result.get("status") == "ok":
            print(f"📁 已归档: {org_result['path']}", file=sys.stderr)
        else:
            print(f"⚠️  归档失败: {org_result.get('error')}", file=sys.stderr)


def cmd_organize(fid: str, title: str, config: dict, content_type: str = "movie",
                 season: int = 1, episode: int = 0, genre: str = ""):
    client = get_quark_client(config)
    lib = LibraryManager(
        client,
        library_root=config.get("save_folder", "影视资源"),
        omdb_key=config.get("omdb_api_key", ""),
    )

    if content_type == "tv":
        result = lib.organize_tv_show(fid, title, season=season, episode=episode)
    else:
        result = lib.organize_movie(fid, title, genre=genre)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def _safe_input(prompt: str) -> str:
    """input() wrapper that handles non-interactive environments."""
    try:
        return input(prompt)
    except (EOFError, OSError):
        print()
        print("  ⚠️  当前环境不支持交互输入。")
        print("  请手动创建 config.json（参考 config.example.json）")
        sys.exit(1)


def cmd_login(config: dict):
    """Login to Quark — QR scan or manual cookie."""
    print()
    print("=" * 50)
    print("  夸克网盘登录")
    print("=" * 50)
    print()
    print("  [1] 扫码登录（推荐）— 终端显示二维码，夸克 App 一扫即可")
    print("  [2] 手动输入 Cookie — 从浏览器复制")
    print()

    choice = _safe_input("选择登录方式 [1/2] (默认 1): ").strip() or "1"

    if choice == "1":
        print()
        print("  正在获取二维码...")
        print()
        client = QuarkClient()
        if client.qr_login():
            config["quark"] = config.get("quark", {})
            config["quark"]["cookie"] = client.cookie
            config["quark"]["username"] = ""
            config["quark"]["password"] = ""
            save_config(config)
            print(f"✅ Cookie 已保存")
        else:
            print()
            print("❌ 扫码登录失败。可能的原因：")
            print("   - 网络连接问题")
            print("   - 夸克 API 暂时不可用")
            print()
            print("  试试方式 2：")
            print("      mediavault login")
            print("  然后选择 [2] 手动输入 Cookie。")
    elif choice == "2":
        print()
        print("  📖 获取 Cookie 步骤：")
        print()
        print("  1. 打开浏览器，访问 https://pan.quark.cn")
        print("  2. 登录你的夸克账号")
        print("  3. 按 F12 打开开发者工具")
        print("  4. 点击 Application → Cookies → pan.quark.cn")
        print("  5. 你会看到很多条目，全选复制，粘贴到下面")
        print()
        cookie = _safe_input("Cookie: ").strip()
        if cookie:
            config["quark"] = config.get("quark", {})
            config["quark"]["cookie"] = cookie
            config["quark"]["username"] = ""
            config["quark"]["password"] = ""
            save_config(config)
            print()
            print("✅ Cookie 已保存")
            print("   ⚠️  Cookie 约 7 天后过期，届时重新运行 mediavault login")
        else:
            print("❌ Cookie 为空，未保存。")
    else:
        print("请输入 1 或 2，重新运行 mediavault login。")


def cmd_plugins(config: dict):
    plugins = load_plugins(config)
    if not plugins:
        print("没有启用的搜索引擎。")
        print()
        print("添加搜索引擎：")
        print("  cp scripts/plugins/example.py scripts/plugins/your_site.py")
        print("  # 编辑 your_site.py，实现 search() 和 extract_link()")
        print('  # 在 config.json 中启用: "your_site": {"enabled": true}')
        return

    print("已启用的搜索引擎：")
    for p in plugins:
        auth = "[auth]" if p.requires_auth else "[free]"
        print(f"  {auth} {p.display_name} ({p.name}) — {p.url}")


def print_help():
    print(__doc__)


def main():
    # Ensure UTF-8 output on Windows terminals
    if sys.platform == 'win32':
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    config = load_config()
    cmd = sys.argv[1]

    if cmd == "init":
        cmd_init(config)

    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        if not query:
            print("用法: mediavault search <关键词>")
            sys.exit(1)
        cmd_search(query, config)

    elif cmd == "save":
        if len(sys.argv) < 3:
            print("用法: mediavault save <序号>")
            print("       mediavault save <夸克分享链接> [--folder <文件夹名>]")
            sys.exit(1)
        try:
            index = int(sys.argv[2])
            folder = ""
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--folder" and i + 1 < len(sys.argv):
                    folder = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1
            cmd_save_by_index(index, config, folder=folder)
        except ValueError:
            # It's a raw share URL
            from quark import QuarkClient
            if not check_cookie_health(config):
                sys.exit(1)
            share_url = sys.argv[2]
            folder = ""
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--folder" and i + 1 < len(sys.argv):
                    folder = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1
            client = get_quark_client(config)
            print(f"☁️  保存到夸克: {share_url}")
            result = client.save_share(share_url, folder_name=folder or config.get("save_folder", ""))
            print(json.dumps(result, indent=2, ensure_ascii=False))

    elif cmd == "auto":
        content_type = ""
        folder = ""
        genre = ""
        query_parts = []
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--folder" and i + 1 < len(sys.argv):
                folder = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--type" and i + 1 < len(sys.argv):
                content_type = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--genre" and i + 1 < len(sys.argv):
                genre = sys.argv[i + 1]
                i += 2
            else:
                query_parts.append(sys.argv[i])
                i += 1
        query = " ".join(query_parts)
        if not query:
            print("用法: mediavault auto <关键词> [--folder <文件夹>] [--type movie|tv] [--genre <类型>]")
            sys.exit(1)
        cmd_auto(query, config, folder=folder, content_type=content_type, genre=genre)

    elif cmd == "organize":
        if len(sys.argv) < 4:
            print("用法: mediavault organize <file_id> <标题> [--type movie|tv] [--genre <类型>] [--season N] [--episode N]")
            sys.exit(1)
        fid = sys.argv[2]
        title = sys.argv[3]
        content_type = "movie"
        genre = ""
        season, episode = 1, 0
        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--type" and i + 1 < len(sys.argv):
                content_type = sys.argv[i + 1]; i += 2
            elif sys.argv[i] == "--genre" and i + 1 < len(sys.argv):
                genre = sys.argv[i + 1]; i += 2
            elif sys.argv[i] == "--season" and i + 1 < len(sys.argv):
                season = int(sys.argv[i + 1]); i += 2
            elif sys.argv[i] == "--episode" and i + 1 < len(sys.argv):
                episode = int(sys.argv[i + 1]); i += 2
            else:
                i += 1
        cmd_organize(fid, title, config, content_type, season, episode, genre)

    elif cmd == "login":
        cmd_login(config)

    elif cmd == "plugins":
        cmd_plugins(config)

    elif cmd in ("-h", "--help", "help"):
        print_help()

    else:
        print(f"未知命令: {cmd}")
        print()
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
