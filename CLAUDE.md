# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

思源笔记导出工具 (SiYuan Note Exporter) - A Python tool that calls the SiYuan Note API to export notebook structures to JSON.

Key capabilities:
- Fetches notebook list via `/api/notebook/lsNotebooks`
- Queries all documents per notebook via `/api/query/sql`
- Builds hierarchical tree structure from flat document data
- Exports tree structure to JSON

## Common Development Commands

### Running the tool
```bash
# Basic usage (requires SiYuan Note running with API enabled)
python main.py --token your_api_token

# With custom output directory
python main.py --token your_api_token --output ./export

# With remote SiYuan instance
python main.py --token your_api_token --base-url http://192.168.1.100:6806
```

### Installing dependencies
```bash
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

**Main** (`main.py`)
- CLI entry point with argparse
- Workflow: fetch notebooks → fetch docs per notebook → build trees → print to console → export JSON
- Output: `output/siyuan_tree_YYYYMMDD_HHMMSS.json`

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

### Data Flow

```
SiYuan API → notebook list
    ↓
For each notebook: SQL query → flat doc list
    ↓
TreeBuilder: path analysis → hierarchical tree
    ↓
Console output + JSON export
```

### Next Planned Features

Based on README.md roadmap:
- Export document content as Markdown files
- Support image/resource file export
- Support sync/update functionality
