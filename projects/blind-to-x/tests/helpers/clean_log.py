with open("out_final.txt", encoding="utf-16le", errors="ignore") as f:
    text = f.read()
with open("out_final_clean.txt", "w", encoding="utf-8") as out:
    out.write(text)
