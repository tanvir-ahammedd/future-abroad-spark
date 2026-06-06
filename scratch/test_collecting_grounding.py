import logging
from app.services.gemini import get_genai_client
from app.prompts.budget import SYSTEM_PROMPT
from app.config import settings
from google.genai import types

logging.basicConfig(level=logging.INFO)

history = [
    {"role": "user", "content": "Whats the block amount money need for student visa from bangladesh in germany"}
]

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

# Strict instruction reminder
full_system_prompt = (
    f"{SYSTEM_PROMPT}\n\n"
    "CRITICAL: You MUST respond ONLY with a valid JSON object matching the required shape. "
    "Do NOT include any preamble, conversational commentary, or markdown code blocks (```json). "
    "Start your response with '{' and end with '}'."
)

config = types.GenerateContentConfig(
    system_instruction=full_system_prompt,
    tools=[types.Tool(google_search=types.GoogleSearch())]
)

try:
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=contents,
        config=config
    )
    print("Response text:")
    print(response.text)
except Exception as e:
    print("Error:", e)
