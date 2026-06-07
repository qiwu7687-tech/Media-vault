# 🎬 MediaVault — 影视媒体库管理工具

**自动化管理夸克网盘中的影视文件 — 分类整理、元数据补全、Infuse / Plex / Jellyfin 兼容。**

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License MIT">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
</p>

---

## ✨ 功能

- 📁 **媒体库整理** — 自动按电影/电视剧→类型→片名 (年份) 归档，Infuse / Plex 兼容
- 🎭 **元数据补全** — 通过 OMDB API 自动识别类型（动作/科幻/剧情/动画...）
- 🏷️ **智能重命名** — 识别场景命名格式，清理杂乱文件名
- ☁️ **网盘文件管理** — 在夸克网盘内创建文件夹、移动、重命名
- 🔌 **插件化搜索** — 可扩展的搜索接口，按需启用，也可完全不用
- 📊 **质量评分** — 按分辨率、片源、HDR、音频、编码自动排序

> 💡 核心价值是**管理你的媒体库**。搜索是可选插件 —— 用内置的、自己写、或者完全跳过搜索，只管理已有文件。

---

## 🚀 3 分钟上手

```bash
# 1. 克隆
git clone https://github.com/qiwu7687-tech/Media-vault.git
cd media-vault

# 2. 安装（注册 mediavault 命令到系统）
pip install .

# 3. 首次配置
mediavault init

# 4. 整理你的媒体库
mediavault organize <file_id> "电影名称"
```

> 💡 如果需要搜索新内容，看下面的插件搜索说明。

---

## 📖 使用说明

### 媒体库管理（核心功能）

```bash
# 整理单个文件到媒体库
$ mediavault organize <file_id> "天空之鱼"

Genre: 冒险
📁 已归档: 夸克影视/电影/冒险/天空之鱼 (2031)

# 整理电视剧
$ mediavault organize <file_id> "王国的纷争" --type tv --season 1 --episode 1
📁 已归档: 夸克影视/电视剧/奇幻/王国的纷争/Season 01
```

### 插件搜索（可选）

```bash
# 使用已配置的插件搜索
$ mediavault search "天空之鱼"

找到 32 个结果，按评分排序：

  #   评分   画质   来源   标题
  ─── ───── ────── ────── ──────────────────────────────────
  1   150   4k     夸克   Sky Fish 2031 2160p REMUX HDR Atmos
  2   102   1080p  夸克   天空之鱼 2031 BluRay 1080p x265
  ...

# 选择保存
$ mediavault save 1
✅ 保存成功！📁 已归档: 夸克影视/电影/冒险/天空之鱼 (2031)
```

### 全部命令

| 命令 | 说明 |
|------|------|
| `mediavault init` | 首次配置向导 |
| `mediavault organize <fid> <标题>` | 整理文件到媒体库 |
| `mediavault organize <fid> <标题> --genre 纪录片` | 手动指定类型整理 |
| `mediavault search <关键词>` | 插件搜索，评分排序 |
| `mediavault save <序号>` | 保存上次搜索的第 N 个结果 |
| `mediavault auto <关键词>` | 搜索 + 保存 + 整理一步完成 |
| `mediavault auto <关键词> --genre 科幻` | 自动模式 + 手动指定类型 |
| `mediavault login` | 扫码登录夸克网盘 |
| `mediavault plugins` | 查看已启用的插件 |

---

## 📁 媒体库结构

自动整理为 Infuse / Plex 兼容结构：

```
夸克影视/
├── 电影/
│   ├── 动作/
│   │   └── 影子计划 (2032)/
│   ├── 科幻/
│   │   └── 银河漫游 (2033)/
│   ├── 剧情/
│   │   └── 午后时光 (2030)/
│   └── 冒险/
│       └── 天空之鱼 (2031)/
├── 电视剧/
│   ├── 剧情/
│   │   └── 夏日回忆 (2034)/
│   │       └── Season 01/
│   └── 奇幻/
│       └── 王国的纷争 (2035)/
```

---

## 🔌 插件系统

内置插件演示了接口用法。你可以自己写，也可以完全不用 —— 媒体库管理功能独立运行。

| 插件 | 类型 | 配置 |
|------|------|------|
| **PanSou** | 自建聚合引擎 | `docker compose up -d` |
| **365WP** | 在线聚合 | 无需配置 |

### 自己写插件

```bash
cp scripts/plugins/example.py scripts/plugins/你的来源.py
```

```python
from plugins import ResourcePlugin, ResourceResult

class Plugin(ResourcePlugin):
    name = "your_source"
    display_name = "你的内容来源"

    def search(self, query: str, page: int = 1) -> list[ResourceResult]:
        # 返回 ResourceResult 列表
        ...

    def extract_link(self, resource: ResourceResult) -> str | None:
        # 返回夸克分享链接或 None
        ...
```

在 `config.json` 中启用：`"your_source": {"enabled": true}`

---

## 🏗️ 架构设计

各层独立，可单独扩展或替换：

```
┌─────────────────────────────────────┐
│              CLI (mediavault)            │  ← 统一入口
├─────────────────────────────────────┤
│  搜索插件         │   媒体库管理      │  ← 独立模块
│  (pansou/wp365)  │   (整理/分类)     │
├─────────────────────────────────────┤
│         存储层 (quark.py)            │  ← 当前：夸克
│                                       │    未来：阿里云盘/115/百度网盘
├─────────────────────────────────────┤
│         元数据 (OMDB)                │  ← 可选增强
└─────────────────────────────────────┘
```

添加新存储（阿里云盘/115/百度网盘）只需实现 `quark.py` 相同接口。添加元数据源（豆瓣/TMDB）扩展 `library.py`。插件接口定义在 `plugins/__init__.py`。

---

## OMDB API（可选）

MediaVault 可通过 OMDB 自动识别影片类型，用于更精准的分类归档。例如：`天空之鱼` → 冒险 → `电影/冒险/天空之鱼 (2031)`。

**不配置完全不影响使用**：搜索、保存、整理均正常工作。未识别的影片归入默认分类，也可用 `--genre 纪录片` 手动指定。

**免费获取（30 秒）：**
1. 访问 [omdbapi.com/apikey.aspx](http://www.omdbapi.com/apikey.aspx)
2. 选择 **FREE**（免费版，1000 次/天）
3. 填邮箱 → 收邮件 → 复制 Key → 粘贴到 `mediavault init`

---

## ⚠️ 免责声明

详见 [DISCLAIMER.md](DISCLAIMER.md)。简而言之：本工具是**媒体库管理工具**，不提供、不托管、不分发任何内容。用户自行对其使用行为负责。

---

## ❓ 常见问题

**Q: 必须用搜索插件吗？**
A: 不用。媒体库管理功能（整理、重命名、分类）不依赖任何插件。搜索完全可选。

**Q: 夸克网盘怎么连接？**
A: `mediavault login` 会弹出二维码，用夸克 App 扫描即可。工具通过官方 API 管理文件。

**Q: Cookie 过期了怎么办？**
A: 工具会自动检测并提示重新扫码。

**Q: 没有 OMDB API Key 能用吗？**
A: 完全可以。搜索、保存、整理都不依赖 OMDB。Genre 分类会自动回退为"其他"，也可以用 `--genre 纪录片` 手动指定。

---

## 📄 许可证

MIT — 随意使用、二次开发、分享。
