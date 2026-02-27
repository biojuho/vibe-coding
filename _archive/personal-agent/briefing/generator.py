from utils.llm import LLMClient
from briefing.weather import get_weather
from briefing.news import get_top_news
import datetime

def generate_briefing():
    """
    Generates a daily briefing using LLM.
    """
    print("Gathering information...")
    weather_data = get_weather("Seoul")
    news_data = get_top_news(limit=5)
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    prompt = f"""
    You are Jarvis, a personal AI assistant.
    Current Time: {current_time}
    
    Here is the latest data found:
    
    [Weather]
    {weather_data}
    
    [News Headlines]
    {news_data}
    
    Please provide a 'Morning Briefing' for your user.
    1. Start with a warm greeting based on the time and weather.
    2. Summarize the weather and suggest what to wear or precise advice.
    3. Summarize the key news headlines in a conversational tone.
    4. End with a motivating closing statement.
    
    Keep it concise, professional yet friendly.
    """
    
    try:
        llm = LLMClient()
        print("Consulting with AI...")
        return llm.generate_text(prompt)
    except ValueError as e:
        return f"Configuration Error: {str(e)}\nPlease check your .env file and API keys."
    except Exception as e:
        return f"An error occurred: {str(e)}"

if __name__ == "__main__":
    print(generate_briefing())
