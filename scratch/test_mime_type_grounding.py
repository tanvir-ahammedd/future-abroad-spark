from google import genai
from google.genai import types
from app.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

config = types.GenerateContentConfig(
    system_instruction="You are a helpful assistant. You must output a JSON object with 'answer' containing your response.",
    tools=[types.Tool(google_search=types.GoogleSearch())],
    response_mime_type="application/json"
)

try:
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents="Whats the block amount money need for student visa from bangladesh in germany in 2026?",
        config=config
    )
    print("Combined call succeeded!")
    print("Response:")
    print(response.text)
except Exception as e:
    print("Combined call failed with:", e)
