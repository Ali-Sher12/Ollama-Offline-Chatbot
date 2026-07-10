import csv

def load_csv(filepath):
    f = open(filepath, 'r')
    reader = csv.reader(f)
    text = ""
    for row in reader:
        text += " ".join(row) + "\n"
    f.close()
    return text
