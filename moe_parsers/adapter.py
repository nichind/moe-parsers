from aiohttp import ClientSession, TCPConnector
from aiohttp.client import _RequestContextManager
from asyncio import sleep, wait, FIRST_COMPLETED, create_task, run
from json import loads
from typing import TypedDict, Literal, Unpack, List
from faker import Faker
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse


class _ProxyParams(TypedDict, total=False):
    protocol: Literal["http", "https", "socks4", "socks5"]
    ip: str
    port: str
    username: str
    password: str


class Proxy:
    def __init__(self, *args, url: str = None, **kwargs: Unpack[_ProxyParams]):
        self.latency = None
        self.client = None
        self.last_used = None
        self.use_count = 0
        if url or len(args) == 1:
            parsed = urlparse(url or args[0])
            self.ip = parsed.hostname
            self.port = parsed.port
            self.protocol = parsed.scheme
            self.username = parsed.username
            self.password = parsed.password
        elif args:
            self.ip = args[0]
            self.port = args[1]
            self.protocol = args[2] if len(args) > 2 else kwargs.get("protocol", "http")
            self.username = args[3] if len(args) > 3 else kwargs.get("username", None)
            self.password = args[4] if len(args) > 4 else kwargs.get("password", None)
        self.__dict__.update(**kwargs)

    @property
    def url(self):
        return (
            f"{self.protocol}://{self.username}:{self.password}@{self.ip}:{self.port}"
            if self.username and self.password
            else f"{self.protocol}://{self.ip}:{self.port}"
        )

    def __repr__(self):
        return f"Proxy({self.url})"


class ProxySwithcher:
    proxies: List[Proxy]

    def __init__(self, proxies: List[Proxy | str] = []):
        self.proxies = proxies

    async def check(self, proxy: Proxy | str) -> bool:
        try:
            start = datetime.now()
            if isinstance(proxy, str):
                proxy = Proxy(url=proxy)
            if not proxy.client:
                proxy.client = Client()
            response = await proxy.client.request(
                method="get",
                url="https://httpbin.org/ip",
                proxy=proxy.url if isinstance(proxy, Proxy) else proxy,
                ratelimit_raise=False,
                timeout=5,
                use_switcher=False,
            )
            if response.status != 200:
                raise Exception(f"Status code: {response.status}")
            proxy.latency = int((datetime.now() - start).total_seconds() * 1000)
            return proxy
        except Exception as exc:
            print(f"{proxy} failed the check: {exc}")
            return False

    async def checkadd(self, proxy: Proxy | str | List[Proxy | str]):
        if isinstance(proxy, list):
            tasks = []
            for p in proxy:
                task = create_task(self.checkadd(p))
                tasks.append(task)
                done, pending = await wait(tasks, return_when=FIRST_COMPLETED)
                for task in done:
                    await task
                tasks = list(pending)
            return
        _ = await self.check(proxy)
        if _:
            self.proxies.append(proxy if isinstance(proxy, Proxy) else _)
            return True
        return False

    def add(self, proxy: Proxy | str | List[Proxy | str]):
        if isinstance(proxy, list):
            for p in proxy:
                self.add(p)
            return
        self.proxies.append(proxy if isinstance(proxy, Proxy) else Proxy(url=proxy))

    def sort(self):
        self.proxies.sort(key=lambda x: (x.use_count, x.latency))

    def pick(self, ignore: List[Proxy | str] = []) -> Proxy:
        self.sort()
        for proxy in self.proxies:
            if proxy not in ignore and proxy.url not in ignore:
                return proxy
        return self.proxies[0]

    def get_by_url(self, url: str) -> Proxy:
        for proxy in self.proxies:
            if proxy.url == url:
                return proxy


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
    proxies: "ProxySwithcher" | List[Proxy | str]


class RequestArgs(TypedDict, total=False):
    session: ClientSession
    url: str
    method: Literal["get", "post", "put", "delete"]
    headers: _ClientHeaders
    params: dict
    data: dict
    cookie: str
    proxy: Proxy | str
    json: dict
    retries: int
    ratelimit_raise: bool
    max_retries: int
    ignore_set_cookie: bool
    timeout: int
    use_switcher: bool
    ignore_codes: List[int]


