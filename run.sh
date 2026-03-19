#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Windows 下虚拟环境的激活脚本路径通常在 Scripts 目录下
# 但为了兼容性，建议直接判断路径
if [ -d "$SCRIPT_DIR/.venv/Scripts" ]; then
    source "$SCRIPT_DIR/.venv/Scripts/activate"
else
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

python "$SCRIPT_DIR/main.py" "$@"