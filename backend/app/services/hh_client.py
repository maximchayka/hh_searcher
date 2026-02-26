"""hh.ru API client."""
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.security import decrypt_token, encrypt_token


class HHClient:
    BASE_URL = settings.HH_API_BASE_URL

    def __init__(self, access_token: str):
        self._token = access_token

    @classmethod
    def get_auth_url(cls, state: str = "") -> str:
        return (
            f"https://hh.ru/oauth/authorize"
            f"?response_type=code"
            f"&client_id={settings.HH_CLIENT_ID}"
            f"&redirect_uri={settings.HH_REDIRECT_URI}"
            f"&state={state}"
        )

    @classmethod
    async def exchange_code(cls, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://hh.ru/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.HH_CLIENT_ID,
                    "client_secret": settings.HH_CLIENT_SECRET,
                    "redirect_uri": settings.HH_REDIRECT_URI,
                },
            )
            resp.raise_for_status()
            return resp.json()

    @classmethod
    async def refresh_token(cls, refresh_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://hh.ru/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": settings.HH_CLIENT_ID,
                    "client_secret": settings.HH_CLIENT_SECRET,
                },
            )
            resp.raise_for_status()
            return resp.json()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "HH-User-Agent": "JobAutoApply/1.0 (contact@example.com)",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}{path}",
                headers=self._headers(),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _post(self, path: str, data: dict | None = None, params: dict | None = None) -> Any:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}{path}",
                headers=self._headers(),
                json=data,
                params=params,
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}

    async def get_me(self) -> dict:
        return await self._get("/me")

    async def get_resumes(self) -> list[dict]:
        data = await self._get("/resumes/mine")
        return data.get("items", [])

    async def search_vacancies(self, params: dict) -> dict:
        """Returns {found, pages, per_page, items: [...]}"""
        return await self._get("/vacancies", params=params)

    async def get_vacancy(self, vacancy_id: str) -> dict:
        return await self._get(f"/vacancies/{vacancy_id}")

    async def apply_to_vacancy(
        self,
        vacancy_id: str,
        resume_id: str,
        cover_letter: str = "",
    ) -> dict:
        return await self._post(
            "/negotiations",
            params={"vacancy_id": vacancy_id},
            data={"resume_id": resume_id, "message": cover_letter},
        )

    async def get_negotiations(self) -> list[dict]:
        data = await self._get("/negotiations")
        return data.get("items", [])
