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
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set, Tuple

from siyuan_exporter.tree_builder import DocNode, NotebookNode


def _parse_time(time_str: str) -> Optional[datetime]:
    """统一解析时间字符串，支持 ISO 8601 和 SiYuan 的 YYYYMMDDHHMMSS 格式"""
    if not time_str:
        return None
    # ISO 8601 格式 (如 2025-04-13T12:00:00.123456)
    try:
        return datetime.fromisoformat(time_str)
    except ValueError:
        pass
    # SiYuan 格式: YYYYMMDDHHMMSS 或带毫秒 YYYYMMDDHHMMSSfff
    try:
        return datetime.strptime(time_str[:14], "%Y%m%d%H%M%S")
    except (ValueError, IndexError):
        pass
    return None


@dataclass
class NotebookSyncRecord:
    """笔记本同步记录 - 仅记录最后一次同步时间"""
    last_sync: str  # 整体上次同步时间

    def to_dict(self) -> dict:
        return {"last_sync": self.last_sync}

    @classmethod
    def from_dict(cls, data: dict) -> "NotebookSyncRecord":
        return cls(last_sync=data["last_sync"])


class SyncManager:
    """增量同步管理器"""

    def __init__(self, config_dir: str = None):
        """
        初始化同步管理器

        Args:
            config_dir: 配置目录路径，默认为项目根目录下的 .siyuan-export/sync
        """
        if config_dir is None:
            # 默认存储在项目根目录下的 .siyuan-export/sync 中
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(project_root, ".siyuan-export", "sync")

        self.config_dir = config_dir
        self._records = {}
        self._loaded = False

        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)

    def _get_sync_record_path(self, notebook_node: NotebookNode) -> str:
        """获取同步记录文件路径"""
        # 使用 notebook_id 作为文件名，避免笔记本重命名导致的问题
        return os.path.join(self.config_dir, f"{notebook_node.id}.json")

    def load_record(self, notebook_node: NotebookNode) -> Optional[NotebookSyncRecord]:
        """加载指定笔记本的同步记录（仅包含 last_sync）"""
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

    def save_record(self, notebook_node: NotebookNode):
        """保存指定笔记本的同步记录（仅记录当前时间）"""
        record_path = self._get_sync_record_path(notebook_node)
        record = NotebookSyncRecord(last_sync=datetime.now().isoformat())

        try:
            with open(record_path, 'w', encoding='utf-8') as f:
                json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"   ⚠️ 保存同步记录失败: {e}")

    def should_update(self, doc: DocNode, last_sync_time: Optional[str], file_path: str) -> bool:
        """
        判断笔记是否需要更新

        Args:
            doc: 当前笔记节点
            last_sync_time: 上次同步时间（ISO格式字符串）
            file_path: 文件完整路径

        Returns:
            是否需要更新
        """
        # 如果文件不存在，需要创建
        if not os.path.exists(file_path):
            return True

        # 如果没有同步记录，需要更新
        if last_sync_time is None:
            return True

        # 统一解析两种时间格式后再比较
        doc_updated = _parse_time(doc.updated)
        sync_time = _parse_time(last_sync_time)

        if doc_updated is not None and sync_time is not None:
            return doc_updated > sync_time

        # 回退到字符串比较（通常不正确，仅作为兜底）
        return doc.updated > last_sync_time

    def get_existing_files(self, notebook_dir: str) -> Set[str]:
        """
        获取笔记本目录下所有现有的 .md 文件路径集合

        Returns:
            相对于 notebook_dir 的文件路径集合
        """
        existing_files = set()

        for root, dirs, files in os.walk(notebook_dir):
            for file in files:
                if file.endswith('.md'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, notebook_dir)
                    existing_files.add(rel_path)

        return existing_files

    def get_expected_files(self, notebook_node: NotebookNode, duplicate_ids: Set[str] = None) -> Set[str]:
        """
        根据当前笔记本结构，计算应该存在的文件路径集合

        Args:
            notebook_node: 笔记本节点
            duplicate_ids: 需要添加 ID 后缀的文档 ID 集合

        Returns:
            相对于 notebook_dir 的文件路径集合
        """
        if duplicate_ids is None:
            duplicate_ids = set()

        expected_files = set()

        def traverse(node: DocNode, current_path: str):
            """递归遍历文档树，计算预期文件路径"""
            # 当前文档的文件路径
            safe_title = "".join(c for c in node.title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_title:
                safe_title = node.id
            if len(safe_title) > 100:
                safe_title = safe_title[:100]

            # 根据是否需要 ID 后缀生成文件名
            if node.id in duplicate_ids:
                filename = f"{safe_title}_{node.id}.md"
            else:
                filename = f"{safe_title}.md"
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

    def remove_orphaned_files(self, notebook_node: NotebookNode, notebook_dir: str, duplicate_ids: Set[str] = None) -> Tuple[int, int]:
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

        expected_files = self.get_expected_files(notebook_node, duplicate_ids)
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

