import os
import json
import logging

# Setup Logging
logger = logging.getLogger(__name__)

MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory.json")
MAX_MEMORY_MESSAGES = int(os.getenv("MAX_MEMORY_MESSAGES", "200"))


def _trim_messages(messages):
    if not isinstance(messages, list):
        return []
    trimmed = [m for m in messages if isinstance(m, dict)]
    if len(trimmed) > MAX_MEMORY_MESSAGES:
        trimmed = trimmed[-MAX_MEMORY_MESSAGES:]
    return trimmed

def load_memory():
    """Loads chat history from the JSON file."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                memory = json.load(f)
                memory = _trim_messages(memory)
                logger.info(f"Loaded {len(memory)} messages from memory.")
                return memory
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return []
    return []

def save_memory(messages):
    """Saves chat history to the JSON file."""
    try:
        normalized = _trim_messages(messages)
        # Ensure data directory exists
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved {len(normalized)} messages to memory.")
    except Exception as e:
        logger.error(f"Failed to save memory: {e}")

def clear_memory():
    """Clears the chat history file."""
    if os.path.exists(MEMORY_FILE):
        try:
            os.remove(MEMORY_FILE)
            logger.warning("Memory wiped.")
        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
