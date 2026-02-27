from gtts import gTTS
import os
import uuid

def text_to_speech(text, output_dir="metrics"):
    """
    Converts text to speech using Google Text-to-Speech (gTTS).
    Saves the audio file to the specified directory.
    
    Args:
        text (str): The text to convert.
        output_dir (str): Directory to save the audio file.
        
    Returns:
        str: Path to the saved audio file, or None if failed.
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Generate a unique filename to avoid caching issues
        filename = f"briefing_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(output_dir, filename)
        
        tts = gTTS(text=text, lang='ko')
        tts.save(filepath)
        
        return filepath
    except Exception as e:
        error_msg = str(e)
        if "ConnectionError" in error_msg or "Max retries" in error_msg:
            print(f"⚠️ TTS Network Error: {e}")
            return None # Return None to indicate failure gracefully
        print(f"Error generating speech: {e}")
        return None

if __name__ == "__main__":
    # Test
    path = text_to_speech("안녕하세요, 자비스입니다. 목소리 테스트 중입니다.")
    print(f"Audio saved to: {path}")
