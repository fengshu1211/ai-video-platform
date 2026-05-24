import sqlite3, os

os.chdir(os.path.dirname(os.path.abspath(__file__)) or '.')
db = sqlite3.connect('data.db')
cleaned = 0

for table, col in [
    ('rewritten_scripts', 'rewritten_text'),
    ('rewritten_scripts', 'original_text'),
]:
    rows = db.execute(f"SELECT id, {col} FROM {table}").fetchall()
    for rid, text in rows:
        if not text:
            continue
        # Replace literal \udXXX patterns (JSON surrogate escapes)
        new_text = text
        for i in range(len(text)):
            if text[i:i+2] == '\\u' and i+5 < len(text):
                hexcode = text[i+2:i+6]
                try:
                    cp = int(hexcode, 16)
                    if 0xD800 <= cp <= 0xDFFF:
                        new_text = new_text.replace(text[i:i+6], '', 1)
                except ValueError:
                    pass
        if new_text != text:
            db.execute(f"UPDATE {table} SET {col}=? WHERE id=?", (new_text, rid))
            cleaned += 1
            print(f"Fixed {table}.{col} id={rid}")

db.commit()
db.close()
print(f"Cleaned {cleaned} records")