class RequestResponse:
    status: int
    headers: dict
    text: str
    json: dict
    data: bytes
    soup: BeautifulSoup
    _response: _RequestContextManager

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
        self.switcher = ProxySwithcher()
        self.__dict__.update(**params)
        if "proxies" in params and isinstance(params["proxies"], list):
            for proxy in params["proxies"]:
                run(self.switcher.checkadd(proxy))

    class Exceptions:
        class BaseException(Exception):
            def __repr__(self):
                return f"{self.__class__.__name__}({self.__dict__})"

        class RateLimit(BaseException):
            def __repr__(self):
                return f"{self.__class__.__name__}({self.__dict__}). You can make the client automatically bypass this exception by setting ratelimit_raise=False in Client() or as a parameter in request()"

    def _my(self, key: str, default=None):
        return self.__dict__.get(key, default)

    def json(self, text):
        return loads(text)

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

    async def close_session(self):
        if self._my("session"):
            await self._my("session").close()

    async def request(self, *args, **kwargs: Unpack[RequestArgs]) -> RequestResponse:
        print(kwargs.items())
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
        if (
            not kwargs.get("use_switcher", True)
            or len(self.switcher.proxies) == 0
            or "proxy" in kwargs
        ):
            proxy = kwargs.get("proxy", None) or self._my("proxy", None)
        else:
            proxy = self.switcher.pick(ignore=kwargs.get("ignore_proxies", []))
            proxy.last_used = datetime.now()
            proxy.use_count += 1
            proxy = proxy.url
        async with session.request(
            method=kwargs.get("method", "get"),
            url=kwargs.get("url"),
            data=kwargs.get("data", None),
            json=kwargs.get("json", None),
            headers=kwargs.get("headers", None) or self._my("headers"),
            params=kwargs.get("params", None),
            proxy=proxy,
            timeout=kwargs.get("timeout", None),
        ) as response:
            response = RequestResponse(
                text=await response.text(),
                status=response.status,
                headers=response.headers,
                _response=response,
            )
        print
        if self.switcher.get_by_url(proxy):
            self.switcher.get_by_url(proxy).latency = int(
                (
                    datetime.now() - self.switcher.get_by_url(proxy).last_used
                ).total_seconds()
                * 1000
            )
        if kwargs.get("close", True):
            await session.close()
        if (
            len(str(response.status)) == 3
            and str(response.status).startswith("5")
            and (
                response.status
                not in kwargs.get("ingore_codes", self._my("ingore_codes", []))
            )
        ):
            await sleep(0.2)
            kwargs.update({"retries": kwargs.get("retries", 0) + 1})
            if kwargs.get("use_switcher", True) and len(self.switcher.proxies) > 1:
                ignored = kwargs.get("ignore_proxies", [])
                ignored.append(self.switcher.get_by_url(proxy))
                kwargs.update({"ignore_proxies": ignored})
            print(
                f"{response} receieved code {response.status}, retrying... (disable this by providing the status code to the ignore_codes list parameter)"
            )
            return await self.request(*args, **kwargs)
        if response.status == 429:
            if kwargs.get("ratelimit_raise", self._my("ratelimit_raise", True)):
                raise self.Exceptions.RateLimit
            retry_after = response.headers.get("Retry-After", 1)
            await sleep(float(retry_after))
            kwargs.update({"retries": kwargs.get("retries", 0) + 1})
            if kwargs.get("use_switcher", True) and len(self.switcher.proxies) > 1:
                ignored = kwargs.get("ignore_proxies", [])
                ignored.append(self.switcher.get_by_url(proxy))
                kwargs.update({"ignore_proxies": ignored})
            return await self.request(*args, **kwargs)
        if "set-cookie" in response.headers.keys() and not kwargs.get(
            "ignore_set_cookie", False
        ):
            self.replace_headers(cookie=response.headers.get("set-cookie"))
        return response

    async def get(self, *args, **kwargs: Unpack[RequestArgs]) -> RequestResponse:
        return await self.request(method="get", *args, **kwargs)

    async def post(self, *args, **kwargs: Unpack[RequestArgs]) -> RequestResponse:
        return await self.request(method="post", *args, **kwargs)

    async def put(self, *args, **kwargs: Unpack[RequestArgs]) -> RequestResponse:
        return await self.request(method="put", *args, **kwargs)

    async def delete(self, *args, **kwargs: Unpack[RequestArgs]) -> RequestResponse:
        return await self.request(method="delete", *args, **kwargs)


class Client(_Client):
    def __init__(self, **params: Unpack[_ClientParams]):
        super().__init__(**params)
        self.max_retries = 6
        self.headers = {"User-Agent": Faker().user_agent()}
        self.__dict__.update(**params)
