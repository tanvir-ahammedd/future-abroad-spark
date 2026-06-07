import json
import logging
from app.config import settings
from app.schemas.checklist import ChecklistSchema
from app.prompts.checklist import UPDATE_PROMPT_TEMPLATE
from app.services.gemini import generate_structured_json

# Configure logging
logging.basicConfig(level=logging.INFO)

dummy_checklist = {
    "destination_country": "Portugal",
    "move_date_reference": "September 2026",
    "phases": [
        {
            "phase_id": "six_months_before",
            "phase_label": "6 Months Before",
            "items": [
                {
                    "item_id": "apply_for_nif",
                    "title": "Apply for NIF",
                    "description": "Get Portuguese taxpayer number.",
                    "status": "not_started",
                    "category": "legal",
                    "country_specific": True,
                    "notes": None
                }
            ]
        }
    ]
}

# Convert dummy_checklist to ChecklistSchema to mimic request
current_checklist_obj = ChecklistSchema(**dummy_checklist)

system_prompt = "You are a relocation checklist specialist for MyFutureAbroad. Modify the checklist JSON based on the user's instruction."
user_prompt = UPDATE_PROMPT_TEMPLATE.format(
    current_checklist=current_checklist_obj.model_dump_json(),
    instruction="Add a new item to verify school enrollment in Portugal."
)

print("Calling generate_structured_json...")
try:
    raw_response = generate_structured_json(system_prompt, user_prompt, enable_search_grounding=False)
    print("Raw response from Gemini:")
    print(json.dumps(raw_response, indent=2))
    
    # Try validating
    print("\nAttempting validation...")
    validated = ChecklistSchema(**raw_response)
    print("Validation succeeded!")
except Exception as e:
    print(f"Error occurred: {e}")
