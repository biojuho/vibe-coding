from bs4 import BeautifulSoup

with open("raw.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find where the post text might be
# The post title was "내 폰 구형이라"
for tag in soup.find_all(string=lambda t: t and "구형이라" in t):
    parent = tag.parent
    print(f"Text found in: {parent.name} (class={parent.get('class')})")
    
    # Go up 5 ancestors
    ancestor = parent.parent
    for i in range(5):
        if ancestor and ancestor.name != "[document]":
            print(f"  Ancestor {i+1} ({ancestor.name}):", ancestor.get("class"))
            ancestor = ancestor.parent
    print("-" * 40)
