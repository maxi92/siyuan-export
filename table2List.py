import re
import os

def convert_markdown_tables(md_text):
    """
    将包含 Markdown 表格的文本转换为对 AI 检索更友好的段落化列表格式。
    主要功能：
    1. 提取 YAML Frontmatter 中的 title 属性作为全局标题。
    2. 清除文中无用的 Markdown 图片标签。
    3. 遍历文本，将表格的每一行转化为带有层级的段落，每一列转化为“键值对”形式的列表。
    4. 自动跳过空值列或被清理后变为空的列。
    """
    output_lines = []
    
    # 1. 处理 Frontmatter 提取 title 属性
    # 使用正则表达式匹配位于文件开头，由 '---' 包裹的 Frontmatter 区域。
    # re.DOTALL 允许 '.' 匹配换行符，以获取完整的头部块。
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = frontmatter_pattern.match(md_text)
    
    body_text = md_text
    if match:
        frontmatter_content = match.group(1)
        # 在提取出的 Frontmatter 内容中，逐行查找 'title: xxx' 格式的属性
        title_match = re.search(r'^title:\s*(.+)$', frontmatter_content, re.MULTILINE)
        if title_match:
            title_val = title_match.group(1).strip()
            output_lines.append(f"# 标题：{title_val}\n")
        # 截取掉 Frontmatter 部分，保留剩余的 Markdown 正文以供后续解析
        body_text = md_text[match.end():]
        
    # 2. 去除 Markdown 图片标签
    # 匹配标准 Markdown 图片语法 ![任意文本](任意链接) 并将其替换为空字符串
    body_text = re.sub(r'!\[.*?\]\(.*?\)', '', body_text)
        
    # 3. 逐行解析正文文本
    lines = body_text.split('\n')
    in_table = False    # 用于标记当前是否处于表格解析状态
    headers = []        # 存储当前表格的表头列名
    row_count = 1       # 记录当前表格的有效数据行数（用于生成子标题）
    
    for line in lines:
        strip_line = line.strip()
        
        # 判断当前行是否为表格行（以 '|' 开头并以 '|' 结尾）
        if strip_line.startswith('|') and strip_line.endswith('|'):
            if not in_table:
                # 首次遇到表格行，视为表头行。切片 [1:-1] 是为了去除 split 产生的首尾空字符串
                in_table = True
                headers = [h.strip() for h in strip_line.split('|')[1:-1]]
                row_count = 1
            else:
                # 检查是否为表头下方的格式分割线（主要包含 -、:、空格等），如果是则跳过
                if re.match(r'^\|[\s\-:|]+\|$', strip_line):
                    continue 
                    
                # 解析常规数据行，提取各个单元格的内容
                cells = [c.strip() for c in strip_line.split('|')[1:-1]]
                
                # 取表头数量和数据列数的最小值，防止由于表格书写不规范导致的数组越界
                col_count = min(len(headers), len(cells))
                
                # 如果整行数据全部为空，则直接跳过该行，不生成记录
                if not any(cells):
                    continue
                    
                # 为每行数据生成一个唯一的子标题
                output_lines.append(f"## 第{row_count}条记录")
                for i in range(col_count):
                    val = cells[i]
                    if val:
                        # 将表格中用于换行的 <br/> 标签替换为真实的 Markdown 换行，并增加缩进以保持列表层级
                        val_cleaned = val.replace('<br/>', '\n  ').strip()
                        # 再次判断清理后的字符串是否为空（例如图片标签被去除后可能只剩空白），非空才输出
                        if val_cleaned:
                            output_lines.append(f"- **{headers[i]}**: {val_cleaned}")
                
                # 每条记录解析完成后增加一个空行，保证最终 Markdown 排版清晰
                output_lines.append("") 
                row_count += 1
        else:
            # 遇到非表格行时，重置表格解析状态
            if in_table:
                in_table = False
                headers = []
                row_count = 1
            # 原样输出非表格的普通文本
            output_lines.append(line)
            
    # 将所有处理后的行合并为最终的纯文本内容
    return '\n'.join(output_lines)

def main():
    """
    主控函数，负责文件的读取、数据预处理、调用转换逻辑以及结果保存。
    """
    input_filename = 'input.md'
    output_filename = 'output.md'

    # 校验当前目录下是否存在待处理的源文件
    if not os.path.exists(input_filename):
        print(f"错误：找不到名为 '{input_filename}' 的文件。")
        return

    try:
        # 读取原始 Markdown 文件
        with open(input_filename, 'r', encoding='utf-8') as f:
            raw_markdown = f.read()
            
        # 核心修复步骤：将部分笔记软件导出时产生的字面字符串 '\n' 还原为真实的物理换行符
        # 这一步是使得表格解析逻辑能够正确按行切割的前提
        raw_markdown = raw_markdown.replace('\\n', '\n')
        
    except Exception as e:
        print(f"读取文件时发生错误：{e}")
        return

    print("开始转换 Markdown 表格数据...")
    # 调用核心转换逻辑
    converted_markdown = convert_markdown_tables(raw_markdown)

    try:
        # 将转换并重新排版后的数据写入到目标文件中
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(converted_markdown)
        print(f"转换成功！结果已保存至 '{output_filename}' 文件中。")
    except Exception as e:
        print(f"写入文件时发生错误：{e}")

if __name__ == "__main__":
    main()