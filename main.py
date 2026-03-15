"""
思源笔记导出工具主程序

功能：
1. 获取思源笔记中的所有笔记本列表
2. 获取每个笔记本下的所有文档
3. 根据文档路径构建树形结构
4. 输出树形结构到控制台和 JSON 文件

使用方法：
1. 在思源笔记中获取 API Token（设置 -> 关于 -> API Token）
2. 运行程序：python main.py --token your_token_here
"""

import argparse
import json
import os
from datetime import datetime
from typing import List, Dict, Any

from siyuan_exporter.client import SiYuanClient
from siyuan_exporter.tree_builder import TreeBuilder, NotebookNode


def export_to_json(trees: List[NotebookNode], output_path: str):
    """
    将树形结构导出为 JSON 文件

    Args:
        trees: 笔记本树形结构列表
        output_path: 输出文件路径
    """
    data = [tree.to_dict() for tree in trees]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 树形结构已导出到: {output_path}")


def print_summary(trees: List[NotebookNode]):
    """
    打印统计摘要

    Args:
        trees: 笔记本树形结构列表
    """
    print("\n" + "=" * 50)
    print("📊 统计摘要")
    print("=" * 50)

    total_docs = 0

    for tree in trees:
        # 递归计算文档数量
        def count_docs(node) -> int:
            if isinstance(node, NotebookNode):
                return sum(count_docs(child) for child in node.children)
            else:
                return 1 + sum(count_docs(child) for child in node.children)

        doc_count = count_docs(tree)
        total_docs += doc_count
        print(f"📒 {tree.name}: {doc_count} 篇文档")

    print(f"\n总计: {len(trees)} 个笔记本, {total_docs} 篇文档")


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='思源笔记导出工具 - 获取笔记树形结构',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --token your_token_here
  python main.py --token your_token_here --output ./export
  python main.py --token your_token_here --base-url http://127.0.0.1:6806
        """
    )
    parser.add_argument('--token', required=True, help='思源笔记 API Token')
    parser.add_argument('--base-url', default='http://127.0.0.1:6806',
                       help='思源笔记 API 地址 (默认: http://127.0.0.1:6806)')
    parser.add_argument('--output', default='./output',
                       help='输出目录 (默认: ./output)')

    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)

    # 初始化客户端
    print("🔌 正在连接思源笔记...")
    client = SiYuanClient(token=args.token, base_url=args.base_url)

    # 1. 获取笔记本列表
    print("📚 正在获取笔记本列表...")
    notebooks = client.get_notebooks()

    if not notebooks:
        print("❌ 没有找到任何笔记本，请检查：")
        print("   1. 思源笔记是否已启动")
        print("   2. API Token 是否正确")
        print("   3. 思源笔记 API 服务是否已开启")
        return

    print(f"✅ 找到 {len(notebooks)} 个笔记本")

    # 2. 获取每个笔记本的文档并构建树形结构
    trees: List[NotebookNode] = []

    for notebook in notebooks:
        notebook_id = notebook.get("id", "")
        notebook_name = notebook.get("name", "未命名")
        notebook_icon = notebook.get("icon", "")

        print(f"\n📖 正在处理笔记本: {notebook_name}...")

        # 获取该笔记本下的所有文档
        docs = client.get_docs_by_notebook(notebook_id)
        print(f"   找到 {len(docs)} 篇文档")

        # 构建树形结构
        tree = TreeBuilder.build_notebook_tree(
            notebook_id=notebook_id,
            notebook_name=notebook_name,
            notebook_icon=notebook_icon,
            docs=docs
        )
        trees.append(tree)

    # 3. 打印树形结构
    print("\n" + "=" * 50)
    print("🌲 笔记树形结构")
    print("=" * 50)

    for tree in trees:
        TreeBuilder.print_tree(tree)
        print()

    # 4. 打印统计摘要
    print_summary(trees)

    # 5. 导出到 JSON 文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(args.output, f"siyuan_tree_{timestamp}.json")
    export_to_json(trees, output_file)

    print("\n🎉 完成！")


if __name__ == "__main__":
    main()
