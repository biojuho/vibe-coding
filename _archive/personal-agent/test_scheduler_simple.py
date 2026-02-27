from utils.scheduler import scheduler
import time

def job():
    print("✅ Job Executed!")

print("Testing Scheduler...")
scheduler.start()

# Schedule a job every 1 second (using schedule library's lower level API for test if possible,
# but our wrapper only exposes 'every day at'. I might need to extend the wrapper for testing
# or just test the 'add_job' returns True and trust the library).

# Let's test adding a job.
success = scheduler.add_job("23:59", job)
print(f"Job scheduled: {success}")

jobs = scheduler.list_jobs()
print(f"Active Jobs: {len(jobs)}")
for j in jobs:
    print(f"- {j}")

scheduler.stop()
print("Scheduler stopped.")
