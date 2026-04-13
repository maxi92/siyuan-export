# 思源笔记导出工具

调用思源笔记 API，将笔记导出为 Markdown 文件的 Python 工具。支持按树形结构组织文件目录，并提供表格转列表的 AI 友好格式。

## 功能特性

- ✅ 获取所有笔记本列表
- ✅ 获取每个笔记本下的所有文档
- ✅ 根据文档路径自动构建树形结构
- ✅ 支持多级嵌套笔记（笔记下再建笔记）
- ✅ **导出笔记内容为 Markdown 文件**
- ✅ **批量导出笔记本下所有笔记，按树形结构组织文件目录**
- ✅ **自动将 Markdown 表格转换为列表格式，提升 AI 可读性**

## 安装

### 环境要求

- Python 3.7+
- 思源笔记已启动并开启 API 服务

### 安装依赖

```bash
# 一键安装（自动创建虚拟环境并安装依赖）
./install.sh

# 或手动安装
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 使用方法

### 1. 获取 API Token

在思源笔记中：
1. 打开 **设置** → **关于**
2. 找到 **API Token** 并复制

### 2. 运行程序

```bash
# 使用便捷脚本（自动激活虚拟环境）
./run.sh --token your_token_here

# 或手动激活虚拟环境后运行
source venv/bin/activate
python main.py --token your_token_here
```

### 命令行参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--token` | 是 | - | 思源笔记 API Token |
| `--base-url` | 否 | http://127.0.0.1:6806 | 思源笔记 API 地址 |
| `--output` | 否 | ./output | 输出目录 |
| `--doc-id` | 否 | - | 指定要导出的笔记（文档）ID |
| `--notebook-id` | 否 | - | 指定要导出的笔记本 ID（导出该笔记本下所有笔记） |
| `--all-notebooks` | 否 | - | 导出所有笔记本（与 `--notebook-id` 互斥） |
| `--sync` | 否 | - | 启用增量同步模式（需配合 `--notebook-id` 或 `--all-notebooks` 使用） |

### 示例

```bash
# 基本用法（只查看树形结构，不导出 Markdown）
./run.sh --token your_token_here

# 导出指定笔记为 Markdown
./run.sh --token your_token_here --doc-id 20240806202611-ecxtzjt

# 指定输出目录
./run.sh --token your_token_here --output ./my_export

# 使用自定义 API 地址（远程思源实例）
./run.sh --token your_token_here --base-url http://192.168.1.100:6806

# 导出指定笔记的 Markdown 内容
./run.sh --token your_token_here --doc-id 20240806202611-ecxtzjt

# 批量导出整个笔记本（按树形结构组织）
./run.sh --token your_token_here --notebook-id 20240806202611-ecxtzjt

# 增量同步模式（只导出有更新的笔记，删除已不存在的笔记）
./run.sh --token your_token_here --notebook-id 20240806202611-ecxtzjt --sync

# 导出所有笔记本
./run.sh --token your_token_here --all-notebooks

# 增量同步所有笔记本
./run.sh --token your_token_here --all-notebooks --sync
```

## 输出说明

程序运行后会输出以下内容：

1. **控制台输出**：树形结构的可视化展示和统计摘要
2. **Markdown 文件**（使用 `--doc-id`）：`思源笔记/{标题}.md`（如标题重复则添加 ID 后缀）
3. **笔记本批量导出**（使用 `--notebook-id` 或 `--all-notebooks`）：`思源笔记/{笔记本名称}/` 目录，内部按树形结构组织

### 笔记本批量导出的文件结构

使用 `--notebook-id` 参数导出时，文件按树形结构组织：

```
思源笔记/
└── 笔记本名称/
    ├── 父笔记.md              # 父笔记本身
    ├── 父笔记/                # 子笔记文件夹（与父笔记同名）
    │   ├── 子笔记1.md
    │   └── 子笔记2.md
    ├── 另一个笔记.md
    └── 另一个笔记/
        └── 子笔记3.md
```

