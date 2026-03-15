# 思源笔记导出工具

调用思源笔记 API，将笔记导出为树形结构的 Python 工具。

## 功能特性

- ✅ 获取所有笔记本列表
- ✅ 获取每个笔记本下的所有文档
- ✅ 根据文档路径自动构建树形结构
- ✅ 支持多级嵌套笔记（笔记下再建笔记）
- ✅ 导出为 JSON 格式

## 安装

### 环境要求

- Python 3.7+
- 思源笔记已启动并开启 API 服务

### 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 获取 API Token

在思源笔记中：
1. 打开 **设置** → **关于**
2. 找到 **API Token** 并复制

### 2. 运行程序

```bash
python main.py --token your_token_here
```

### 命令行参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--token` | 是 | - | 思源笔记 API Token |
| `--base-url` | 否 | http://127.0.0.1:6806 | 思源笔记 API 地址 |
| `--output` | 否 | ./output | 输出目录 |

### 示例

```bash
# 基本用法
python main.py --token your_token_here

# 指定输出目录
python main.py --token your_token_here --output ./my_export

# 使用自定义 API 地址
python main.py --token your_token_here --base-url http://192.168.1.100:6806
```

## 输出示例

程序运行后会输出：

1. **控制台输出**：树形结构的可视化展示
2. **JSON 文件**：位于 `output/siyuan_tree_YYYYMMDD_HHMMSS.json`

### 树形结构示例

```
🌲 笔记树形结构
==================================================
📒 笔记本名称 (ID: 20240806202611-ecxtzjt)
  📄 一级笔记标题 (ID: 20250311204950-6dq3vcj)
    📄 二级笔记标题 (ID: 20250311205000-abc123)
      📄 三级笔记标题 (ID: 20250311205010-def456)
  📄 另一个一级笔记 (ID: 20250311205100-xyz789)

📊 统计摘要
==================================================
📒 笔记本名称: 3 篇文档

总计: 1 个笔记本, 3 篇文档
```

### JSON 结构示例

```json
[
  {
    "id": "20240806202611-ecxtzjt",
    "name": "笔记本名称",
    "icon": "",
    "children": [
      {
        "id": "20250311204950-6dq3vcj",
        "title": "一级笔记标题",
        "updated": "20250311205339",
        "path": "/20240806202611-ecxtzjt/20250311204950-6dq3vcj.sy",
        "level": 0,
        "children": [
          {
            "id": "20250311205000-abc123",
            "title": "二级笔记标题",
            "updated": "20250311205400",
            "path": "/20240806202611-ecxtzjt/20250311204950-6dq3vcj/20250311205000-abc123.sy",
            "level": 1,
            "children": []
          }
        ]
      }
    ]
  }
]
```

## 项目结构

```
siyuan-export/
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖项
├── README.md              # 项目说明
└── siyuan_exporter/       # 核心模块
    ├── __init__.py
    ├── client.py          # API 客户端
    └── tree_builder.py    # 树形结构构建器
```

## 原理说明

思源笔记的文档路径结构如下：

```
/笔记本ID/父笔记ID/子笔记ID/当前笔记ID.sy
```

例如：
```
/20240806202611-ecxtzjt/20250311204950-6dq3vcj.sy
```

- `20240806202611-ecxtzjt` 是笔记本 ID
- `20250311204950-6dq3vcj` 是当前笔记 ID
- 如果有更多层级，中间会有更多的 ID

本工具通过分析 `path` 字段，自动构建出完整的树形层级关系。

## 下一步计划

- [ ] 导出笔记内容为 Markdown 文件
- [ ] 支持图片和资源文件导出
- [ ] 支持笔记内容同步更新

## 许可证

MIT License
