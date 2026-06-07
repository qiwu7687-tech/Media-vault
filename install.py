#!/usr/bin/env python3
"""
MediaVault — One-click installer.

Checks environment → installs dependencies → guides through setup.
"""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def run(cmd, description="", check_return=True):
    """Run a shell command with progress display."""
    prefix = f"  ... {description}" if description else f"  ... {cmd[:60]}"
    print(f"{prefix:<60}", end=" ", flush=True)
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if check_return and result.returncode != 0:
            print(f"❌")
            if result.stderr.strip():
                print(f"      错误: {result.stderr.strip()[:120]}")
            return False
        print(f"✅")
        return True
    except Exception as e:
        print(f"❌ ({e})")
        return False


def check_python():
    """Check Python version."""
    version = sys.version_info
    if version >= (3, 9):
        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    print(f"  ❌ Python {version.major}.{version.minor} — 需要 Python 3.9+")
    return False


def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print("  ⚠️  Docker 未安装（PanSou 搜索引擎需要）")
    print("      安装 Docker Desktop: https://www.docker.com/products/docker-desktop")
    print("      或跳过 PanSou，仅使用 365聚合资源站（免费在线搜索）")
    return False


def setup_pansou():
    """Pull PanSou Docker image."""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", "ghcr.io/fish2018/pansou:latest"],
            capture_output=True, text=True,
        )
        if result.stdout.strip():
            print("  ✅ PanSou 镜像已存在")
            return True
    except FileNotFoundError:
        return False

    # Pull image
    print("  ... 拉取 PanSou 镜像 (ghcr.io/fish2018/pansou:latest)...")
    try:
        subprocess.run(
            ["docker", "pull", "ghcr.io/fish2018/pansou:latest"],
            check=True,
        )
        print("  ✅ PanSou 镜像拉取成功")
        return True
    except Exception:
        print("  ⚠️  PanSou 镜像拉取失败，可稍后手动执行:")
        print("      docker pull ghcr.io/fish2018/pansou:latest")
        return False


def main():
    # Ensure UTF-8 output on Windows terminals
    if sys.platform == 'win32':
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass

    print()
    print("=" * 55)
    print("  🎬 MediaVault — 一键安装")
    print("=" * 55)
    print()
    print("  自动搜索影视资源 → 保存到夸克网盘 → 分类整理")
    print()

    # ── Step 1: Environment check ──
    print("📋 环境检查")
    print("-" * 40)
    py_ok = check_python()
    docker_ok = check_docker()
    print()

    if not py_ok:
        print("请安装 Python 3.9+ 后重试: https://www.python.org/downloads/")
        sys.exit(1)

    # ── Step 2: Install dependencies ──
    print("📦 安装依赖")
    print("-" * 40)
    req_file = PROJECT_DIR / "requirements.txt"
    if req_file.exists():
        run(f'"{sys.executable}" -m pip install -r "{req_file}"', "pip install -r requirements.txt")
    else:
        run(f'"{sys.executable}" -m pip install httpx qrcode Pillow quarkpan', "pip install httpx qrcode Pillow quarkpan")
    print()

    # ── Step 3: Docker / PanSou ──
    if docker_ok:
        print("🐳 PanSou 搜索引擎")
        print("-" * 40)
        setup_pansou()
        print()
        print("  启动 PanSou:")
        print("      docker compose up -d")
        print("  或:")
        print("      docker run -d --name pansou -p 8888:8888 ghcr.io/fish2018/pansou:latest")
        print()

    # ── Step 4: Config ──
    config_path = PROJECT_DIR / "config.json"
    if not config_path.exists():
        print("⚙️  生成配置文件")
        print("-" * 40)
        example = PROJECT_DIR / "config.example.json"
        if example.exists():
            import shutil
            shutil.copy(example, config_path)
            print("  ✅ config.json 已创建（来自 config.example.json）")
        print()

    # ── Done ──
    print("=" * 55)
    print("  ✅ 安装完成！")
    print()
    print("  接下来运行:")
    print("      pip install .          # 注册 mediavault 命令")
    print("      mediavault init            # 首次配置向导")
    print()
    print("  或不安装直接用:")
    print("      python scripts/mediavault.py init")
    print("=" * 55)
    print()


if __name__ == "__main__":
    main()
