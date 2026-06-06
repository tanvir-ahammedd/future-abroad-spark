import asyncio
import httpx
from app.main import app

async def test_new_session():
    print("--- Testing /budget/chat with a brand new session ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "message": "Whats the block amount money need for student visa from bangladesh in germany",
            "feature": "budget"
        }
        response = await client.post("/budget/chat", json=payload)
        print("Status Code:", response.status_code)
        try:
            resp_json = response.json()
            print("Response Stage:", resp_json.get("stage"))
            print("Response Message:")
            print(resp_json.get("message"))
        except Exception as e:
            print("Failed to parse response:", e)

if __name__ == "__main__":
    asyncio.run(test_new_session())
