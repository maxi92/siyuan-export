"""
Markdown 后处理工具

功能：将包含 Markdown 表格的文本转换为对 AI 检索更友好的段落化列表格式。

处理规则：
1. 提取 YAML Frontmatter 中的 title 属性作为全局标题。
2. 清除正文中的 Markdown 图片标签（代码块内原样保留）。
3. 将表格逐行转化为「键值对」列表，每条记录一个标题；记录编号在同一文档内全局递增，
   避免多个表格出现重复的「第1条记录」。
4. 代码围栏（``` 或 ~~~）内部的内容原样透传，不做任何转换。
5. 正确处理单元格内的转义管道（\\|）和 <br>/<br/>/<br /> 换行标签。

注意：早期版本会在预处理时把字面 '\\n' 替换为真实换行符。经全库实测，
思源 exportMdContent 的输出不含字面 '\\n'（0/119 篇），该替换没有作用，
反而会损坏代码块内的 '\\n' 字面量，因此已移除。
"""

import re

# 代码围栏起始/结束行，如 ``` 或 ~~~（可带语言标记）
_FENCE_RE = re.compile(r'^(`{3,}|~{3,})')
# 表格格式分割线，如 | --- | :---: | ---: |
_TABLE_SEP_RE = re.compile(r'^\|[\s\-:|]+\|$')
# 未转义的管道符（前面不是反斜杠），用于切分单元格
_UNESCAPED_PIPE_RE = re.compile(r'(?<!\\)\|')
# <br> 的三种常见写法
_BR_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)
# Markdown 图片标签
_IMAGE_RE = re.compile(r'!\[.*?\]\(.*?\)')


def _split_row(strip_line: str) -> list:
    """切分表格行内的单元格，正确处理转义管道，并还原 '\\|' 为 '|'。"""
    cells = _UNESCAPED_PIPE_RE.split(strip_line)[1:-1]
    return [c.replace('\\|', '|').strip() for c in cells]


def _record_discriminator(cells: list, col_count: int) -> str:
    """
    从一行的单元格中提取记录判别信息（用于「第N条记录」标题）。

    取第一个非空的、非纯数字的单元格值——记录型表格的第一列通常是序号，
    「第3条记录：1」没有检索价值，「第3条记录：川香芽菜风味意面」才有。
    全部为纯数字时退回第一个非空值。超长截断。
    """
    first_any = ""
    for i in range(col_count):
        val = cells[i]
        if not val:
            continue
        d = _BR_RE.sub(' ', val)
        d = re.sub(r'[*`#\[\]]', '', d).strip()
        d = re.sub(r'\s+', ' ', d)
        if not d:
            continue
        if not first_any:
            first_any = d
        if not d.isdigit():
            return d[:40]
    return first_any[:40]


