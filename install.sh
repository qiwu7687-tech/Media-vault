#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  Cinema Manager 一键安装"
echo "=========================================="
echo ""

# Find Python
PYTHON=""
command -v python3 >/dev/null 2>&1 && PYTHON=python3
command -v python >/dev/null 2>&1 && PYTHON=python
if [ -z "$PYTHON" ]; then
    echo "[错误] 未找到 Python，请先安装 Python 3.8+"
    exit 1
fi
echo "[√] 找到 $PYTHON"

echo ""
echo "[1/2] 安装依赖..."
$PYTHON -m pip install -r "$(dirname "$0")/requirements.txt"

echo ""
echo "[2/2] 运行配置向导..."
$PYTHON "$(dirname "$0")/scripts/setup.py"

echo ""
echo "=========================================="
echo "  安装完成！"
echo ""
echo "  使用方式："
echo "    $PYTHON scripts/cinema.py auto 电影名"
echo "=========================================="
