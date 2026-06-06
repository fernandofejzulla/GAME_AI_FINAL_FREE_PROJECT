"""Verify Gemini API access with a test call"""
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="What is the prediction for todays Euroleague game?",
)
print("Response:", response.text.strip())
print("API connection works.")