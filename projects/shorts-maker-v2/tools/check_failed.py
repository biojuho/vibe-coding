import subprocess

with open("check_failed.txt", "w", encoding="utf-8") as f:
    f.write("--- RUFF ERRORS ---\n")
    result_ruff = subprocess.run(
        [r"..\..\venv\Scripts\ruff.exe", "check", "."],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    f.write(result_ruff.stdout)

    f.write("\n--- PYTEST FAILURES ---\n")
    result_pytest = subprocess.run(
        [r"..\..\venv\Scripts\pytest.exe", "tests/", "-q", "--tb=short"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    lines = result_pytest.stdout.splitlines()
    for line in lines:
        if line.startswith("FAILED") or line.startswith("E ") or line.startswith("ERROR "):
            f.write(line + "\n")
