# 思源笔记 API 调用参考

> 本文档基于 WeRead2SiYuan 项目总结，用于指导如何在 Python 项目中调用思源笔记 API

## 1. 基础配置

### 1.1 服务地址
```python
BASE_URL = "http://127.0.0.1:6806"
```
思源笔记默认在本地 6806 端口提供 API 服务。

### 1.2 认证方式
思源笔记使用 Token 进行认证，需要在请求头中携带：
```python
headers = {
    'Authorization': 'your_api_token_here',  # 在思源笔记设置-关于-API token 处获取
    'Content-Type': 'application/json'
}
```

对于文件上传接口，Authorization 格式略有不同：
```python
headers = {
    'Authorization': f'token {token}'  # 注意需要加上 "token " 前缀
}
```

---

## 2. 核心 API 列表

### 2.1 笔记本管理

#### 获取笔记本列表
```python
def get_notebook_list(token):
    """
    获取所有笔记本列表

    Returns:
        list: 笔记本列表，每个笔记本包含 id, name 等字段
    """
    url = "http://127.0.0.1:6806/api/notebook/lsNotebooks"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }

    response = requests.post(url, json={}, headers=headers)
    resp_json = response.json()

    if resp_json["code"] == 0 and "notebooks" in resp_json["data"]:
        return resp_json["data"]["notebooks"]  # 列表，每项包含 id, name 等
    return []
```

#### 创建笔记本
```python
def create_notebook(token, name):
    """
    创建新笔记本

    Args:
        token: API Token
        name: 笔记本名称

    Returns:
        str: 新创建的笔记本 ID，失败返回空字符串
    """
    url = "http://127.0.0.1:6806/api/notebook/createNotebook"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    body = {"name": name}

    response = requests.post(url, json=body, headers=headers)
    resp_json = response.json()

    if resp_json["code"] == 0 and "notebook" in resp_json["data"]:
        return resp_json["data"]["notebook"].get("id", "")
    return ""
```

---

### 2.2 文档管理

#### 搜索文档
```python
def search_docs_by_title(token, title):
    """
    根据标题搜索文档

    Args:
        token: API Token
        title: 文档标题

    Returns:
        dict: 包含 box(笔记本ID), hPath(人类可读路径), path(文档路径) 的字典
              未找到返回空字典
    """
    url = "http://127.0.0.1:6806/api/filetree/searchDocs"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    body = {"k": title}

    response = requests.post(url, json=body, headers=headers)
    resp_json = response.json()

    if resp_json["code"] == 0 and isinstance(resp_json["data"], list):
        # 筛选标题完全匹配的结果
        for item in resp_json["data"]:
            if item.get("hPath", "").split('/')[-1] == title:
                return {
                    "box": item.get("box", ""),      # 笔记本 ID
                    "hPath": item.get("hPath", ""),  # 人类可读路径
                    "path": item.get("path", "")     # 文档路径
                }
    return {}
```

#### 创建 Markdown 文档
```python
def create_doc_with_md(token, notebook_id, path, markdown_content):
    """
    使用 Markdown 内容创建文档

    Args:
        token: API Token
        notebook_id: 笔记本 ID
        path: 文档路径（如 "书籍名称" 或 "文件夹/书籍名称"）
        markdown_content: Markdown 格式的内容

    Returns:
        str: 创建的文档 ID，失败返回空字符串
    """
    url = "http://127.0.0.1:6806/api/filetree/createDocWithMd"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    body = {
        "notebook": notebook_id,
        "path": path,
        "markdown": markdown_content
    }

    response = requests.post(url, json=body, headers=headers)
    resp_json = response.json()

    if resp_json["code"] == 0 and "data" in resp_json:
        return resp_json["data"]  # 返回文档 ID
    return ""
```

#### 获取文档内容
```python
def get_doc_content(token, doc_id):
    """
    获取指定文档的内容

    Args:
        token: API Token
        doc_id: 文档 ID

    Returns:
        str: 文档内容（HTML 格式），失败返回空字符串
    """
    url = "http://127.0.0.1:6806/api/filetree/getDoc"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    body = {"id": doc_id}

    response = requests.post(url, json=body, headers=headers)
    resp_json = response.json()

    if resp_json["code"] == 0 and "data" in resp_json:
        return resp_json["data"].get("content", "")  # HTML 格式内容
    return ""
```

