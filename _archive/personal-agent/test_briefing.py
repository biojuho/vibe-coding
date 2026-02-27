import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from briefing.weather import get_weather
from briefing.news import get_top_news

print("Testing Weather Module...")
print(get_weather("Seoul"))

print("\nTesting News Module...")
print(get_top_news())
