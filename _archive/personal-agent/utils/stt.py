import speech_recognition as sr
import logging

# Setup Logging
logger = logging.getLogger(__name__)

def listen_and_transcribe(timeout=5, phrase_time_limit=5):
    """
    Captures audio from the microphone and converts it to text using Google Web Speech API.
    
    Args:
        timeout (int): Maximum seconds to wait for speech to start.
        phrase_time_limit (int): Maximum seconds to let the user speak.
        
    Returns:
        str: The recognized text, or None if failed.
    """
    recognizer = sr.Recognizer()
    
    # Adjust for ambient noise
    try:
        with sr.Microphone() as source:
            logger.info("Adjusting for ambient noise... Please wait.")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            logger.info("Listening... Speak now!")
            
            try:
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                logger.info("Audio captured. Transcribing...")
                
                # Use Google Web Speech API (Free, no key required for low volume)
                text = recognizer.recognize_google(audio, language="ko-KR")
                logger.info(f"Recognized Text: {text}")
                return text
                
            except sr.WaitTimeoutError:
                logger.warning("Listening timed out. No speech detected.")
                return None
            except sr.UnknownValueError:
                logger.warning("Could not understand audio.")
                return None
            except sr.RequestError as e:
                logger.error(f"Google Speech API validation failed: {e}")
                return None
            except Exception as e:
                logger.error(f"STT Error: {e}")
                return None
    except OSError as e:
        logger.error(f"Microphone access failed. PyAudio might be missing or no mic found: {e}")
        return None
    except AttributeError:
        logger.error("PyAudio is not installed. Microphone input is unavailable.")
        return None

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    print("Say something...")
    result = listen_and_transcribe()
    print(f"You said: {result}")
