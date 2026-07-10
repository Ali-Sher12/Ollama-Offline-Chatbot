from openpyxl import load_workbook

def load_xlsx(filepath):
    wb = load_workbook(filepath)
    ws = wb.active
    text = ""
    for row in ws.iter_rows(values_only=True):#I need the text from the cells
        text += str(row) + "\n"
    wb.close()
    return text