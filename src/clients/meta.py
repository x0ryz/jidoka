import httpx

from src.core.config import settings


class MetaClient:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.base_url = settings.META_URL

    async def send_message(self, phone_id: str, data: dict):
        """Send a message to a phone number using Meta Graph API."""
        url = f"{self.base_url}/{phone_id}/messages"
        resp = await self.client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()

    async def fetch_account_info(self, waba_id: str):
        """Fetch WABA account information from Meta Graph API."""
        url = f"{self.base_url}/{waba_id}"
        params = {"fields": "name,account_review_status,business_verification_status"}

        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def fetch_phone_numbers(self, waba_id: str):
        """Fetch WABA phone numbers from Meta Graph API."""
        url = f"{self.base_url}/{waba_id}/phone_numbers"

        resp = await self.client.get(url)
        resp.raise_for_status()
        return resp.json()
