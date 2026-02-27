import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects", "personal-agent"))

import shutil
import time
from tools.file_manager import organize_directory

TEST_DIR = "temp_test_downloads"

def setup_test_files():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)
    
    # Create dummy files
    files = [
        "image.png", "photo.jpg", "document.pdf", "notes.txt",
        "installer.exe", "archive.zip", "video.mp4", "script.py",
        "unknown.xyz"
    ]
    
    for f in files:
        with open(os.path.join(TEST_DIR, f), 'w') as fh:
            fh.write("dummy content")
            
    print(f"Created {len(files)} dummy files in {TEST_DIR}")

def verify_organization():
    print("Running organization...")
    result = organize_directory(os.path.abspath(TEST_DIR))
    print(result)
    
    # Check structure
    expected_dirs = ["Images", "Documents", "Installers", "Archives", "Media", "Code", "Others"]
    
    passed = True
    for d in expected_dirs:
        dir_path = os.path.join(TEST_DIR, d)
        if os.path.exists(dir_path):
            files = os.listdir(dir_path)
            if files:
                print(f"[PASS] {d}: {files}")
            else:
                pass
        else:
            pass
            
    # Specific checks
    if os.path.exists(os.path.join(TEST_DIR, "Images", "image.png")):
        print("[PASS] Image moved correctly")
    else:
        print("[FAIL] Image NOT moved")
        passed = False

    if os.path.exists(os.path.join(TEST_DIR, "Others", "unknown.xyz")):
        print("[PASS] Unknown file moved to Others")
    else:
        print("[FAIL] Unknown file NOT moved to Others")
        passed = False
        
    return passed

if __name__ == "__main__":
    setup_test_files()
    if verify_organization():
        print("\n[SUCCESS] Safety Test PASSED. Safe to run on real folder.")
        # Cleanup
        shutil.rmtree(TEST_DIR)
    else:
        print("\n[FAIL] Safety Test FAILED.")
