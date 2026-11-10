from tkinter import Tk
from tkinter.filedialog import askopenfilenames

def pick_files():
    root = Tk()
    root.withdraw()
    filepaths = askopenfilenames(
        title="Select one or more files",
        filetypes=[
            ("All supported", "*.cpp *.h *.py *.txt *.docx *.pdf *.xlsx *.csv *.pptx")
        ]
    )
    root.destroy()
    return list(filepaths)#converting to a list

