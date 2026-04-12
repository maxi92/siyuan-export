"""
Markdown 后处理工具

功能：将包含 Markdown 表格的文本转换为对 AI 检索更友好的段落化列表格式。
"""

import re


def convert_markdown_tables(md_text: str) -> str:
    """
    将包含 Markdown 表格的文本转换为对 AI 检索更友好的段落化列表格式。

    主要功能：
    1. 提取 YAML Frontmatter 中的 title 属性作为全局标题。
    2. 清除文中无用的 Markdown 图片标签。
    3. 遍历文本，将表格的每一行转化为带有层级的段落，每一列转化为"键值对"形式的列表。
    4. 自动跳过空值列或被清理后变为空的列。
    """
    output_lines = []

    # 1. 处理 Frontmatter 提取 title 属性
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = frontmatter_pattern.match(md_text)

    body_text = md_text
    if match:
        frontmatter_content = match.group(1)
        title_match = re.search(r'^title:\s*(.+)$', frontmatter_content, re.MULTILINE)
        if title_match:
            title_val = title_match.group(1).strip()
            output_lines.append(f"# 标题：{title_val}\n")
        body_text = md_text[match.end():]

    # 2. 去除 Markdown 图片标签
    body_text = re.sub(r'!\[.*?\]\(.*?\)', '', body_text)

    # 3. 逐行解析正文文本
    lines = body_text.split('\n')
    in_table = False
    headers = []
    row_count = 1

    for line in lines:
        strip_line = line.strip()

        if strip_line.startswith('|') and strip_line.endswith('|'):
            if not in_table:
                in_table = True
                headers = [h.strip() for h in strip_line.split('|')[1:-1]]
                row_count = 1
            else:
                # 跳过分割线
                if re.match(r'^\|[\s\-:|]+\|$', strip_line):
                    continue

                cells = [c.strip() for c in strip_line.split('|')[1:-1]]
                col_count = min(len(headers), len(cells))

                if not any(cells):
                    continue

                output_lines.append(f"## 第{row_count}条记录")
                for i in range(col_count):
                    val = cells[i]
                    if val:
                        val_cleaned = val.replace('<br/>', '\n  ').strip()
                        if val_cleaned:
                            output_lines.append(f"- **{headers[i]}**: {val_cleaned}")

                output_lines.append("")
                row_count += 1
        else:
            if in_table:
                in_table = False
                headers = []
                row_count = 1
            output_lines.append(line)

    return '\n'.join(output_lines)


def preprocess_markdown(raw_markdown: str) -> str:
    """
    预处理 Markdown 文本：还原字面 '\\n' 为真实换行符，再执行表格转换。

    Args:
        raw_markdown: 原始 Markdown 字符串

    Returns:
        处理后的 Markdown 字符串
    """
    # 将部分笔记软件导出时产生的字面字符串 '\\n' 还原为真实换行符
    processed = raw_markdown.replace('\\n', '\n')
    return convert_markdown_tables(processed)
