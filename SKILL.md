---
name: media-vault
description: 影视媒体库管理工具 — 整理夸克网盘文件、元数据补全、类型归档。插件化搜索可选。
---

# MediaVault — AI Agent 上下文

## 项目定位

MediaVault 是一个**媒体库管理工具**，核心功能是整理夸克网盘中的影视文件。搜索是可选插件，不是项目核心目的。

```
核心 = 媒体库管理（整理 / 分类 / 元数据）
插件 = 内容搜索（PanSou / wp365 / 用户自定义）
```

## 设计原则

1. **媒体库管理优先** — library.py 是核心，优先保护和维护
2. **搜索插件可替换** — plugins/ 是扩展层，可随时增减
3. **第三方 API 尽量可选** — 任何外部依赖都有回退路径
4. **失败时优雅降级** — OMDB → `--genre` → 缓存 → "其他"

## 项目结构

```
media-vault-github/
├── scripts/
│   ├── mediavault.py       # CLI 入口（init/search/save/auto/organize/login/plugins）
│   ├── quark.py        # 夸克网盘客户端（quarkpan + HTTP 回退）
│   ├── library.py      # 媒体库管理（分类/重命名/Genre/场景识别）
│   └── plugins/        # 搜索插件（pansou.py / wp365.py / 可扩展）
├── install.py          # 一键安装脚本
├── docker-compose.yml  # PanSou Docker 启动
├── setup.py            # pip install . 注册 mediavault 命令
├── config.example.json # 配置模板
└── requirements.txt    # httpx, qrcode, Pillow, quarkpan
```

## 工作流程

```
用户输入影视名
   ↓
搜索插件（可选，mediavault organize 跳过此步）
   ↓
评分排序
   ↓
提取夸克链接
   ↓
保存到网盘
   ↓
元数据补全
   ↓
Genre 归档
```

## 登录

首次使用需要登录夸克网盘：

```bash
mediavault login
```

三种登录方式（自动选择最合适的）：
1. **PNG 二维码**（最稳）—— 保存到 `.cache/login_qr.png`，用户打开扫码
2. **ASCII 二维码**（终端内显示）—— 适用于 SSH / 远程
3. **登录链接**（永远可用）—— 打印 URL，复制到浏览器扫码

如果终端无法显示二维码，检查 `.cache/login_qr.png` 是否生成。也支持手动输入 Cookie（`mediavault login` → 选 [2]）。

## OMDB API（可选）

用途：自动获取 Genre、年份，提高分类准确率。

```
有 OMDB → 《天空之鱼》→ Adventure → 电影/冒险/天空之鱼 (2031)
无 OMDB → 《天空之鱼》→ 其他 → 电影/其他/天空之鱼 (2031)
```

**申请**：https://www.omdbapi.com/apikey.aspx → 选 FREE（1000次/天）→ 填邮箱 → 收 Key

**不配置**：搜索、保存、整理全部正常。仅 Genre 自动分类回退到"其他"或手动 `--genre 纪录片`。

在 `mediavault init` 中可直接回车跳过。Key 填入 `config.json` 的 `omdb_api_key` 字段。

## 命令行

```bash
mediavault init                        # 首次配置向导
mediavault search <关键词>              # 插件搜索，评分表格
mediavault save <序号>                  # 保存搜索结果
mediavault auto <关键词>                # 一键搜索+保存+整理
mediavault auto <关键词> --genre 纪录片 # 手动指定类型
mediavault organize <fid> <标题>        # 手动整理文件
mediavault login                        # 重新登录
mediavault plugins                      # 查看插件
```

## 搜索引擎

| 引擎 | 状态 | 说明 |
|------|:----:|------|
| PanSou | 可选 | 需 Docker：`docker compose up -d` |
| 365聚合资源站 (wp365) | 默认启用 | 免费，无需配置 |

## Genre 回退机制

```
OMDB API 查询        ← 有 Key 时自动
   ↓ 失败
--genre 手动指定      ← 用户明确知道类型
   ↓ 未指定
本地缓存 (.cache)     ← 之前查过
   ↓ 无缓存
"其他"               ← 兜底
```

## 敏感文件（Never Commit）

这些文件包含用户凭证或运行时数据，绝对不要加入版本控制：

- `config.json` — 夸克 Cookie + OMDB Key
- `.cache/*` — 登录二维码 + Genre 缓存
- `*.log` — 运行日志

始终使用 `config.example.json` 作为配置模板。

## 注意事项

- 夸克 Cookie 约 7 天过期，工具会检测并提示重新登录
- 夸克 API 接口可能变动，存储层设计为可插拔（未来可接阿里云盘/115/百度网盘）
- PanSou 需要 Docker，未安装时仅 wp365 可用
- 非交互环境（CI/Docker）中 `mediavault login` 会提示手动创建 config.json