#### 删除文档（按 ID）
```python
def remove_doc_by_id(token, doc_id):
    """
    根据 ID 删除文档

    Args:
        token: API Token
        doc_id: 文档 ID

    Returns:
        bool: 删除成功返回 True，失败返回 False
    """
    url = "http://127.0.0.1:6806/api/filetree/removeDocByID"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    body = {"id": doc_id}

    response = requests.post(url, json=body, headers=headers)
    resp_json = response.json()

    return resp_json["code"] == 0
```

#### 删除文档（按路径）
```python
def remove_doc(token, notebook_id, path):
    """
    根据路径删除文档

    Args:
        token: API Token
        notebook_id: 笔记本 ID
        path: 文档路径

    Returns:
        bool: 删除成功返回 True，失败返回 False
    """
    url = "http://127.0.0.1:6806/api/filetree/removeDoc"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    body = {
        "notebook": notebook_id,
        "path": path
    }

    response = requests.post(url, json=body, headers=headers)
    resp_json = response.json()

    return resp_json["code"] == 0
```

---

### 2.3 块属性操作

#### 设置块属性
```python
def set_block_attributes(token, block_id, attrs):
    """
    设置指定块的属性

    Args:
        token: API Token
        block_id: 块 ID
        attrs: 属性字典，如 {"colgroup": "|width: 1200px;"}

    Returns:
        bool: 设置成功返回 True
    """
    url = "http://127.0.0.1:6806/api/attr/setBlockAttrs"
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    body = {
        "id": block_id,
        "attrs": attrs
    }

    response = requests.post(url, json=body, headers=headers)
    resp_json = response.json()

    return resp_json["code"] == 0
```

**常见用途**：调整表格宽度
```python
# 设置表格宽度为 1200px
set_block_attributes(token, block_id, {"colgroup": "|width: 1200px;"})
```

---

### 2.4 资源上传

#### 上传图片
```python
def upload_image(token, image_path, assets_dir="/assets/"):
    """
    上传图片到思源笔记

    Args:
        token: API Token
        image_path: 本地图片路径
        assets_dir: 资源存储目录，默认 /assets/

    Returns:
        str: 上传成功后的图片路径（如 /assets/image-xxx.jpg），失败返回 None
    """
    url = "http://127.0.0.1:6806/api/asset/upload"

    # 注意：上传接口的 Authorization 格式不同
    headers = {
        'Authorization': f'token {token}'
    }

    with open(image_path, 'rb') as f:
        files = [
            ('assetsDirPath', (None, assets_dir)),
            ('file[]', (os.path.basename(image_path), f)),
        ]
        response = requests.post(url, headers=headers, files=files)

    resp_json = response.json()

    if resp_json.get('code') == 0:
        succ_map = resp_json.get('data', {}).get('succMap', {})
        if succ_map:
            # 返回第一个成功上传的文件路径
            return next(iter(succ_map.values()))
    return None
```

#### 从 URL 上传图片
```python
def upload_image_from_url(token, image_url):
    """
    从 URL 下载并上传图片到思源笔记

    Args:
        token: API Token
        image_url: 图片 URL

    Returns:
        str: 上传成功后的图片路径，失败返回 None
    """
    import tempfile
    import os
    from urllib.parse import urlparse

    # 下载图片
    response = requests.get(image_url)
    if response.status_code != 200:
        return None

    # 创建临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        tmp_file.write(response.content)
        temp_file_path = tmp_file.name

    try:
        # 上传到思源笔记
        result = upload_image(token, temp_file_path)
        return result
    finally:
        # 清理临时文件
        os.remove(temp_file_path)
```

---

## 3. 完整使用示例

