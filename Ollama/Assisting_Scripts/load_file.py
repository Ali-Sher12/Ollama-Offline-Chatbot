import csv
from pathlib import Path
from docx import Document
import PyPDF2
from pptx import Presentation
from openpyxl import load_workbook

def _load_csv(filepath):
    f = open(filepath, 'r')
    reader = csv.reader(f)
    text = ""
    for row in reader:
        text += " ".join(row) + "\n"
    f.close()
    return text


def _load_docx(filepath):
    doc = Document(filepath)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def _load_pdf(filepath):
    reader = PyPDF2.PdfReader(filepath)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def _load_pptx(filepath):
    prs = Presentation(filepath)
    text = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                text += shape.text_frame.text + "\n"
    return text

def _load_txt(filepath):
    f = open(filepath, 'r', encoding='utf-8')
    content = f.read()
    f.close()
    return content

def _load_xlsx(filepath):
    wb = load_workbook(filepath)
    ws = wb.active
    text = ""
    for row in ws.iter_rows(values_only=True):#I need the text from the cells
        text += str(row) + "\n"
    wb.close()
    return text

#only puclic function
def load_file_ext(filepath):
    ext = Path(filepath).suffix.lower()
    if ext == '.docx':
        return _load_docx(filepath)
    elif ext == '.pdf':
        return _load_pdf(filepath)
    elif ext == '.pptx':
        return _load_pptx(filepath)
    elif ext == '.xlsx':
        return _load_xlsx(filepath)    
    elif ext == '.csv':
        return _load_csv(filepath)
    else:
        return _load_txt(filepath)

