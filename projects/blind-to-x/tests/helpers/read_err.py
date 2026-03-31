import io

try:
    with io.open("out_final.txt", "r", encoding="utf-16le") as f:
        lines = f.readlines()
        for line in lines[-30:]:
            print(line.strip())
except Exception as e:
    print(f"Failed to read out_final.txt: {e}")
