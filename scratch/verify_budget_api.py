import httpx
import uuid
import sys

def main():
    base_url = "http://127.0.0.1:8000"
    print("Starting API Verification for Phase 7 - Budget Tool...")

    with httpx.Client(timeout=120.0) as client:
        # 1. Test invalid feature mismatch (400)
        print("\n--- Test 1: Feature mismatch validation ---")
        res = client.post(f"{base_url}/budget/chat", json={
            "session_id": None,
            "message": "I want to move to Spain.",
            "feature": "visa_finder"
        })
        print(f"Status code (Expected 400): {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 400
        assert "Feature mismatch" in res.json()["detail"]

        # 2. Test empty message validation (400)
        print("\n--- Test 2: Empty message validation ---")
        res = client.post(f"{base_url}/budget/chat", json={
            "session_id": None,
            "message": "   ",
            "feature": "budget"
        })
        print(f"Status code (Expected 400): {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 400
        assert "Message cannot be empty" in res.json()["detail"]

        # 3. Test message too long validation (400)
        print("\n--- Test 3: Message length validation ---")
        res = client.post(f"{base_url}/budget/chat", json={
            "session_id": None,
            "message": "A" * 2001,
            "feature": "budget"
        })
        print(f"Status code (Expected 400): {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 400
        assert "Message exceeds maximum length" in res.json()["detail"]

        # 4. Test invalid session ID validation (404)
        print("\n--- Test 4: Invalid session ID validation ---")
        fake_session_id = str(uuid.uuid4())
        res = client.post(f"{base_url}/budget/chat", json={
            "session_id": fake_session_id,
            "message": "I want to move to Portugal.",
            "feature": "budget"
        })
        print(f"Status code (Expected 404): {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 404
        assert "Session not found" in res.json()["detail"]

        # 5. Test valid chat initialization (200)
        print("\n--- Test 5: Valid budget chat session initialization ---")
        res = client.post(f"{base_url}/budget/chat", json={
            "session_id": None,
            "message": "I want to move to Portugal.",
            "feature": "budget"
        })
        print(f"Status code (Expected 200): {res.status_code}")
        data = res.json()
        print(f"Response: {data}")
        assert res.status_code == 200
        assert "session_id" in data
        assert data["stage"] == "collecting"
        assert data["message"] is not None
        session_id = data["session_id"]

        # 6. Test session history retrieval (200)
        print("\n--- Test 6: Fetching budget session history ---")
        res = client.get(f"{base_url}/budget/session/{session_id}")
        print(f"Status code (Expected 200): {res.status_code}")
        history_data = res.json()
        print(f"History messages count (Expected 2): {len(history_data['messages'])}")
        assert res.status_code == 200
        assert history_data["session_id"] == session_id
        assert len(history_data["messages"]) == 2
        assert history_data["messages"][0]["role"] == "user"
        assert history_data["messages"][1]["role"] == "assistant"

        # 7. Test budget update with dummy budget (200)
        print("\n--- Test 7: Budget update endpoint ---")
        dummy_budget = {
            "destination_country": "Portugal",
            "visa_type": "D7 Passive Income",
            "currency_code": "EUR",
            "total_one_time_costs": 1000.0,
            "total_monthly_ongoing_costs": 500.0,
            "buffer_fund_amount": 150.0,
            "categories": [
                {
                    "category_name": "pre_move",
                    "category_total": 1000.0,
                    "line_items": [
                        {
                            "item_id": "visa_fee",
                            "label": "Visa Fee",
                            "amount": 1000.0,
                            "frequency": "one_time",
                            "notes": "Original fee",
                            "source_url": None
                        }
                    ]
                }
            ]
        }
        
        update_res = client.post(f"{base_url}/budget/update", json={
            "session_id": session_id,
            "instruction": "Add a line item for pet shipping at 1500 EUR one-time in pre_move category.",
            "current_budget": dummy_budget
        })
        
        print(f"Status code (Expected 200): {update_res.status_code}")
        update_data = update_res.json()
        print(f"Response: {update_data}")
        assert update_res.status_code == 200
        assert update_data["session_id"] == session_id
        
        updated_budget = update_data["budget"]
        print(f"Updated budget: {updated_budget}")
        
        # Assert recalculations
        assert updated_budget["total_one_time_costs"] == 2500.0
        assert updated_budget["buffer_fund_amount"] == 375.0  # 15% of 2500 is 375
        assert updated_budget["total_monthly_ongoing_costs"] == 0.0

        # 8. Test history after update (should have 4 messages now)
        print("\n--- Test 8: Fetching budget session history after update ---")
        res = client.get(f"{base_url}/budget/session/{session_id}")
        print(f"Status code (Expected 200): {res.status_code}")
        history_data2 = res.json()
        print(f"History messages count (Expected 4): {len(history_data2['messages'])}")
        assert res.status_code == 200
        assert len(history_data2["messages"]) == 4

        print("\nALL PHASE 7 BUDGET API VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
