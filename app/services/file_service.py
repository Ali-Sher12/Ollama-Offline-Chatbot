import csv
import os
from pathlib import Path
from typing import Dict, Any, List

class FileService:
    @staticmethod
    def extract_text(file_path: Path) -> str:
        """Extract plain text from supported document and code files."""
        ext = file_path.suffix.lower()
        
        try:
            if ext == '.docx':
                from docx import Document
                doc = Document(str(file_path))
                return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
            
            elif ext == '.pdf':
                text_parts = []
                # Try pypdf first, then PyPDF2
                try:
                    import pypdf
                    reader = pypdf.PdfReader(str(file_path))
                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                except ImportError:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(str(file_path))
                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                return "\n".join(text_parts)

            elif ext == '.pptx':
                from pptx import Presentation
                prs = Presentation(str(file_path))
                text_parts = []
                for i, slide in enumerate(prs.slides):
                    slide_texts = []
                    for shape in slide.shapes:
                        if shape.has_text_frame:
                            slide_texts.append(shape.text_frame.text.strip())
                    if slide_texts:
                        text_parts.append(f"--- Slide {i+1} ---\n" + "\n".join(slide_texts))
                return "\n".join(text_parts)

            elif ext in ('.xlsx', '.xls'):
                from openpyxl import load_workbook
                wb = load_workbook(str(file_path), data_only=True)
                lines = []
                for sheet in wb.sheetnames:
                    ws = wb[sheet]
                    lines.append(f"--- Sheet: {sheet} ---")
                    for row in ws.iter_rows(values_only=True):
                        row_vals = [str(cell) for cell in row if cell is not None]
                        if row_vals:
                            lines.append(" | ".join(row_vals))
                wb.close()
                return "\n".join(lines)

            elif ext == '.csv':
                lines = []
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row:
                            lines.append(" | ".join(row))
                return "\n".join(lines)

            else:
                # Text or source code files (.txt, .md, .py, .cpp, .h, .c, .js, .ts, .html, .css, .json, etc.)
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()

        except Exception as e:
            return f"[Error extracting text from {file_path.name}: {str(e)}]"

    @staticmethod
    def get_file_metadata(file_path: Path, max_chars: int = 40000) -> Dict[str, Any]:
        """Reads file, extracts text, and returns formatted metadata."""
        size_bytes = file_path.stat().st_size
        raw_text = FileService.extract_text(file_path)
        truncated = False
        if len(raw_text) > max_chars:
            raw_text = raw_text[:max_chars] + f"\n\n... [Content truncated, total {len(raw_text)} chars]"
            truncated = True

        size_kb = round(size_bytes / 1024, 1)
        size_str = f"{size_kb} KB" if size_kb < 1024 else f"{round(size_kb / 1024, 2)} MB"

        return {
            "filename": file_path.name,
            "filepath": str(file_path),
            "extension": file_path.suffix.lower(),
            "size_str": size_str,
            "char_count": len(raw_text),
            "is_truncated": truncated,
            "content": raw_text
        }

file_service = FileService()
