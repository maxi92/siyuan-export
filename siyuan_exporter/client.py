"""
思源笔记 API 客户端
"""

import requests
from typing import List, Dict, Any, Optional


class SiYuanClient:
    """思源笔记 API 客户端"""

    def __init__(self, token: str, base_url: str = "http://127.0.0.1:6806"):
        """
        初始化客户端

        Args:
            token: API Token（在思源笔记设置-关于-API Token 处获取）
            base_url: API 基础地址，默认 http://127.0.0.1:6806
        """
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }

    def get_notebooks(self) -> List[Dict[str, Any]]:
        """
        获取所有笔记本列表

        Returns:
            笔记本列表，每个笔记本包含 id, name, icon, sort, closed 等字段
        """
        url = f"{self.base_url}/api/notebook/lsNotebooks"

        try:
            response = requests.post(url, json={}, headers=self.headers, timeout=30)
            response.raise_for_status()
            resp_json = response.json()

            if resp_json.get("code") == 0 and "data" in resp_json:
                notebooks = resp_json["data"].get("notebooks", [])
                # 过滤掉已关闭的笔记本
                return [nb for nb in notebooks if not nb.get("closed", False)]
            else:
                print(f"获取笔记本列表失败: {resp_json.get('msg', '未知错误')}")
                return []

        except requests.exceptions.ConnectionError:
            print(f"连接失败，请确保思源笔记已启动并开启了 API 服务")
            return []
        except requests.exceptions.Timeout:
            print(f"请求超时")
            return []
        except Exception as e:
            print(f"获取笔记本列表时出错: {e}")
            return []

    def get_docs_by_notebook(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        通过 SQL 查询获取指定笔记本下的所有文档

        Args:
            notebook_id: 笔记本 ID

        Returns:
            文档列表，每个文档包含 id, content(标题), updated, path 字段
        """
        url = f"{self.base_url}/api/query/sql"

        # 构建 SQL 查询语句
        stmt = f"select id, content, updated, path from blocks where box='{notebook_id}' and type='d' order by updated asc"

        body = {"stmt": stmt}

        try:
            response = requests.post(url, json=body, headers=self.headers, timeout=30)
            response.raise_for_status()
            resp_json = response.json()

            if resp_json.get("code") == 0 and "data" in resp_json:
                return resp_json["data"]
            else:
                print(f"查询文档失败: {resp_json.get('msg', '未知错误')}")
                return []

        except requests.exceptions.ConnectionError:
            print(f"连接失败，请确保思源笔记已启动并开启了 API 服务")
            return []
        except requests.exceptions.Timeout:
            print(f"请求超时")
            return []
        except Exception as e:
            print(f"查询文档时出错: {e}")
            return []
