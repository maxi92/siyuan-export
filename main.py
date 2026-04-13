"""
思源笔记导出工具主程序

功能：
1. 获取思源笔记中的所有笔记本列表
2. 获取每个笔记本下的所有文档
3. 根据文档路径构建树形结构
4. 输出树形结构到控制台

使用方法：
1. 在思源笔记中获取 API Token（设置 -> 关于 -> API Token）
2. 运行程序：python main.py --token your_token_here
"""

import argparse
import os
from datetime import datetime
from typing import List

from siyuan_exporter.client import SiYuanClient
from siyuan_exporter.tree_builder import TreeBuilder, NotebookNode, DocNode
from siyuan_exporter.markdown_processor import preprocess_markdown
from siyuan_exporter.sync_manager import SyncManager, NotebookSyncRecord, DocSyncRecord


def export_single_doc_markdown(client: SiYuanClient, doc_id: str, output_dir: str):
    """
    导出指定笔记（文档）的 Markdown 内容

    Args:
        client: SiYuanClient 实例
        doc_id: 笔记 ID
        output_dir: 输出目录
    """
    print(f"\n📄 正在获取笔记 {doc_id} 的 Markdown 内容...")

    markdown_content = client.get_doc_markdown(doc_id)
    if markdown_content is None:
        print("❌ 获取 Markdown 内容失败")
        return

    # 预处理：还原字面换行符并转换表格为列表格式
    markdown_content = preprocess_markdown(markdown_content)

    # 从内容中提取标题（如果有 YAML frontmatter 中的 title）
    import re
    title_match = re.search(r'^# 标题：(.+)$', markdown_content, re.MULTILINE)
    if title_match:
        doc_title = title_match.group(1).strip()
    else:
        # 尝试从第一行获取标题
        first_line = markdown_content.split('\n')[0].strip()
        if first_line.startswith('# '):
            doc_title = first_line[2:].strip()
        else:
            doc_title = doc_id

    safe_title = "".join(c for c in doc_title if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_title:
        safe_title = doc_id

    output_file = os.path.join(output_dir, f"{safe_title}_{doc_id}.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"✅ Markdown 已导出到: {output_file}")
    print(f"   文件大小: {len(markdown_content)} 字符")


def export_notebook_markdown(client: SiYuanClient, notebook_node: NotebookNode, output_dir: str):
    """
    导出整个笔记本的所有笔记为 Markdown 文件，按树形结构组织文件系统

    文件结构：
    - 笔记本名称作为根文件夹
    - 父笔记的 markdown 文件与其子笔记文件夹同级
    - 子笔记放在以父笔记名称命名的文件夹下

    Args:
        client: SiYuanClient 实例
        notebook_node: 笔记本节点（包含树形结构）
        output_dir: 输出目录
    """
    # 创建安全的笔记本文件夹名称
    safe_notebook_name = "".join(c for c in notebook_node.name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_notebook_name:
        safe_notebook_name = notebook_node.id

    notebook_dir = os.path.join(output_dir, safe_notebook_name)
    os.makedirs(notebook_dir, exist_ok=True)

    print(f"\n📁 笔记本导出目录: {notebook_dir}")

    # 统计
    total_docs = 0
    success_count = 0
    fail_count = 0

    def get_safe_filename(title: str, doc_id: str) -> str:
        """生成安全的文件名"""
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_title:
            safe_title = doc_id
        # 限制文件名长度，避免系统限制
        if len(safe_title) > 100:
            safe_title = safe_title[:100]
        return f"{safe_title}_{doc_id}.md"

    def export_doc_recursive(node: DocNode, current_dir: str, parent_title: str = ""):
        """
        递归导出文档及其子文档

        Args:
            node: 当前文档节点
            current_dir: 当前所在的目录路径
            parent_title: 父文档标题（用于显示层级关系）
        """
        nonlocal total_docs, success_count, fail_count

        total_docs += 1
        doc_title = node.title
        doc_id = node.id

        prefix = f"  {'  ' * node.level}"
        print(f"{prefix}📄 正在导出: {doc_title}")

        # 获取 Markdown 内容
        markdown_content = client.get_doc_markdown(doc_id)

        if markdown_content is None:
            print(f"{prefix}   ❌ 获取失败: {doc_title}")
            fail_count += 1
            # 即使失败也继续处理子文档
        else:
            # 预处理 Markdown
            markdown_content = preprocess_markdown(markdown_content)

            # 保存到文件
            filename = get_safe_filename(doc_title, doc_id)
            output_file = os.path.join(current_dir, filename)

            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                success_count += 1
            except Exception as e:
                print(f"{prefix}   ❌ 写入文件失败: {e}")
                fail_count += 1

        # 处理子文档
        if node.children:
            # 创建以当前文档命名的子文件夹存放子文档
            safe_folder_name = "".join(c for c in doc_title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_folder_name:
                safe_folder_name = doc_id
            # 限制文件夹名长度
            if len(safe_folder_name) > 100:
                safe_folder_name = safe_folder_name[:100]

            child_dir = os.path.join(current_dir, safe_folder_name)
            os.makedirs(child_dir, exist_ok=True)

            print(f"{prefix}   📂 创建子文件夹: {safe_folder_name}/ ({len(node.children)} 个子文档)")

            for child in node.children:
                export_doc_recursive(child, child_dir, doc_title)

    # 从笔记本的直接子文档开始导出
    for doc_node in notebook_node.children:
        export_doc_recursive(doc_node, notebook_dir)

    print(f"\n📊 导出统计: 总计 {total_docs} 篇, 成功 {success_count} 篇, 失败 {fail_count} 篇")


def export_notebook_markdown_incremental(client: SiYuanClient, notebook_node: NotebookNode, output_dir: str):
    """
    增量导出整个笔记本的所有笔记为 Markdown 文件

    逻辑：
    1. 如果目标位置没有该笔记对应的md文件，则创建
    2. 如果文件已存在，则比较 updated 时间，仅在上次导出后有更新时才覆盖
    3. 如果笔记已不存在但文件/文件夹还在，则删除

    Args:
        client: SiYuanClient 实例
        notebook_node: 笔记本节点（包含树形结构）
        output_dir: 输出目录
    """
    sync_manager = SyncManager()  # 使用默认配置目录 .siyuan-export/sync

    # 创建安全的笔记本文件夹名称（处理重名情况）
    safe_notebook_name = "".join(c for c in notebook_node.name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_notebook_name:
        safe_notebook_name = notebook_node.id

    notebook_dir = os.path.join(output_dir, safe_notebook_name)
    os.makedirs(notebook_dir, exist_ok=True)

    print(f"\n📁 笔记本导出目录: {notebook_dir}")

    # 加载上次同步记录
    sync_record = sync_manager.load_record(notebook_node)
    if sync_record:
        print(f"   📋 上次同步时间: {sync_record.last_sync[:19]}")
    else:
        print(f"   📋 首次同步，将创建所有文件")

    # 创建新的同步记录
    from datetime import datetime
    new_sync_record = NotebookSyncRecord(
        notebook_id=notebook_node.id,
        notebook_name=notebook_node.name,
        last_sync=datetime.now().isoformat(),
        docs={}
    )

    # 统计
    stats = {"created": 0, "updated": 0, "unchanged": 0, "failed": 0, "deleted_files": 0, "deleted_folders": 0}

    def get_safe_filename(title: str, doc_id: str) -> str:
        """生成安全的文件名"""
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_title:
            safe_title = doc_id
        if len(safe_title) > 100:
            safe_title = safe_title[:100]
        return f"{safe_title}_{doc_id}.md"

    def export_doc_recursive(node: DocNode, current_dir: str, parent_title: str = ""):
        """
        递归导出文档及其子文档
        """
        doc_title = node.title
        doc_id = node.id

        prefix = "  " * node.level
        filename = get_safe_filename(doc_title, doc_id)
        file_path = os.path.join(current_dir, filename)
        rel_path = os.path.relpath(file_path, notebook_dir)

        # 判断是否需要更新
        doc_record = sync_record.docs.get(doc_id) if sync_record else None
        needs_update = sync_manager.should_update(node, doc_record, file_path)

        if doc_record is None:
            action = "🆕 创建"
            stats["created"] += 1
        elif needs_update:
            action = "🔄 更新"
            stats["updated"] += 1
        else:
            action = "⏭️  跳过"
            stats["unchanged"] += 1

        if needs_update:
            print(f"{prefix}{action}: {doc_title}")

            # 获取 Markdown 内容
            markdown_content = client.get_doc_markdown(doc_id)

            if markdown_content is None:
                print(f"{prefix}   ❌ 获取失败: {doc_title}")
                stats["failed"] += 1
            else:
                # 预处理 Markdown
                markdown_content = preprocess_markdown(markdown_content)

                # 保存到文件
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                except Exception as e:
                    print(f"{prefix}   ❌ 写入文件失败: {e}")
                    stats["failed"] += 1
        else:
            # 跳过未变更的文件
            pass

        # 记录当前同步状态
        new_sync_record.docs[doc_id] = DocSyncRecord(
            doc_id=doc_id,
            title=doc_title,
            updated=node.updated,
            last_sync=datetime.now().isoformat(),
            file_path=rel_path
        )

        # 处理子文档
        if node.children:
            safe_folder_name = "".join(c for c in doc_title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_folder_name:
                safe_folder_name = doc_id
            if len(safe_folder_name) > 100:
                safe_folder_name = safe_folder_name[:100]

            child_dir = os.path.join(current_dir, safe_folder_name)
            os.makedirs(child_dir, exist_ok=True)

            if needs_update:
                print(f"{prefix}   📂 子文件夹: {safe_folder_name}/ ({len(node.children)} 个子文档)")

            for child in node.children:
                export_doc_recursive(child, child_dir, doc_title)

    # 从笔记本的直接子文档开始导出
    for doc_node in notebook_node.children:
        export_doc_recursive(doc_node, notebook_dir)

    # 清理孤儿文件和文件夹
    print(f"\n🧹 清理已删除的笔记文件...")
    deleted_files, deleted_folders = sync_manager.remove_orphaned_files(notebook_node, notebook_dir)
    stats["deleted_files"] = deleted_files
    stats["deleted_folders"] = deleted_folders

    if deleted_files == 0 and deleted_folders == 0:
        print(f"   ✨ 无需清理")
    else:
        print(f"   🗑️  删除 {deleted_files} 个文件, {deleted_folders} 个文件夹")

    # 保存同步记录
    sync_manager.save_record(notebook_node, new_sync_record)
    print(f"   💾 同步记录已保存")

    print(f"\n📊 导出统计: 新建 {stats['created']} 篇, 更新 {stats['updated']} 篇, 跳过 {stats['unchanged']} 篇, 失败 {stats['failed']} 篇")
    if stats['deleted_files'] > 0 or stats['deleted_folders'] > 0:
        print(f"   🗑️ 清理: {stats['deleted_files']} 个文件, {stats['deleted_folders']} 个文件夹")


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
  python main.py --token your_token_here --doc-id 20240806202611-ecxtzjt
  python main.py --token your_token_here --notebook-id 20240806202611-ecxtzjt
  python main.py --token your_token_here --notebook-id 20240806202611-ecxtzjt --sync
  python main.py --token your_token_here --all-notebooks
  python main.py --token your_token_here --all-notebooks --sync
        """
    )
    parser.add_argument('--token', required=True, help='思源笔记 API Token')
    parser.add_argument('--base-url', default='http://127.0.0.1:6806',
                       help='思源笔记 API 地址 (默认: http://127.0.0.1:6806)')
    parser.add_argument('--output', default='./output',
                       help='输出目录 (默认: ./output)')
    parser.add_argument('--doc-id',
                       help='要导出的笔记（文档）ID，导出该笔记的 Markdown 内容')
    parser.add_argument('--notebook-id',
                       help='要导出的笔记本 ID，导出该笔记本下所有笔记的 Markdown 内容（按树形结构组织）')
    parser.add_argument('--all-notebooks', action='store_true',
                       help='导出所有笔记本下的所有笔记（与 --notebook-id 互斥）')
    parser.add_argument('--sync', action='store_true',
                       help='启用增量同步模式（与 --notebook-id 或 --all-notebooks 配合使用），只导出有更新的笔记并清理已删除的文件')

    args = parser.parse_args()

    # 检查互斥参数
    if args.notebook_id and args.all_notebooks:
        print("❌ 错误: --notebook-id 和 --all-notebooks 不能同时使用")
        print("   请只使用其中一个参数")
        return

    # 创建输出目录（在指定目录下创建"思源笔记"子目录）
    args.output = os.path.join(args.output, "思源笔记")
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

    # 5. 如果指定了笔记 ID，导出该笔记的 Markdown
    if args.doc_id:
        print("\n" + "=" * 50)
        print("📄 指定笔记 Markdown 导出")
        print("=" * 50)
        export_single_doc_markdown(client, args.doc_id, args.output)

    # 6. 如果指定了笔记本 ID，导出该笔记本下所有笔记的 Markdown
    if args.notebook_id:
        print("\n" + "=" * 50)
        if args.sync:
            print("📚 笔记本增量同步导出")
        else:
            print("📚 笔记本批量 Markdown 导出")
        print("=" * 50)

        # 查找指定的笔记本
        target_notebook = None
        for tree in trees:
            if tree.id == args.notebook_id:
                target_notebook = tree
                break

        if target_notebook is None:
            print(f"❌ 未找到笔记本 ID: {args.notebook_id}")
            print("可用的笔记本:")
            for tree in trees:
                print(f"   - {tree.name} (ID: {tree.id})")
        else:
            print(f"📒 正在导出笔记本: {target_notebook.name}")
            if args.sync:
                export_notebook_markdown_incremental(client, target_notebook, args.output)
            else:
                export_notebook_markdown(client, target_notebook, args.output)

    # 7. 如果指定了导出所有笔记本
    if args.all_notebooks:
        print("\n" + "=" * 50)
        if args.sync:
            print("📚 全部笔记本增量同步导出")
        else:
            print("📚 全部笔记本批量 Markdown 导出")
        print("=" * 50)

        total_notebooks = len(trees)
        print(f"📒 共 {total_notebooks} 个笔记本需要导出\n")

        for i, tree in enumerate(trees, 1):
            print(f"\n[{i}/{total_notebooks}] 📒 正在导出笔记本: {tree.name}")
            if args.sync:
                export_notebook_markdown_incremental(client, tree, args.output)
            else:
                export_notebook_markdown(client, tree, args.output)

    print("\n🎉 完成！")


if __name__ == "__main__":
    main()
