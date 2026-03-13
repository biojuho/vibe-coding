from bs4 import BeautifulSoup

with open("raw2.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
out = []
for tag in soup.find_all(string=lambda t: t and "인테리어 공사 중인데" in t):
    parent = tag.parent
    out.append(f"Found exact text in tag: {parent.name} (class={parent.get('class')})")
    
    ancestor = parent.parent
    for i in range(5):
        if ancestor and ancestor.name != "[document]":
            out.append(f"  Ancestor {i+1} ({ancestor.name}): class={ancestor.get('class')}")
            ancestor = ancestor.parent
    out.append("-" * 40)

with open("selectors.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
