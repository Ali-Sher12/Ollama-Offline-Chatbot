def load_txt(filepath):
    f = open(filepath, 'r', encoding='utf-8')
    content = f.read()
    f.close()
    return content