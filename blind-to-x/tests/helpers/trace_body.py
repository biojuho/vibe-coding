from bs4 import BeautifulSoup

with open("raw.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
body = soup.find("body")

if body:
    text = body.get_text(strip=True, separator=" ")
    print(f"Body text length: {len(text)}")
    print(f"Body text start (first 500 chars): {text[:500]}")
    # Print the specific error or login messages
    if "로그인" in text:
        print("Found '로그인' (Login) in body text!")
    if "권한" in text:
        print("Found '권한' (Permission) in body text!")
else:
    print("No body tag found!")
