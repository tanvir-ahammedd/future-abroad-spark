import asyncio
import httpx
from app.main import app

async def test_budget_chat():
    print("--- Testing /budget/chat endpoint locally (Multi-Turn) ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Turn 1: Send a chat message to start a budget session
        payload1 = {
            "message": "I want to move to Germany from Bangladesh as a student.",
            "feature": "budget"
        }
        print("Sending initial message...")
        response1 = await client.post("/budget/chat", json=payload1)
        print("Turn 1 Status Code:", response1.status_code)
        
        resp_json1 = response1.json()
        session_id = resp_json1.get("session_id")
        print("New Session ID:", session_id)
        print("Assistant Message:", resp_json1.get("message"))
        
        # Turn 2: Reply to the assistant's questions to complete collection
        payload2 = {
            "session_id": session_id,
            "message": "I plan to move in September 2026. I'll rent a single room in a shared apartment, have a budget-conscious lifestyle, and I am not shipping any possessions except regular suitcases. No pets or vehicles.",
            "feature": "budget"
        }
        print("\nSending response to complete detail collection...")
        response2 = await client.post("/budget/chat", json=payload2)
        print("Turn 2 Status Code:", response2.status_code)
        
        resp_json2 = response2.json()
        print("Assistant Message:", resp_json2.get("message"))
        
        # Turn 3: Reply with the city details
        payload3 = {
            "session_id": session_id,
            "message": "I am moving to Munich.",
            "feature": "budget"
        }
        print("\nSending response with the city details...")
        response3 = await client.post("/budget/chat", json=payload3)
        print("Turn 3 Status Code:", response3.status_code)
        
        try:
            resp_json3 = response3.json()
            print("\nResponse Stage:", resp_json3.get("stage"))
            if resp_json3.get("stage") == "complete":
                print("Budget details:")
                import pprint
                pprint.pprint(resp_json3.get("budget"))
            else:
                print("Response Message:", resp_json3.get("message"))
        except Exception as e:
            print("Failed to parse response JSON:", e)
            print("Raw Content:", response3.text)

if __name__ == "__main__":
    asyncio.run(test_budget_chat())