组织规则：
- 以笔记本名称创建根文件夹
- 父笔记的 `.md` 文件与其子笔记文件夹同级
- 子笔记放在以父笔记名称命名的文件夹下
- 支持无限层级嵌套

### 增量同步模式

使用 `--sync` 参数启用增量同步，适合定期备份场景：

```bash
./run.sh --token your_token_here --notebook-id 20240806202611-ecxtzjt --sync
```

**增量同步逻辑：**

1. **创建** - 目标位置没有该笔记对应的 `.md` 文件时，自动创建
2. **更新** - 满足以下任一条件时覆盖文件：
   - 文件被手动删除后需要重新创建
   - 笔记的 `updated` 时间戳比上次同步时间更新（笔记在思源中有修改）
3. **删除** - 思源笔记中已删除的笔记，其对应的 `.md` 文件和空文件夹会被自动清理

**同步记录：**

每个笔记本的同步状态会保存在 `.siyuan-export/sync/{笔记本ID}.json` 文件中（与应用代码分离，不随导出内容一起），包含：
- 上次同步时间
- 每个笔记的 ID、标题、更新时间、文件路径

**使用场景：**

```bash
# 首次导出（全量导出）
./run.sh --token your_token --notebook-id xxx --sync

# 一周后再次运行（只导出有更新的笔记）
./run.sh --token your_token --notebook-id xxx --sync

# 添加定时任务，每天自动同步
0 2 * * * cd /path/to/siyuan-export && ./run.sh --token xxx --notebook-id xxx --sync
```

### Markdown 后处理

所有导出的 Markdown 文件会自动进行以下处理：

- **提取 YAML Frontmatter 标题**：将 frontmatter 中的 `title` 提取为文档主标题 `# 标题：xxx`
- **移除图片标签**：自动清除 `![...](...)` 格式的 Markdown 图片
- **表格转列表**：将 Markdown 表格转换为层级化的列表格式，便于 AI 处理

#### 表格转换示例

原始表格：
```markdown
| 姓名 | 年龄 | 城市 |
|------|------|------|
| 张三 | 25   | 北京 |
| 李四 | 30   | 上海 |
```

转换后：
```markdown
## 第1条记录
- **姓名**: 张三
- **年龄**: 25
- **城市**: 北京

## 第2条记录
- **姓名**: 李四
- **年龄**: 30
- **城市**: 上海
```

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

## 项目结构

```
siyuan-export/
├── main.py                      # 主程序入口
├── run.sh                       # 便捷运行脚本（自动激活虚拟环境）
├── install.sh                   # 安装脚本（创建虚拟环境并安装依赖）
├── requirements.txt             # 依赖项
├── README.md                    # 项目说明
├── CLAUDE.md                    # Claude Code 开发指南
├── venv/                        # Python 虚拟环境（自动创建）
└── siyuan_exporter/             # 核心模块
    ├── __init__.py
    ├── client.py                # API 客户端
    ├── tree_builder.py          # 树形结构构建器
    ├── markdown_processor.py    # Markdown 后处理器（表格转列表等）
    └── sync_manager.py          # 增量同步管理器
```

## 原理说明

### 思源笔记的文档路径结构

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

### API 端点

| 端点 | 用途 |
|------|------|
| `/api/notebook/lsNotebooks` | 获取笔记本列表 |
| `/api/query/sql` | 查询文档数据 |
| `/api/export/exportMdContent` | 导出笔记 Markdown 内容 |

## 下一步计划

- [x] 导出笔记内容为 Markdown 文件
- [x] 支持表格转列表格式，提升 AI 可读性
- [x] 支持批量导出笔记本下所有文档（按树形结构组织）
- [x] 支持导出所有笔记本
- [x] 支持增量同步模式（只更新有变化的笔记，删除已不存在的笔记）
- [ ] 支持图片和资源文件导出

## 许可证

MIT License
