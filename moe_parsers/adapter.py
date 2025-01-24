from aiohttp import ClientSession
from asyncio import sleep
from json import loads
from requests import request, packages, Response as RequestsModuleResponse
from typing import TypedDict, Literal, Unpack
from faker import Faker
from bs4 import BeautifulSoup


class _ClientHeaders(TypedDict, total=False):
    user_agent: str
    referer: str
    x_forwarded_for: str
    x_requested_with: str
    accept: str
    accept_language: str
    accept_encoding: str
    accept_charset: str
    connection: str
    cookie: str


class _ClientParams(TypedDict, total=False):
    headers: _ClientHeaders
    max_retries: int
    base_url: str


class RequestArgs(TypedDict, total=False):
    session: ClientSession
    url: str
    method: Literal["get", "post", "put", "delete"]
    headers: _ClientHeaders


class _RequestResponse:
    status: int
    headers: dict
    text: str
    json: dict
    data: bytes
    soup: BeautifulSoup
    _response: RequestsModuleResponse | None

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)
        try:
            self.json = loads(self.text)
        except ValueError:
            self.json = None
        self.soup = BeautifulSoup(self.text, features="html.parser")

    def __repr__(self):
        return f"<Response [{self.status}] ({len(self.text)}, {len(self.json) if self.json else 0})>"

    def json(self):
        return self.__dict__.get("json", None)


class _Client:
    def __init__(self, **params: Unpack[_ClientParams]):
        self.__dict__.update(**params)

    def _my(self, key: str):
        return self.__dict__.get(key, None)

    def replace_headers(self, *dicts: dict, **headers: Unpack[_ClientHeaders]):
        for d in dicts:
            self.__dict__.get("headers", {}).update(**d)
        self.__dict__.get("headers", {}).update(
            **{k.replace("_", "-").title(): v for k, v in headers.items()}
        )

    def soup(self, *args, **kwargs):
        return BeautifulSoup(*args, **kwargs, features="html.parser")

    async def request(self, *args, **kwargs: Unpack[RequestArgs]) -> _RequestResponse:
        if kwargs.get("retries", 0) > self.__dict__.get("max_retries", 5):
            raise Exception("Too many retries")
        if not kwargs.get("url", None) and args and isinstance(args[0], str):
            kwargs["url"] = args[0]
        elif not kwargs.get("url", None):
            raise Exception("Missing url")
        kwargs["url"] = kwargs["url"].replace(" ", "%20")
        if not kwargs["url"].startswith("http"):
            kwargs["url"] = f"{self._my('base_url') or 'https://'}{kwargs['url']}"
        if self._my("proxy") or kwargs.get("proxy", None):
            packages.urllib3.disable_warnings()
            response = request(
                method=kwargs.get("method", "get"),
                url=kwargs.get("url"),
                data=kwargs.get("data", None),
                json=kwargs.get("json", None),
                headers=kwargs.get("headers", None),
                proxies={
                    "http": self._my("proxy") or kwargs.get("proxy", False),
                    "https": self._my("proxy") or kwargs.get("proxy", False),
                },
                params=kwargs.get("params", None),
            )
            response = _RequestResponse(
                text=response.text,
                status=response.status_code,
                headers=response.headers,
                _response=response,
            )
        else:
            session: ClientSession = self._my("session") or ClientSession(
                headers=kwargs.get("headers", None)
            )
            async with session.request(
                method=kwargs.get("method", "get"),
                url=kwargs.get("url"),
                data=kwargs.get("data", None),
                json=kwargs.get("json", None),
                headers=kwargs.get("headers", None),
                params=kwargs.get("params", None),
            ) as response:
                response = _RequestResponse(
                    text=await response.text(),
                    status=response.status,
                    headers=response.headers,
                    _response=response,
                )
            if kwargs.get("close", True):
                await session.close()
        if response.status == 429:
            retry_after = response.headers.get("Retry-After", 1)
            await sleep(float(retry_after))
            kwargs.update({"retries": kwargs.get("retries", 0) + 1})
            return await self.request(**kwargs)
        return response

    async def get(self, *args, **kwargs):
        return await self.request(method="get", *args, **kwargs)

    async def post(self, *args, **kwargs):
        return await self.request(method="post", *args, **kwargs)


class Client(_Client):
    def __init__(self, **params: Unpack[_ClientParams]):
        super().__init__(**params)
        self.max_retries = 12
        self.headers = {"User-Agent": Faker().user_agent()}
        self.__dict__.update(**params)
