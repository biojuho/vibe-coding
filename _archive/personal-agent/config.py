import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Selection (openai or google)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

# User Persona
USER_NAME = "Joolife President JooPark" # 쥬라프 대표 쥬팍
