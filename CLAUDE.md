# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

思源笔记导出工具 (SiYuan Note Exporter) - A Python tool that calls the SiYuan Note API to export notebook structures to JSON and Markdown.

Key capabilities:
- Fetches notebook list via `/api/notebook/lsNotebooks`
- Queries all documents per notebook via `/api/query/sql`
- Builds hierarchical tree structure from flat document data
- Exports tree structure to JSON
- **Exports random document Markdown content via `/api/export/exportMdContent`**
- **Exports specific document Markdown by `--doc-id`**
- **Converts Markdown tables to list format for better AI readability**

## Common Development Commands

### Running the tool
```bash
# Basic usage (requires SiYuan Note running with API enabled)
./run.sh --token your_api_token

# With custom output directory
./run.sh --token your_api_token --output ./export

# With remote SiYuan instance
./run.sh --token your_api_token --base-url http://192.168.1.100:6806

# Export specific document by ID (with table-to-list conversion)
./run.sh --token your_api_token --doc-id 20240806202611-ecxtzjt
```

### Installing dependencies
```bash
# One-command install (creates venv and installs deps)
./install.sh

# Or manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Getting API Token
In SiYuan Note: Settings → About → API Token

## High-Level Architecture

### Core Components

**SiYuanClient** (`siyuan_exporter/client.py`)
- Handles HTTP communication with SiYuan API
- `get_notebooks()`: Returns list of active (non-closed) notebooks
- `get_docs_by_notebook(notebook_id)`: Executes SQL query to fetch all documents in a notebook
- `get_doc_markdown(doc_id)`: Fetches Markdown content for a specific document via `/api/export/exportMdContent`
- API uses Token auth in `Authorization` header
- Default base URL: `http://127.0.0.1:6806`

**TreeBuilder** (`siyuan_exporter/tree_builder.py`)
- Transforms flat document list into hierarchical tree
- Key dataclasses: `NotebookNode`, `DocNode`
- Tree building logic:
  1. Creates `DocNode` for each document
  2. Parses `path` field to determine parent-child relationships
  3. Attaches children to parents based on ID matching
- Path format: `/notebookID/parentID/docID.sy` (parentID may repeat for nested docs)

**MarkdownProcessor** (`siyuan_exporter/markdown_processor.py`)
- Post-processes exported Markdown for better AI readability
- `convert_markdown_tables(md_text)`: Converts Markdown tables to hierarchical list format
  - Extracts YAML Frontmatter title as document header
  - Removes Markdown image tags
  - Transforms each table row into a numbered record section
  - Converts columns to `**key**: value` list items
- `preprocess_markdown(raw_markdown)`: Preprocesses raw content (converts literal `\n` to newlines)

**Main** (`main.py`)
- CLI entry point with argparse
- Arguments:
  - `--token` (required): API Token
  - `--base-url`: SiYuan API address (default: `http://127.0.0.1:6806`)
  - `--output`: Output directory (default: `./output`)
  - `--doc-id`: Specific document ID to export (optional)
- Workflow:
  1. Fetch notebooks → fetch docs per notebook → build trees
  2. Print tree to console + export JSON
  3. Export random document Markdown (with table conversion)
  4. **If `--doc-id` provided: export specific document Markdown (with table conversion)**
- Output:
  - Tree structure: `output/siyuan_tree_YYYYMMDD_HHMMSS.json`
  - Random document Markdown: `output/{title}_{doc_id}.md`
  - **Specific document Markdown (when `--doc-id` used): `output/{title}_{doc_id}.md`**

### SiYuan API Structure

**SQL Query for documents:**
```sql
select id, content, updated, path from blocks
where box='${notebook_id}' and type='d'
order by updated asc
```

**Document fields:**
- `id`: Unique document ID (e.g., `20250311204950-6dq3vcj`)
- `content`: Document title
- `path`: File path containing hierarchy info (e.g., `/20240806202611-ecxtzjt/20250311204950-6dq3vcj.sy`)
- `updated`: Timestamp

**Building hierarchy from paths:**
- Path segments (excluding `.sy` suffix) represent the ID chain
- Last segment = current document ID
- Second-to-last segment = direct parent document ID
- Single segment after notebook ID = top-level document

### Markdown Export Feature

**API Endpoint:** `POST /api/export/exportMdContent`

**Request body:**
```json
{
    "id": "20241007023356-ciuje9u"
}
```

**Response structure:**
```json
{
    "code": 0,
    "msg": "",
    "data": {
        "content": "# Document Title\n\nMarkdown content...",
        "hPath": "/notebook/path"
    }
}
```

**Implementation details:**
- Random document selection using `random.choice()` from collected documents
- Specific document export via `--doc-id` parameter
- Safe filename generation (alphanumeric, spaces, hyphens, underscores only)
- File naming format: `{safe_title}_{doc_id}.md`
- Output directory: same as JSON export (default: `./output`)
- **All exported Markdown goes through `preprocess_markdown()` for table-to-list conversion**

### Data Flow

```
SiYuan API → notebook list
    ↓
For each notebook: SQL query → flat doc list
    ↓
TreeBuilder: path analysis → hierarchical tree
    ↓
Console output + JSON export
    ↓
Random selection → /api/export/exportMdContent → preprocess_markdown() → Markdown file export
    ↓
(Alternative) --doc-id provided → /api/export/exportMdContent → preprocess_markdown() → Markdown file export
```

**Markdown Post-Processing Pipeline:**
1. Replace literal `\n` strings with actual newlines
2. Extract YAML Frontmatter title as `# 标题：xxx`
3. Remove Markdown image tags `![...](...)`
4. Convert tables to hierarchical lists:
   - Each row becomes `## 第N条记录`
   - Each column becomes `- **header**: value`

### Next Planned Features

Based on README.md roadmap:
- ~~Export document content as Markdown files~~ ✅ Implemented (random/single document export with table-to-list conversion)
- ~~Post-process Markdown for AI readability~~ ✅ Implemented (table-to-list conversion, image removal, YAML frontmatter extraction)
- Export all documents as Markdown files (full export)
- Support image/resource file export
- Support sync/update functionality