### 3.1 完整工作流示例
```python
import requests

class SiYuanAPI:
    def __init__(self, token, base_url="http://127.0.0.1:6806"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }

    # ========== 笔记本操作 ==========
    def get_notebooks(self):
        """获取所有笔记本"""
        url = f"{self.base_url}/api/notebook/lsNotebooks"
        resp = requests.post(url, json={}, headers=self.headers).json()
        return resp["data"]["notebooks"] if resp["code"] == 0 else []

    def create_notebook(self, name):
        """创建笔记本"""
        url = f"{self.base_url}/api/notebook/createNotebook"
        body = {"name": name}
        resp = requests.post(url, json=body, headers=self.headers).json()
        return resp["data"]["notebook"]["id"] if resp["code"] == 0 else None

    # ========== 文档操作 ==========
    def search_doc(self, title):
        """搜索文档"""
        url = f"{self.base_url}/api/filetree/searchDocs"
        body = {"k": title}
        resp = requests.post(url, json=body, headers=self.headers).json()
        if resp["code"] == 0 and resp["data"]:
            for item in resp["data"]:
                if item["hPath"].split('/')[-1] == title:
                    return item
        return None

    def create_doc(self, notebook_id, path, markdown):
        """创建文档"""
        url = f"{self.base_url}/api/filetree/createDocWithMd"
        body = {
            "notebook": notebook_id,
            "path": path,
            "markdown": markdown
        }
        resp = requests.post(url, json=body, headers=self.headers).json()
        return resp["data"] if resp["code"] == 0 else None

    def remove_doc(self, notebook_id, path):
        """删除文档"""
        url = f"{self.base_url}/api/filetree/removeDoc"
        body = {"notebook": notebook_id, "path": path}
        resp = requests.post(url, json=body, headers=self.headers).json()
        return resp["code"] == 0


# 使用示例
def main():
    api = SiYuanAPI(token="your_token_here")

    # 1. 查找或创建笔记本
    notebook_name = "我的笔记"
    notebook_id = None

    for nb in api.get_notebooks():
        if nb["name"] == notebook_name:
            notebook_id = nb["id"]
            break

    if not notebook_id:
        notebook_id = api.create_notebook(notebook_name)

    # 2. 删除已存在的同名文档
    existing = api.search_doc("测试文档")
    if existing:
        api.remove_doc(existing["box"], existing["path"])

    # 3. 创建新文档
    markdown_content = """
# 测试文档

这是一段内容。

| 列1 | 列2 |
| --- | --- |
| A   | B   |
"""
    doc_id = api.create_doc(notebook_id, "测试文档", markdown_content)
    print(f"文档创建成功，ID: {doc_id}")

if __name__ == "__main__":
    main()
```

---

## 4. 响应格式说明

### 4.1 通用响应结构
所有 API 返回 JSON 格式，统一结构如下：
```json
{
    "code": 0,        // 0 表示成功，非 0 表示失败
    "msg": "",        // 错误信息（失败时）
    "data": { }       // 返回数据（成功时）
}
```

### 4.2 笔记本数据结构
```json
{
    "id": "20240728220314-dle1lqk",
    "name": "读书笔记",
    "icon": "",           // 图标
    "sort": 0,            // 排序
    "closed": false       // 是否关闭
}
```

### 4.3 文档搜索结果结构
```json
{
    "box": "20240728220314-dle1lqk",     // 笔记本 ID
    "hPath": "/读书笔记/测试文档",        // 人类可读路径
    "path": "/20240728220314-dle1lqk/20240801120000-abc123"  // 实际路径
}
```

---

## 5. 注意事项

1. **Token 获取**：在思源笔记 设置 → 关于 → API Token 处获取
2. **服务地址**：默认 http://127.0.0.1:6806，确保思源笔记已启动并开启 API 服务
3. **文件上传认证**：上传接口的 Authorization 格式为 `token xxx`，其他接口直接使用 `xxx`
4. **路径格式**：
   - 一级文档：`文档标题`
   - 多级文档：`文件夹/子文件夹/文档标题`
5. **Markdown 支持**：思源笔记支持标准 Markdown 语法，包括表格、代码块等

---

## 6. 相关链接

- [思源笔记官网](https://b3log.org/siyuan/)
- [思源笔记 API 文档](https://github.com/siyuan-note/siyuan/blob/master/API.md)
