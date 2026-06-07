import json
from pydantic import ValidationError
from app.schemas.checklist import ChecklistUpdateRequest

payload = {
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "instruction": "Add checklist items for relocating my pet cat to Germany and mark the visa application task as in progress.",
  "current_checklist": {
    "destination_country": "Germany",
    "move_date_reference": "March 2027",
    "phases": [
      {
        "phase_id": "six_months_before",
        "phase_label": "6 Months Before Move",
        "items": [
          {
            "item_id": "apply-student-visa",
            "title": "Apply for Student Visa",
            "description": "Prepare and submit your German student visa application.",
            "status": "not_started",
            "category": "legal",
            "country_specific": True,
            "notes": None
          },
          {
            "item_id": "prepare-financial-proof",
            "title": "Prepare Financial Proof",
            "description": "Arrange blocked account and supporting financial documents.",
            "status": "not_started",
            "category": "education",
            "country_specific": True,
            "notes": None
          }
        ]
      }
    ]
  }
}

try:
    obj = ChecklistUpdateRequest(**payload)
    print("ChecklistUpdateRequest validated successfully!")
except ValidationError as e:
    print("Pydantic Validation Error:")
    print(e.json(indent=2))
