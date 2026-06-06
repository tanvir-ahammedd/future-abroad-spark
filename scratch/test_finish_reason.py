import logging
from app.services.gemini import get_genai_client, generate_chat_stream
from app.prompts.budget import SYSTEM_PROMPT
from app.config import settings
from google.genai import types

# Setup logging
logging.basicConfig(level=logging.INFO)

history = [
    {"role": "user", "content": "I want to move to Germany from Bangladesh as a student."},
    {"role": "assistant", "content": '{"stage": "collecting", "message": "Welcome! To help build your budget for Germany, could you please tell me your planned move date, your preferred accommodation (e.g., student dorm, shared flat, or private apartment), and your desired lifestyle (budget-conscious or comfortable)? Also, will you be bringing any pets or large items beyond typical luggage?"}'},
    {"role": "user", "content": "I plan to move in September 2026. I'll rent a single room in a shared apartment, have a budget-conscious lifestyle, and I am not shipping any possessions except regular suitcases. No pets or vehicles."},
    {"role": "assistant", "content": '{"stage": "collecting", "message": "Thanks for those details! To finalize your budget, could you please tell me which specific city in Germany you\'ll be studying in?"}'},
    {"role": "user", "content": "I am moving to Munich."}
]

print("--- Testing chat stream with raw candidate inspection ---")
client = get_genai_client()
contents = []
for msg in history:
    role = "model" if msg.get("role") == "assistant" else "user"
    contents.append(
        types.Content(
            role=role,
            parts=[types.Part.from_text(text=msg.get("content", ""))]
        )
    )

config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[types.Tool(google_search=types.GoogleSearch())]
)

try:
    response_stream = client.models.generate_content_stream(
        model=settings.GEMINI_MODEL,
        contents=contents,
        config=config
    )
    
    full_text = ""
    for chunk in response_stream:
        if chunk.text:
            full_text += chunk.text
        if chunk.candidates:
            cand = chunk.candidates[0]
            finish_reason = getattr(cand, "finish_reason", None)
            if finish_reason:
                print(f"\nChunk candidate finish reason: {finish_reason}")
                
    print("\nFull Text Length:", len(full_text))
    print("End of full text:")
    print(repr(full_text[-100:]))
except Exception as e:
    print("Failed with:", e)
