#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 兼容 .venv（install.sh 创建）与 venv 两种目录名，兼容 Windows(Scripts) 与 POSIX(bin)
for VENV_DIR in "$SCRIPT_DIR/.venv" "$SCRIPT_DIR/venv"; do
    if [ -d "$VENV_DIR" ]; then
        if [ -d "$VENV_DIR/Scripts" ]; then
            source "$VENV_DIR/Scripts/activate"
        else
            source "$VENV_DIR/bin/activate"
        fi
        break
    fi
done

if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ 未找到虚拟环境，请先运行 ./install.sh"
    exit 1
fi

python "$SCRIPT_DIR/main.py" "$@"
