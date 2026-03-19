#!/bin/bash
# 思源笔记导出工具安装脚本
# 创建虚拟环境并安装依赖

set -e

echo "📦 正在安装思源笔记导出工具..."

# 检查是否安装了 uv
if ! command -v uv &> /dev/null; then
    echo "⬇️  正在安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# 创建虚拟环境
echo "🐍 正在创建虚拟环境..."
uv venv

# 安装依赖
echo "📥 正在安装依赖..."
uv pip install -r requirements.txt

echo "✅ 安装完成！"
echo ""
echo "使用方法:"
echo "  ./run.sh --token your_api_token"
echo ""
echo "或手动激活虚拟环境:"
echo "  source venv/bin/activate"
echo "  python main.py --token your_api_token"
