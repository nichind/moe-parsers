from aiohttp import ClientSession, TCPConnector
from asyncio import sleep
from json import loads
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
    params: dict
    data: dict
    cookie: str
    proxy: str
    json: dict
    retries: int
    ratelimit_raise: bool
    max_retries: int


class _RequestResponse:
    status: int
    headers: dict
    text: str
    json: dict
    data: bytes
    soup: BeautifulSoup
    _response: dict

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

    class Exceptions:
        class BaseException(Exception):
            def __repr__(self):
                return f"{self.__class__.__name__}({self.__dict__})"

        class RateLimit(BaseException):
            def __repr__(self):
                return f"{self.__class__.__name__}({self.__dict__}). You can make the client automatically bypass this exception by setting ratelimit_raise=False in Client() or as a parameter in request()"

    def _my(self, key: str, default=None):
        return self.__dict__.get(key, default)

    def replace_headers(self, *dicts: dict, **headers: Unpack[_ClientHeaders]):
        for d in dicts:
            self._my("headers", {}).update(**d)
        sorted_headers = {
            k.replace("_", "-").title(): v
            for k, v in sorted(headers.items(), key=lambda x: x[0].lower())
        }
        self._my("headers", {}).update(sorted_headers)

    def soup(self, *args, **kwargs):
        return BeautifulSoup(*args, **kwargs, features="html.parser")

    async def request(self, *args, **kwargs: Unpack[RequestArgs]) -> _RequestResponse:
        if kwargs.get("retries", 0) > self._my("max_retries", 5):
            raise Exception("Too many retries")
        if not kwargs.get("url", None) and args and isinstance(args[0], str):
            kwargs["url"] = args[0]
        elif not kwargs.get("url", None):
            raise Exception("Missing url")
        kwargs["url"] = kwargs["url"].replace(" ", "%20")
        if not kwargs["url"].startswith("http"):
            kwargs["url"] = f"{self._my('base_url') or 'https://'}{kwargs['url']}"
        session: ClientSession = self._my("session") or ClientSession(
            headers=kwargs.get("headers", None),
            connector=TCPConnector(ssl=False)
            if self._my("proxy", None) or kwargs.get("proxy", None)
            else None,
        )
        if self._my("proxy") or kwargs.get("proxy", None):
            session._ssl = False
        async with session.request(
            method=kwargs.get("method", "get"),
            url=kwargs.get("url"),
            data=kwargs.get("data", None),
            json=kwargs.get("json", None),
            headers=kwargs.get("headers", None) or self._my("headers"),
            params=kwargs.get("params", None),
            proxy=kwargs.get("proxy", None) or self._my("proxy", None),
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
            if kwargs.get("ratelimit_raise", self._my("ratelimit_raise", True)):
                raise self.Exceptions.RateLimit
            retry_after = response.headers.get("Retry-After", 1)
            await sleep(float(retry_after))
            kwargs.update({"retries": kwargs.get("retries", 0) + 1})
            return await self.request(*args, **kwargs)
        return response

    async def get(self, *args, **kwargs: Unpack[RequestArgs]):
        return await self.request(method="get", *args, **kwargs)

    async def post(self, *args, **kwargs: Unpack[RequestArgs]):
        return await self.request(method="post", *args, **kwargs)

    async def put(self, *args, **kwargs: Unpack[RequestArgs]):
        return await self.request(method="put", *args, **kwargs)

    async def delete(self, *args, **kwargs: Unpack[RequestArgs]):
        return await self.request(method="delete", *args, **kwargs)


class Client(_Client):
    def __init__(self, **params: Unpack[_ClientParams]):
        super().__init__(**params)
        self.max_retries = 6
        self.headers = {"User-Agent": Faker().user_agent()}
        self.__dict__.update(**params)
