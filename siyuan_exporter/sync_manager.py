"""
增量同步管理器
负责管理笔记本的增量同步逻辑，包括：
1. 记录上次同步时间
2. 判断笔记是否需要更新
3. 清理已删除的笔记文件
"""

import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from siyuan_exporter.tree_builder import DocNode, NotebookNode


@dataclass
class DocSyncRecord:
    """单条笔记同步记录"""
    doc_id: str
    title: str
    updated: str  # 思源笔记的 updated 时间戳
    last_sync: str  # 上次同步时间
    file_path: str  # 相对路径


@dataclass
class NotebookSyncRecord:
    """笔记本同步记录"""
    notebook_id: str
    notebook_name: str
    last_sync: str  # 整体上次同步时间
    docs: Dict[str, DocSyncRecord] = field(default_factory=dict)  # doc_id -> record

    def to_dict(self) -> dict:
        return {
            "notebook_id": self.notebook_id,
            "notebook_name": self.notebook_name,
            "last_sync": self.last_sync,
            "docs": {k: asdict(v) for k, v in self.docs.items()}
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NotebookSyncRecord":
        record = cls(
            notebook_id=data["notebook_id"],
            notebook_name=data["notebook_name"],
            last_sync=data["last_sync"],
            docs={}
        )
        for doc_id, doc_data in data.get("docs", {}).items():
            record.docs[doc_id] = DocSyncRecord(**doc_data)
        return record


class SyncManager:
    """增量同步管理器"""

    SYNC_RECORD_FILENAME = ".last_sync.json"

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self._records: Dict[str, NotebookSyncRecord] = {}  # notebook_id -> record
        self._loaded = False

    def _get_safe_notebook_name(self, name: str, notebook_id: str) -> str:
        """生成安全的笔记本文件夹名称"""
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = notebook_id
        return safe_name

    def _get_sync_record_path(self, notebook_node: NotebookNode) -> str:
        """获取同步记录文件路径"""
        safe_name = self._get_safe_notebook_name(notebook_node.name, notebook_node.id)
        notebook_dir = os.path.join(self.output_dir, safe_name)
        return os.path.join(notebook_dir, self.SYNC_RECORD_FILENAME)

    def load_record(self, notebook_node: NotebookNode) -> Optional[NotebookSyncRecord]:
        """加载指定笔记本的同步记录"""
        record_path = self._get_sync_record_path(notebook_node)

        if not os.path.exists(record_path):
            return None

        try:
            with open(record_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return NotebookSyncRecord.from_dict(data)
        except Exception as e:
            print(f"   ⚠️ 加载同步记录失败: {e}")
            return None

    def save_record(self, notebook_node: NotebookNode, record: NotebookSyncRecord):
        """保存指定笔记本的同步记录"""
        record_path = self._get_sync_record_path(notebook_node)

        try:
            with open(record_path, 'w', encoding='utf-8') as f:
                json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"   ⚠️ 保存同步记录失败: {e}")

    def should_update(self, doc: DocNode, record: Optional[DocSyncRecord], file_path: str) -> bool:
        """
        判断笔记是否需要更新

        Args:
            doc: 当前笔记节点
            record: 上次同步记录
            file_path: 文件完整路径

        Returns:
            是否需要更新
        """
        # 如果文件不存在，需要创建
        if not os.path.exists(file_path):
            return True

        # 如果没有同步记录，或者 updated 时间戳更新了，需要更新
        if record is None:
            return True

        # 比较 updated 时间戳
        return doc.updated > record.updated

    def get_existing_files(self, notebook_dir: str) -> Set[str]:
        """
        获取笔记本目录下所有现有的 .md 文件路径集合

        Returns:
            相对于 notebook_dir 的文件路径集合
        """
        existing_files = set()

        for root, dirs, files in os.walk(notebook_dir):
            # 跳过同步记录文件
            if self.SYNC_RECORD_FILENAME in files:
                files.remove(self.SYNC_RECORD_FILENAME)

            for file in files:
                if file.endswith('.md'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, notebook_dir)
                    existing_files.add(rel_path)

        return existing_files

    def get_expected_files(self, notebook_node: NotebookNode) -> Set[str]:
        """
        根据当前笔记本结构，计算应该存在的文件路径集合

        Returns:
            相对于 notebook_dir 的文件路径集合
        """
        expected_files = set()

        def traverse(node: DocNode, current_path: str):
            """递归遍历文档树，计算预期文件路径"""
            # 当前文档的文件路径
            safe_title = "".join(c for c in node.title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_title:
                safe_title = node.id
            if len(safe_title) > 100:
                safe_title = safe_title[:100]

            filename = f"{safe_title}_{node.id}.md"
            file_path = os.path.join(current_path, filename)
            expected_files.add(file_path)

            # 处理子文档
            if node.children:
                safe_folder_name = "".join(c for c in node.title if c.isalnum() or c in (' ', '-', '_')).strip()
                if not safe_folder_name:
                    safe_folder_name = node.id
                if len(safe_folder_name) > 100:
                    safe_folder_name = safe_folder_name[:100]

                child_path = os.path.join(current_path, safe_folder_name)
                for child in node.children:
                    traverse(child, child_path)

        for doc_node in notebook_node.children:
            traverse(doc_node, "")

        return expected_files

    def get_expected_folders(self, notebook_node: NotebookNode) -> Set[str]:
        """
        根据当前笔记本结构，计算应该存在的文件夹路径集合

        Returns:
            相对于 notebook_dir 的文件夹路径集合
        """
        expected_folders = set()

        def traverse(node: DocNode, current_path: str):
            """递归遍历文档树，计算预期文件夹路径"""
            if node.children:
                safe_folder_name = "".join(c for c in node.title if c.isalnum() or c in (' ', '-', '_')).strip()
                if not safe_folder_name:
                    safe_folder_name = node.id
                if len(safe_folder_name) > 100:
                    safe_folder_name = safe_folder_name[:100]

                folder_path = os.path.join(current_path, safe_folder_name)
                expected_folders.add(folder_path)

                # 递归处理子文档
                for child in node.children:
                    traverse(child, folder_path)

        for doc_node in notebook_node.children:
            traverse(doc_node, "")

        return expected_folders

    def remove_orphaned_files(self, notebook_node: NotebookNode, notebook_dir: str) -> Tuple[int, int]:
        """
        删除笔记已不存在但文件仍存在的孤儿文件和文件夹

        Args:
            notebook_node: 笔记本节点
            notebook_dir: 笔记本目录路径

        Returns:
            (删除文件数, 删除文件夹数)
        """
        if not os.path.exists(notebook_dir):
            return 0, 0

        expected_files = self.get_expected_files(notebook_node)
        expected_folders = self.get_expected_folders(notebook_node)
        existing_files = self.get_existing_files(notebook_dir)

        deleted_files = 0
        deleted_folders = 0

        # 找出并删除不需要的文件
        for file_path in existing_files:
            if file_path not in expected_files:
                full_path = os.path.join(notebook_dir, file_path)
                try:
                    os.remove(full_path)
                    print(f"   🗑️  删除文件: {file_path}")
                    deleted_files += 1
                except Exception as e:
                    print(f"   ⚠️ 删除文件失败 {file_path}: {e}")

        # 找出并删除不需要的空文件夹（从下往上删）
        for root, dirs, files in os.walk(notebook_dir, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                rel_path = os.path.relpath(dir_path, notebook_dir)

                # 检查是否应该保留
                # 文件夹需要保留的条件：1. 是预期文件夹 2. 或包含预期的文件/子文件夹
                should_keep = False

                # 检查是否是预期的文件夹
                if rel_path in expected_folders:
                    should_keep = True

                # 检查是否包含预期的文件
                for expected_file in expected_files:
                    if expected_file.startswith(rel_path + os.sep):
                        should_keep = True
                        break

                # 检查是否包含预期的子文件夹
                if not should_keep:
                    for expected_folder in expected_folders:
                        if expected_folder.startswith(rel_path + os.sep):
                            should_keep = True
                            break

                if not should_keep:
                    try:
                        # 确保文件夹为空才删除（不应该有非 md 文件，但为了安全）
                        remaining_files = os.listdir(dir_path)
                        if not remaining_files or all(f.endswith('.md') for f in remaining_files):
                            shutil.rmtree(dir_path)
                            print(f"   🗑️  删除文件夹: {rel_path}")
                            deleted_folders += 1
                    except Exception as e:
                        print(f"   ⚠️ 删除文件夹失败 {rel_path}: {e}")

        return deleted_files, deleted_folders

    def sync_notebook(self, notebook_node: NotebookNode) -> Tuple[int, int, int]:
        """
        执行笔记本的增量同步分析

        Args:
            notebook_node: 笔记本节点

        Returns:
            (需要创建数, 需要更新数, 需要删除数)
        """
        record = self.load_record(notebook_node)
        new_record = NotebookSyncRecord(
            notebook_id=notebook_node.id,
            notebook_name=notebook_node.name,
            last_sync=datetime.now().isoformat(),
            docs={}
        )

        to_create = 0
        to_update = 0

        def analyze_doc(node: DocNode, file_path: str):
            """分析单个文档的同步状态"""
            nonlocal to_create, to_update

            doc_record = record.docs.get(node.id) if record else None

            if doc_record is None:
                to_create += 1
            elif node.updated > doc_record.updated:
                to_update += 1

            # 记录当前状态
            new_record.docs[node.id] = DocSyncRecord(
                doc_id=node.id,
                title=node.title,
                updated=node.updated,
                last_sync=datetime.now().isoformat(),
                file_path=file_path
            )

        def traverse(node: DocNode, current_path: str):
            """递归遍历文档树"""
            safe_title = "".join(c for c in node.title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_title:
                safe_title = node.id
            if len(safe_title) > 100:
                safe_title = safe_title[:100]

            filename = f"{safe_title}_{node.id}.md"
            file_path = os.path.join(current_path, filename)

            analyze_doc(node, file_path)

            # 处理子文档
            if node.children:
                safe_folder_name = safe_title
                child_path = os.path.join(current_path, safe_folder_name)
                for child in node.children:
                    traverse(child, child_path)

        # 遍历所有文档
        for doc_node in notebook_node.children:
            traverse(doc_node, "")

        # 计算需要删除的数量
        safe_name = self._get_safe_notebook_name(notebook_node.name, notebook_node.id)
        notebook_dir = os.path.join(self.output_dir, safe_name)

        expected_files = self.get_expected_files(notebook_node)
        existing_files = self.get_existing_files(notebook_dir) if os.path.exists(notebook_dir) else set()
        to_delete = len(existing_files - expected_files)

        return to_create, to_update, to_delete
