import google.generativeai as genai
from config import GOOGLE_API_KEY
import os

if not GOOGLE_API_KEY:
    print("GOOGLE_API_KEY not found in config/env")
    exit()

print(f"Using API Key: {GOOGLE_API_KEY[:5]}...")

genai.configure(api_key=GOOGLE_API_KEY)

print("Listing models...")
try:
    for m in genai.list_models():
        print(f"Model: {m.name}")
        print(f"Supported methods: {m.supported_generation_methods}")
        print("-" * 20)
except Exception as e:
    print(f"Error listing models: {e}")
