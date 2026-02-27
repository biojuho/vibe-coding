import schedule
import time
import threading
import logging

class TaskScheduler:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskScheduler, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        
        self.running = False
        self.thread = None
        self.initialized = True
        
        # Setup Logger
        self.logger = logging.getLogger("Scheduler")
        self.logger.setLevel(logging.INFO)

    def start(self):
        """Start the scheduler loop in a background thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.logger.info("Task Scheduler Started.")

    def _run_loop(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        """Stop the scheduler loop."""
        self.running = False
        if self.thread:
            self.thread.join()
        self.logger.info("Task Scheduler Stopped.")

    def add_job(self, time_str, func, *args):
        """Run a job every day at a specific time (e.g., '08:00')."""
        try:
            schedule.every().day.at(time_str).do(func, *args)
            self.logger.info(f"Scheduled job at {time_str}: {func.__name__}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to schedule job: {e}")
            return False

    def list_jobs(self):
        return schedule.get_jobs()

# Global Instance
scheduler = TaskScheduler()
