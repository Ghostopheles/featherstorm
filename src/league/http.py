import json
import httpx

from league.console import log_error, format_url


class BaseAPIClient:
    client: httpx.AsyncClient

    async def _make_request(self, method, *args, no_json: bool = False, _return_exception: bool = False, **kwargs):
        try:
            res = await self.client.request(method, *args, **kwargs)
            res.raise_for_status()

            if no_json:
                return res

            try:
                return res.json()
            except json.decoder.JSONDecodeError:
                if res.status_code != 204:
                    log_error(f"[error]JSON decode error from {format_url(res.request.url)}[/]")
                return None
        except httpx.HTTPStatusError as e:
            log_error(f"[error]HTTP Status Error ({e.response.status_code}) from {format_url(e.request.url)}[/]: {str(e)}", show_locals=False, show_traceback=False)
            return e if _return_exception else None
        except httpx.RequestError as e:
            log_error(f"[error]HTTP Request Error ({type(e).__name__}) from {format_url(e.request.url)}[/]: {str(e)}", show_locals=False, show_traceback=False)
            return e if _return_exception else None


    async def get(self, *args, **kwargs):
        return await self._make_request("GET", *args, **kwargs)

    async def post(self, *args, **kwargs):
        return await self._make_request("POST", *args, **kwargs)
