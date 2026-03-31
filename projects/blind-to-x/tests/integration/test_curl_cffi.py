from curl_cffi import requests


def test_fetch():
    url = "https://www.teamblind.com/kr/post/%ED%98%95%EB%93%A4-%EB%82%98-%EC%9D%B8%ED%85%8C%EB%A6%AC%EC%96%B4-%EA%B3%B5%EC%82%AC-%EC%A4%91%EC%9D%B8%EB%8D%B0-guyg5nxl"
    # impersonate a real browser (chrome 120)
    response = requests.get(url, impersonate="chrome120")
    print(f"Status Code: {response.status_code}")
    print(f"Length: {len(response.text)}")
    if "- Guyg5nxl" in response.text or "인테리어" in response.text:
        print("Success: Found content!")
    else:
        print("Failed: Content not found.")
        print(response.text[:200])


if __name__ == "__main__":
    test_fetch()
