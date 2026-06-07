# MediaVault — 项目总览

## 文件清单

```
media-vault-github/           (20 个文件, ~2100 行 Python)
│
├── 📄 README.md                 英文主文档 (→ GitHub 首页，含架构图)
├── 📄 README_CN.md              中文文档
├── 📄 DISCLAIMER.md             免责声明
├── 📄 PROJECT.md                本文件 — 项目总览
├── 📄 LICENSE                   MIT
│
├── ⚙️  config.example.json       配置模板 (无敏感数据)
├── 🐳 docker-compose.yml         PanSou 一键启动
├── 📦 requirements.txt           httpx, qrcode
│
├── 🔧 install.py                一键安装脚本 (156行)
├── 🔧 setup.py                  pip install . 注册 mediavault 命令 (35行)
├── 🔧 .gitignore                config.json / __pycache__ / .cache
│
└── scripts/
    ├── __init__.py              包初始化
    ├── 🎬 mediavault.py             主入口 (664行)
    │   ├── init       — 交互式配置向导
    │   ├── search     — 插件搜索 + 评分表格
    │   ├── save N     — 选择保存
    │   ├── auto       — 一键搜索+保存+整理
    │   ├── organize   — 手动整理 (核心功能)
    │   ├── login      — 扫码登录夸克
    │   └── plugins    — 查看已启用插件
    │
    ├── ☁️  quark.py              夸克网盘客户端 (291行)
    │   ├── qr_login()     — 二维码扫码
    │   ├── save_share()   — 保存分享链接
    │   ├── list_files()   — 列出文件
    │   ├── create_folder()
    │   ├── rename_file()
    │   └── move_files()
    │
    ├── 📁 library.py            媒体库管理器 (421行)
    │   ├── LibraryManager   — 整理/归档/分类
    │   ├── lookup_genre()   — OMDB + 页面抓取
    │   ├── extract_movie_info()
    │   ├── is_scene_name()   — 场景命名检测
    │   └── clean_display_name()
    │
    └── plugins/
        ├── __init__.py          基类 ResourcePlugin + ResourceResult (59行)
        ├── example.py           插件模板 (80行)
        ├── pansou.py            PanSou 搜索引擎 (122行)
        └── wp365.py             365聚合资源站 (83行)
```

---

## 代码规模

| 模块 | 行数 | 职责 |
|------|:----:|------|
| `mediavault.py` | 764 | CLI 入口 + 全部子命令 |
| `library.py` | 437 | 媒体库整理 + 类型识别 + 场景命名 |
| `quark.py` | 383 | 夸克网盘 API 封装 |
| `install.py` | 164 | 一键安装脚本 |
| `pansou.py` | 122 | PanSou 搜索插件 |
| `wp365.py` | 83 | 365WP 搜索插件 |
| `example.py` | 80 | 插件开发模板 |
| `__init__.py` (plugins) | 59 | 插件基类定义 |
| `setup.py` | 37 | pip 安装配置 |
| `__init__.py` (scripts) | 1 | 包标记 |
| **总计** | **2130** | |

---

## 项目定位

**影视媒体库管理工具** — 核心是整理归档夸克网盘中的文件。

```
                    ┌──────────────────────┐
                    │   mediavault organize     │  ← 核心：独立可用
                    │   媒体库整理/分类/重命名  │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼────────┐ ┌────▼─────┐  ┌───────▼───────┐
     │  Plugin Search   │ │  OMDB    │  │  Quark API    │
     │  (可选插件)       │ │  元数据   │  │  网盘操作      │
     └─────────────────┘ └──────────┘  └───────────────┘
```

搜索是可选插件，媒体库管理独立运行。即所有搜索源失效，`mediavault organize` 仍完整可用。

---

## 安全措施

| 措施 | 状态 |
|------|:----:|
| `config.json` → `.gitignore` | ✅ |
| 无硬编码 Cookie | ✅ |
| 无硬编码 API Key | ✅ |
| 无硬编码个人路径 | ✅ |
| 纯 HTTP API（无 Hermes 依赖） | ✅ |
| 法律声明（README） | ✅ |

---

## 发布前待办

- [ ] 替换 `README.md` 中 `your-username` 为实际 GitHub 用户名
- [ ] 替换 `README_CN.md` 中 `your-username` 为实际 GitHub 用户名
- [ ] 替换 `setup.py` 中 `your-username` 为实际 GitHub 用户名
- [ ] 在 GitHub 创建仓库
- [ ] `git init` → `git add .` → `git commit` → `git push`
