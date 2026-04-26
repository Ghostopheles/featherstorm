import json
import httpx

class BaseAPIClient:
    client: httpx.AsyncClient

    async def _make_request(self, method, *args, **kwargs):
        try:
            res = await self.client.request(method, *args, **kwargs)
            res.raise_for_status()
            try:
                return res.json()
            except json.decoder.JSONDecodeError:
                return None
        except httpx.HTTPStatusError as e:
            print(e.response.json())
            raise e


    async def get(self, *args, **kwargs):
        return await self._make_request("GET", *args, **kwargs)

    async def post(self, *args, **kwargs):
        return await self._make_request("POST", *args, **kwargs)
