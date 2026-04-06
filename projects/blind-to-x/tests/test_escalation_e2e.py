import asyncio
import os
import sys

# Root path: Vibe coding/
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Add root for blind-to-x dependencies
sys.path.insert(0, os.path.join(root_dir, "projects", "blind-to-x"))
# Add workspace for execution module
sys.path.insert(0, os.path.join(root_dir, "workspace"))

from pipeline.notification import NotificationManager
from config import ConfigManager
from pipeline.spike_detector import SpikeEvent
from pipeline.escalation_queue import EscalationQueue


async def main():
    config = ConfigManager("nonexistent")
    config.config = {}

    nm = NotificationManager(config)

    # 1. Mock Event
    event = SpikeEvent(
        url="https://example.com/test-surge-e2e-1234",
        title="Test Surge E2E with Inline Keyboard",
        source="blind",
        likes=150,
        comments=80,
        velocity_score=15.5,
    )

    # Optional: Mock DB insertion to get an ID
    q = EscalationQueue(db_path=":memory:")
    q._init_schema()
    event_id = q.enqueue(event)
    event.id = event_id or 999

    # 2. Test Notification with Keyboard
    # Using dry_run to actually hit Telegram if TELEGRAM_ENABLED=True,
    # but not saving.
    # Note: we need API tokens in env.
    result = await nm.send_surge_alert(
        event, draft_x="Mock X Draft Content", draft_threads="Mock Threads Content", generation_time=2.5
    )

    print(f"Sent surge alert successfully: {result}")


if __name__ == "__main__":
    asyncio.run(main())
