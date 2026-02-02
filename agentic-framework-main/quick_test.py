import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        r = await client.post(
            'http://34.229.112.127:8000/api/chat/public',
            json={'message': 'Hello, this is a quick test. Please respond with just "OK".'},
            timeout=60.0
        )
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")

asyncio.run(test())
