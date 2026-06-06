import logging
from app.services.gemini import generate_chat_stream, generate_structured_json

# Setup basic logging to see warnings/errors
logging.basicConfig(level=logging.INFO)

print("--- Testing generate_chat_stream with grounding ---")
try:
    messages = [
        {"role": "user", "content": "Whats the block amount money need for student visa from bangladesh in germany"}
    ]
    
    stream = generate_chat_stream(
        system_prompt="You are a helpful assistant.",
        messages=messages,
        enable_search_grounding=True
    )
    
    full_text = ""
    for chunk in stream:
        print(chunk, end="", flush=True)
        full_text += chunk
    print("\n\nStream completed successfully!")
    
except Exception as e:
    print("\nStream test failed with:", e)


print("\n--- Testing generate_structured_json ---")
try:
    system_prompt = "You are a relocation budget specialist for MyFutureAbroad."
    user_prompt = "Generate a sample budget structure for moving to Germany from Bangladesh."
    
    response_json = generate_structured_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        enable_search_grounding=False
    )
    
    import pprint
    pprint.pprint(response_json)
    print("\nJSON generation completed successfully!")
except Exception as e:
    print("\nJSON test failed with:", e)
