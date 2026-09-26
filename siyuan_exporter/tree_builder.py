"""
树形结构构建器
用于将思源笔记的扁平数据转换为树形结构
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

# Windows 文件名非法字符 + 控制字符
_INVALID_FS_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
# Windows 保留设备名（不分大小写，可带扩展名）
_RESERVED_NAMES = re.compile(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..+)?$')


def sanitize_filename(title: str, fallback: str = "", max_len: int = 100) -> str:
    """
    将笔记标题清洗为安全的文件/文件夹名。

    这是全项目唯一的文件名清洗实现，所有需要生成文件名或文件夹名的地方
    都必须调用本函数，禁止各自内联实现——否则增量同步的孤儿清理会因
    路径规则不一致而误删文件。

    清洗策略：保留中文及全角标点（：《》！？、等在 Windows 文件名中合法，
    且导入知识库后文件名即文档标题，标点影响检索质量），只剔除
    Windows 真正非法的字符（\\ / : * ? " < > | 及控制字符），
    处理保留设备名（CON/PRN 等）与结尾的点和空格。

    Args:
        title: 笔记标题
        fallback: 清洗后为空时使用的兜底名（通常传文档 ID）
        max_len: 最大长度限制

    Returns:
        清洗后的文件名（不含扩展名）
    """
    safe = _INVALID_FS_CHARS.sub('', title).strip()
    safe = safe.rstrip('. ')
    if not safe:
        safe = fallback
    if _RESERVED_NAMES.match(safe):
        safe = '_' + safe
    if len(safe) > max_len:
        safe = safe[:max_len].rstrip('. ')
    return safe


@dataclass
class DocNode:
    """文档节点"""
    id: str
    title: str
    updated: str
    path: str
    children: List['DocNode'] = field(default_factory=list)
    level: int = 0  # 层级，0表示笔记本下的直接子文档

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "updated": self.updated,
            "path": self.path,
            "level": self.level,
            "children": [child.to_dict() for child in self.children]
        }


@dataclass
class NotebookNode:
    """笔记本节点"""
    id: str
    name: str
    icon: str = ""
    children: List[DocNode] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "children": [child.to_dict() for child in self.children]
        }


class TreeBuilder:
    """树形结构构建器"""

    @staticmethod
    def parse_doc_path(path: str) -> List[str]:
        """
        解析文档路径，提取各级父文档 ID

        Args:
            path: 文档路径，例如：/20240806202611-ecxtzjt/20250311204950-6dq3vcj.sy

        Returns:
            各级 ID 列表，例如：['20240806202611-ecxtzjt', '20250311204950-6dq3vcj']
        """
        # 移除末尾的 .sy 后缀
        clean_path = path.replace('.sy', '')
        # 按 / 分割，过滤空字符串
        parts = [p for p in clean_path.split('/') if p]
        return parts

    @staticmethod
    def get_parent_id_from_path(path: str) -> Optional[str]:
        """
        从路径中获取直接父文档的 ID

        Args:
            path: 文档路径

        Returns:
            父文档 ID，如果没有父文档则返回 None
        """
        parts = TreeBuilder.parse_doc_path(path)
        if len(parts) >= 2:
            # 倒数第二个就是直接父文档
            return parts[-2]
        return None

    @staticmethod
    def build_notebook_tree(notebook_id: str, notebook_name: str, notebook_icon: str,
                           docs: List[Dict[str, Any]]) -> NotebookNode:
        """
        构建单个笔记本的树形结构

        Args:
            notebook_id: 笔记本 ID
            notebook_name: 笔记本名称
            notebook_icon: 笔记本图标
            docs: 该笔记本下的所有文档列表

        Returns:
            笔记本节点，包含树形结构的子文档
        """
        notebook = NotebookNode(
            id=notebook_id,
            name=notebook_name,
            icon=notebook_icon
        )

        # 创建 ID -> DocNode 的映射，用于快速查找
        node_map: Dict[str, DocNode] = {}

        # 首先，为每个文档创建节点
        for doc in docs:
            doc_id = doc.get("id", "")
            if not doc_id:
                continue

            node = DocNode(
                id=doc_id,
                title=doc.get("content", "无标题"),
                updated=doc.get("updated", ""),
                path=doc.get("path", "")
            )
            node_map[doc_id] = node

        # 然后，建立父子关系
        for doc in docs:
            doc_id = doc.get("id", "")
            path = doc.get("path", "")

            if not doc_id or doc_id not in node_map:
                continue

            node = node_map[doc_id]
            parent_id = TreeBuilder.get_parent_id_from_path(path)

            if parent_id and parent_id in node_map:
                # 有父文档，添加到父文档的子列表中
                parent = node_map[parent_id]
                node.level = parent.level + 1
                parent.children.append(node)
            else:
                # 没有父文档，是笔记本的直接子文档
                node.level = 0
                notebook.children.append(node)

        return notebook

    @staticmethod
    def print_tree(notebook: NotebookNode, indent: str = ""):
        """
        打印树形结构（用于调试）

        Args:
            notebook: 笔记本节点
            indent: 缩进字符串
        """
        icon = notebook.icon if notebook.icon else "📒"
        print(f"{icon} {notebook.name} (ID: {notebook.id})")

        def print_doc_node(node: DocNode, indent: str = "  "):
            prefix = "  " * node.level
            print(f"{prefix}📄 {node.title} (ID: {node.id})")
            for child in node.children:
                print_doc_node(child, indent)

        for child in notebook.children:
            print_doc_node(child, indent)