def convert_markdown_tables(md_text: str) -> str:
    """
    将包含 Markdown 表格的文本转换为对 AI 检索更友好的段落化列表格式。
    """
    output_lines = []

    # 1. 处理 Frontmatter 提取 title 属性
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = frontmatter_pattern.match(md_text)

    body_text = md_text
    title_val = ""
    if match:
        frontmatter_content = match.group(1)
        title_match = re.search(r'^title:\s*(.+)$', frontmatter_content, re.MULTILINE)
        if title_match:
            title_val = title_match.group(1).strip().strip('"\'')
            output_lines.append(f"# 标题：{title_val}\n")
        body_text = md_text[match.end():]

    # 2. 逐行解析正文文本
    lines = body_text.split('\n')

    # 2a. 顶部重复标题去重：若正文第一个非空行就是标题本身（frontmatter
    #     已提取为「# 标题：X」，正文常再带一个相同的 H1），则去掉正文里那个
    if title_val:
        for idx, ln in enumerate(lines):
            s = ln.strip()
            if not s:
                continue
            if s in (f"# {title_val}", f"# 标题：{title_val}"):
                lines = lines[:idx] + lines[idx + 1:]
            break  # 只检查第一个非空行

    in_code = False      # 是否处于代码围栏内部
    fence_marker = ""    # 当前围栏的起始标记（``` 或 ~~~）
    in_table = False
    headers = []
    record_no = 0        # 记录编号在整篇文档内全局递增，不按表格重置

    for line in lines:
        strip_line = line.strip()

        # 代码围栏状态机：进入/退出围栏，围栏内原样透传
        fence_match = _FENCE_RE.match(strip_line)
        if fence_match:
            if not in_code:
                in_code = True
                fence_marker = fence_match.group(1)
            elif strip_line.startswith(fence_marker):
                in_code = False
                fence_marker = ""
            output_lines.append(line)
            continue
        if in_code:
            output_lines.append(line)
            continue

        # 围栏外：清除图片标签
        line = _IMAGE_RE.sub('', line)
        strip_line = line.strip()

        # 3. 表格行解析
        if strip_line.startswith('|') and strip_line.endswith('|') and strip_line != '|':
            if not in_table:
                in_table = True
                headers = _split_row(strip_line)
            elif _TABLE_SEP_RE.match(strip_line):
                continue
            else:
                cells = _split_row(strip_line)
                col_count = min(len(headers), len(cells))

                if not any(cells):
                    continue

                record_no += 1
                disc = _record_discriminator(cells, col_count)
                if disc:
                    output_lines.append(f"## 第{record_no}条记录：{disc}")
                else:
                    output_lines.append(f"## 第{record_no}条记录")
                for i in range(col_count):
                    val = cells[i]
                    if val:
                        val_cleaned = _BR_RE.sub('\n  ', val).strip()
                        if val_cleaned:
                            output_lines.append(f"- **{headers[i]}**: {val_cleaned}")

                output_lines.append("")
        else:
            if in_table:
                in_table = False
                headers = []
            output_lines.append(line)

    return '\n'.join(output_lines)


# 零宽/不可见字符：思源文档常见，肉眼为空但会让文本判定失效
_INVISIBLE_RE = re.compile(r'[\u200b\u200c\u200d\u2060\ufeff]')


def _yaml_quote(value: str) -> str:
    """YAML 双引号安全转义。"""
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'


def build_frontmatter(title: str = "", source: str = "", updated: str = "") -> str:
    """
    生成 YAML frontmatter 块。字段值全部用双引号包裹，避免标题中的
    冒号、引号等字符破坏 YAML 语法。无任何字段时返回空串。
    """
    lines = ["---"]
    if title:
        lines.append(f"title: {_yaml_quote(title)}")
    if source:
        lines.append(f"source: {_yaml_quote(source)}")
    if updated:
        lines.append(f"updated: {_yaml_quote(updated)}")
    lines.append("---")
    return "\n".join(lines) if len(lines) > 2 else ""


def prepend_frontmatter(md_text: str, title: str = "", source: str = "", updated: str = "") -> str:
    """在处理完成的 Markdown 顶部插入 frontmatter（须在 is_empty_document 判定之后调用）。"""
    fm = build_frontmatter(title, source, updated)
    if not fm:
        return md_text
    return fm + "\n\n" + md_text


def is_empty_document(md_text: str) -> bool:
    """
    判断文档是否为"纯容器"：正文除标题、分隔线外没有任何实际内容。

    这类文档在思源里只为挂载子文档而存在，导出后进知识库只会产生
    噪声 chunk，应跳过。判定前先剔除零宽字符——思源文档里这类
    不可见字符很常见，肉眼是空的但字符串非空。
    """
    for line in md_text.split('\n'):
        s = _INVISIBLE_RE.sub('', line).strip()
        if not s:
            continue
        if s.startswith('#'):      # 标题行不算正文
            continue
        if s in ('---', '***'):    # 分隔线不算正文
            continue
        return False
    return True


def preprocess_markdown(raw_markdown: str) -> str:
    """
    预处理 Markdown 文本并执行表格转换。

    早期版本会在此处把字面 '\\n' 还原为真实换行符，经全库实测思源导出内容
    不含字面 '\\n'，且该替换会损坏代码块内容，已移除。函数名保留以维持调用兼容。
    """
    return convert_markdown_tables(raw_markdown)
