import logging
import os
import sys
from datetime import datetime

# Setup Logging similar to app.py
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_filename = os.path.join(log_dir, f"test_agent_{datetime.now().strftime('%Y-%m-%d')}.log")
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(module)s: %(message)s',
    encoding='utf-8',
    force=True
)

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "projects", "personal-agent"))

from rag.query import query_rag

if __name__ == "__main__":
    logging.info("Starting logging test...")
    print("Running query_rag...")
    query_rag("시스템 상태 어때?")
    logging.info("Test complete.")
    print(f"Check log file: {log_filename}")
