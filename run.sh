#!/bin/bash
# 思源笔记导出工具运行脚本
# 自动激活虚拟环境并运行程序

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 激活虚拟环境
source "$SCRIPT_DIR/venv/bin/activate"

# 运行主程序
python "$SCRIPT_DIR/main.py" "$@"
