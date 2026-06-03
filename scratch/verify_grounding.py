import os
import sys

# Ensure project root is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
from app.config import settings

def main():
    # Force output to use utf-8 representation to avoid stdout charmap issues
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print(f"Configuring Gemini client using model: {settings.GEMINI_MODEL}")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    # Correct proto structure for search grounding
    proto_tool = [genai.protos.Tool(google_search=genai.protos.Tool.GoogleSearch())]
    
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        tools=proto_tool
    )
    
    # Prompt that definitely requires search grounding
    prompt = "Who is the current Prime Minister of the United Kingdom?"
    print(f"Sending prompt: '{prompt}' with Google Search Grounding...")
    
    try:
        response = model.generate_content(
            prompt,
            request_options={"timeout": float(settings.GEMINI_TIMEOUT_SECONDS)}
        )
        
        print("\n--- RESPONSE TEXT ---")
        print(response.text.strip())
        print("---------------------\n")
        
        if not response.candidates:
            print("No candidates found in response.")
            return
            
        candidate = response.candidates[0]
        grounding_metadata = getattr(candidate, "grounding_metadata", None)
        
        if not grounding_metadata:
            print("No grounding metadata found in candidate.")
            print("Checking candidate properties:")
            for attr in dir(candidate):
                if not attr.startswith("_"):
                    print(f" - {attr}: {type(getattr(candidate, attr))}")
            return
            
        print("--- GROUNDING METADATA FOUND ---")
        print(f"Type: {type(grounding_metadata)}")
        
        # Display search queries
        web_queries = getattr(grounding_metadata, "web_search_queries", [])
        print(f"Web Search Queries: {list(web_queries)}")
        
        # Display grounding chunks
        chunks = getattr(grounding_metadata, "grounding_chunks", [])
        print(f"Number of grounding chunks/sources: {len(chunks)}")
        for i, chunk in enumerate(chunks, 1):
            web = getattr(chunk, "web", None)
            if web:
                print(f"Source {i}: {getattr(web, 'title', 'No Title')} -> {getattr(web, 'uri', 'No URI')}")
                
        # Display grounding supports
        supports = getattr(grounding_metadata, "grounding_supports", [])
        print(f"Number of grounding supports/citations: {len(supports)}")
        
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
