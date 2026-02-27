import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.stt import listen_and_transcribe

# Setup simple logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def test_stt_functionality():
    print("="*50)
    print("🎤 STT Functionality Test")
    print("="*50)
    print("Please speak a sentence within 5 seconds...")
    
    try:
        text = listen_and_transcribe(timeout=5, phrase_time_limit=10)
        
        if text:
            print(f"\n✅ Success! Transcribed Text: '{text}'")
        else:
            print("\n❌ Failed to transcribe or silence detected.")
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")

if __name__ == "__main__":
    test_stt_functionality()
