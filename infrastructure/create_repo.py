import json
import os
import sys

import requests


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is required.", file=sys.stderr)
        return 1

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    payload = {
        "name": "BIOJUHO-Projects",
        "description": "AI Projects by BIOJUHO",
        "private": False,
    }

    try:
        response = requests.post(
            "https://api.github.com/user/repos",
            headers=headers,
            json=payload,
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    try:
        body = response.json()
    except ValueError:
        body = {"raw_response": response.text}

    print(f"Status: {response.status_code}")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    return 0 if response.ok else 1


if __name__ == "__main__":
    sys.exit(main())
