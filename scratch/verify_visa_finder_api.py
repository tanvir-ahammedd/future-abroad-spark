import httpx
import uuid
import sys

def main():
    base_url = "http://127.0.0.1:8000"
    print("Starting API Verification for Phase 6 - Visa Finder Chatbot...")

    # 1. Test invalid feature mismatch (400)
    print("\n--- Test 1: Feature mismatch validation ---")
    res = httpx.post(f"{base_url}/visa-finder/chat", json={
        "session_id": None,
        "message": "Hi, I want to move to Spain.",
        "feature": "budget"
    })
    print(f"Status code (Expected 400): {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.status_code == 400
    assert "Feature mismatch" in res.json()["detail"]

    # 2. Test empty message validation (400)
    print("\n--- Test 2: Empty message validation ---")
    res = httpx.post(f"{base_url}/visa-finder/chat", json={
        "session_id": None,
        "message": "   ",
        "feature": "visa_finder"
    })
    print(f"Status code (Expected 400): {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.status_code == 400
    assert "Message cannot be empty" in res.json()["detail"]

    # 3. Test message too long validation (400)
    print("\n--- Test 3: Message length validation ---")
    res = httpx.post(f"{base_url}/visa-finder/chat", json={
        "session_id": None,
        "message": "A" * 2001,
        "feature": "visa_finder"
    })
    print(f"Status code (Expected 400): {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.status_code == 400
    assert "Message exceeds maximum length" in res.json()["detail"]

    # 4. Test invalid session ID validation (404)
    print("\n--- Test 4: Invalid session ID validation ---")
    fake_session_id = str(uuid.uuid4())
    res = httpx.post(f"{base_url}/visa-finder/chat", json={
        "session_id": fake_session_id,
        "message": "Hi, I want to move to Portugal.",
        "feature": "visa_finder"
    })
    print(f"Status code (Expected 404): {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.status_code == 404
    assert "Session not found" in res.json()["detail"]

    # 5. Test valid chat initialization (200)
    print("\n--- Test 5: Valid chat session initialization ---")
    res = httpx.post(f"{base_url}/visa-finder/chat", json={
        "session_id": None,
        "message": "I want to retire somewhere warm in Europe.",
        "feature": "visa_finder"
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
    print("\n--- Test 6: Fetching session history ---")
    res = httpx.get(f"{base_url}/visa-finder/session/{session_id}")
    print(f"Status code (Expected 200): {res.status_code}")
    history_data = res.json()
    print(f"History messages count (Expected 2): {len(history_data['messages'])}")
    assert res.status_code == 200
    assert history_data["session_id"] == session_id
    assert len(history_data["messages"]) == 2
    assert history_data["messages"][0]["role"] == "user"
    assert history_data["messages"][1]["role"] == "assistant"

    # 7. Test sending subsequent message in the same session (200)
    print("\n--- Test 7: Sending next message in conversation ---")
    res = httpx.post(f"{base_url}/visa-finder/chat", json={
        "session_id": session_id,
        "message": "I prefer Portugal, my monthly passive income is 3000 EUR and I have 50000 EUR savings.",
        "feature": "visa_finder"
    })
    print(f"Status code (Expected 200): {res.status_code}")
    next_data = res.json()
    print(f"Response: {next_data}")
    assert res.status_code == 200
    assert next_data["session_id"] == session_id
    assert next_data["stage"] == "collecting"

    # 8. Test history after second message (should have 4 messages now)
    print("\n--- Test 8: Fetching session history again ---")
    res = httpx.get(f"{base_url}/visa-finder/session/{session_id}")
    print(f"Status code (Expected 200): {res.status_code}")
    history_data2 = res.json()
    print(f"History messages count (Expected 4): {len(history_data2['messages'])}")
    assert res.status_code == 200
    assert len(history_data2["messages"]) == 4

    print("\nALL PHASE 6 API VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
