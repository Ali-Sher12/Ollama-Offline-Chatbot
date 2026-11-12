import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from docx import Document
from app.agent.permissions import permission_manager

def manage_docx(
    action: str,
    file_path: str,
    output_path: Optional[str] = None,
    text: Optional[str] = None,
    heading_level: Optional[int] = None,
    target_text: Optional[str] = None,
    replacement_text: Optional[str] = None,
    paragraph_index: Optional[int] = None,
    table_data: Optional[List[List[str]]] = None,
    table_index: Optional[int] = None,
    row_index: Optional[int] = None,
    col_index: Optional[int] = None,
    new_value: Optional[str] = None
) -> Dict[str, Any]:
    """
    Manipulate DOCX documents using python-docx:
    - action='read': Read all paragraphs and tables from document.
    - action='create': Create a new document with optional initial text and table.
    - action='add_paragraph': Append paragraph or heading to existing document.
    - action='replace_text': Search and replace text across paragraphs and tables.
    - action='modify_paragraph': Edit text of a specific paragraph by index.
    - action='add_table': Insert a new table with 2D rows/columns.
    - action='modify_table': Update a specific cell in an existing table.
    """
    action = action.lower().strip()
    try:
        resolved_input = permission_manager.resolve_safe_path(file_path)
        save_target = permission_manager.resolve_safe_path(output_path or file_path)
        workspace = permission_manager.get_workspace_dir()

        if action == "create":
            doc = Document()
            if text:
                if heading_level is not None:
                    doc.add_heading(text, level=heading_level)
                else:
                    doc.add_paragraph(text)

            if table_data and len(table_data) > 0:
                rows_count = len(table_data)
                cols_count = max(len(r) for r in table_data)
                tbl = doc.add_table(rows=rows_count, cols=cols_count)
                for r_idx, row in enumerate(table_data):
                    for c_idx, val in enumerate(row):
                        tbl.cell(r_idx, c_idx).text = str(val)

            save_target.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(save_target))
            return {
                "success": True,
                "action": "create",
                "file_path": str(save_target.relative_to(workspace)),
                "message": f"Successfully created document at '{save_target.relative_to(workspace)}'"
            }

        if not resolved_input.exists():
            return {"success": False, "error": f"DOCX file '{file_path}' does not exist"}

        doc = Document(str(resolved_input))

        if action == "read":
            paragraphs = []
            for i, p in enumerate(doc.paragraphs):
                if p.text.strip():
                    paragraphs.append({
                        "index": i,
                        "style": p.style.name if p.style else "",
                        "text": p.text
                    })

            tables = []
            for t_idx, table in enumerate(doc.tables):
                t_rows = []
                for row in table.rows:
                    t_rows.append([cell.text.strip() for cell in row.cells])
                tables.append({
                    "table_index": t_idx,
                    "rows_count": len(table.rows),
                    "columns_count": len(table.columns) if table.rows else 0,
                    "data": t_rows
                })

            return {
                "success": True,
                "action": "read",
                "file_path": str(resolved_input.relative_to(workspace)),
                "paragraph_count": len(paragraphs),
                "paragraphs": paragraphs,
                "table_count": len(tables),
                "tables": tables
            }

        elif action == "add_paragraph":
            if not text:
                return {"success": False, "error": "Argument 'text' is required for add_paragraph"}

            if heading_level is not None:
                new_p = doc.add_heading(text, level=heading_level)
            else:
                new_p = doc.add_paragraph(text)

            save_target.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(save_target))
            return {
                "success": True,
                "action": "add_paragraph",
                "file_path": str(save_target.relative_to(workspace)),
                "text_added": text
            }

        elif action == "modify_paragraph":
            if paragraph_index is None:
                return {"success": False, "error": "Argument 'paragraph_index' is required for modify_paragraph"}
            if paragraph_index < 0 or paragraph_index >= len(doc.paragraphs):
                return {
                    "success": False,
                    "error": f"paragraph_index {paragraph_index} is out of bounds (document has {len(doc.paragraphs)} paragraphs)"
                }
            if text is None:
                return {"success": False, "error": "Argument 'text' is required for modify_paragraph"}

            target_p = doc.paragraphs[paragraph_index]
            old_text = target_p.text
            target_p.text = text

            save_target.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(save_target))
            return {
                "success": True,
                "action": "modify_paragraph",
                "paragraph_index": paragraph_index,
                "old_text": old_text,
                "new_text": text,
                "file_path": str(save_target.relative_to(workspace))
            }

        elif action == "replace_text":
            if not target_text:
                return {"success": False, "error": "Argument 'target_text' is required for replace_text"}
            replacement = replacement_text if replacement_text is not None else ""
            replaced_count = 0

            # 1. Replace in paragraphs (preserving runs structure when possible)
            for p in doc.paragraphs:
                if target_text in p.text:
                    # Check runs first
                    run_replaced = False
                    for run in p.runs:
                        if target_text in run.text:
                            run.text = run.text.replace(target_text, replacement)
                            run_replaced = True
                            replaced_count += 1
                    if not run_replaced and target_text in p.text:
                        p.text = p.text.replace(target_text, replacement)
                        replaced_count += 1

            # 2. Replace in tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if target_text in cell.text:
                            for p in cell.paragraphs:
                                if target_text in p.text:
                                    p.text = p.text.replace(target_text, replacement)
                                    replaced_count += 1

            save_target.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(save_target))
            return {
                "success": True,
                "action": "replace_text",
                "target_text": target_text,
                "replacement_text": replacement,
                "occurrences_replaced": replaced_count,
                "file_path": str(save_target.relative_to(workspace))
            }

        elif action == "add_table":
            if not table_data or len(table_data) == 0:
                return {"success": False, "error": "Argument 'table_data' (2D array of rows) is required for add_table"}

            rows_count = len(table_data)
            cols_count = max(len(r) for r in table_data)
            tbl = doc.add_table(rows=rows_count, cols=cols_count)
            tbl.style = "Table Grid"

            for r_idx, row in enumerate(table_data):
                for c_idx, val in enumerate(row):
                    tbl.cell(r_idx, c_idx).text = str(val)

            save_target.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(save_target))
            return {
                "success": True,
                "action": "add_table",
                "rows": rows_count,
                "columns": cols_count,
                "file_path": str(save_target.relative_to(workspace))
            }

        elif action == "modify_table":
            if table_index is None or row_index is None or col_index is None:
                return {"success": False, "error": "Arguments 'table_index', 'row_index', and 'col_index' are required"}
            if table_index < 0 or table_index >= len(doc.tables):
                return {"success": False, "error": f"table_index {table_index} is out of bounds"}

            tbl = doc.tables[table_index]
            if row_index < 0 or row_index >= len(tbl.rows):
                return {"success": False, "error": f"row_index {row_index} is out of bounds"}
            if col_index < 0 or col_index >= len(tbl.columns):
                return {"success": False, "error": f"col_index {col_index} is out of bounds"}

            cell = tbl.cell(row_index, col_index)
            old_val = cell.text
            cell.text = str(new_value if new_value is not None else "")

            save_target.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(save_target))
            return {
                "success": True,
                "action": "modify_table",
                "table_index": table_index,
                "row_index": row_index,
                "col_index": col_index,
                "old_value": old_val,
                "new_value": cell.text,
                "file_path": str(save_target.relative_to(workspace))
            }

        else:
            return {
                "success": False,
                "error": f"Unsupported DOCX action '{action}'. Valid actions: read, create, add_paragraph, modify_paragraph, replace_text, add_table, modify_table."
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
