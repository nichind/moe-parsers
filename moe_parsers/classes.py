from aiohttp import ClientSession
from bs4 import BeautifulSoup
from asyncio import sleep
from io import BytesIO
from typing import Literal, List, Self
from datetime import datetime
import os


class Exceptions:
    class PageNotFound(Exception):
        pass

    class PlayerBlocked(Exception):
        pass

    class TooManyRetries(Exception):
        pass


class Media(object):
    def __init__(self, url: str, **kwargs):
        self.url = url
        self.content = None
        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

    def __repr__(self):
        return f"<{self.__class__.__name__} {', '.join([f'{k}={v}' for k, v in self.__dict__.items() if k != 'content'])}>"


class MPDPlaylist(Media):
    def __init__(self, url: str, content: str, **kwargs):
        super().__init__(url, **kwargs)
        self.content = content

    def buffer(self) -> BytesIO:
        buffer = BytesIO()
        buffer.write(self.content)
        buffer.seek(0)
        return buffer


class M3U8Playlist(Media):
    def __init__(self, url: str, content: str, **kwargs):
        super().__init__(url, **kwargs)
        self.content = content

    def buffer(self) -> BytesIO:
        buffer = BytesIO()
        buffer.write(self.content)
        buffer.seek(0)
        return buffer


class ParserParams:
    def __init__(
        self,
        base_url: str,
        headers: dict = {},
        session: ClientSession = None,
        proxy: str = None,
        proxy_auth: str = None,
        language: str = None,
    ):
        self.base_url = base_url
        self.headers = headers
        self.session = session
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.language = language

    def __repr__(self):
        return f'<{self.__class__.__name__} {", ".join([f"{k}={v}" for k, v in self.__dict__.items()])}>'


class Parser(object):
    def __init__(self, params: ParserParams = None, **kwargs):
        self.base_url = None
        self.headers = {}
        self.args = []
        self.session = None
        self.proxy = None
        self.proxy_auth = None
        self.language = None

        try:
            import lxml

            self.lxml = True
        except ImportError:
            self.lxml = False

        if params:
            for kwarg in params.__dict__:
                setattr(self, kwarg, params.__dict__[kwarg])

        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

    def list_providers(**filters) -> List[Self]:
        """
        List all supported providers by filters
        """
        all_providers = []
        for provider in os.listdir(os.path.dirname(__file__) + "/providers"):
            if os.path.isfile(os.path.dirname(__file__) + "/providers/" + provider):
                _provider = __import__(
                    f"moe_parsers.providers.{provider[:-3]}",
                    globals(),
                    locals(),
                    ["*"],
                    0,
                )
                try:
                    for cl in _provider.__dict__:
                        if str(cl).endswith("Parser") and str(cl) != "Parser":
                            parser = _provider.__dict__[str(cl)]()
                            for kwarg in filters:
                                if getattr(parser, kwarg) != filters[kwarg]:
                                    break
                            else:
                                if parser.__class__.__name__ not in [
                                    x.__class__.__name__ for x in all_providers
                                ]:
                                    all_providers.append(parser)
                except AttributeError:
                    pass
        return all_providers

    async def get(self, path: str, **kwargs) -> dict | str:
        return await self.request(path, "get", **kwargs)

    async def post(self, path: str, **kwargs) -> dict | str:
        return await self.request(path, "post", **kwargs)

    async def request(
        self, path: str, request_type: Literal["get", "post"] = "get", **kwargs
    ) -> dict | str:
        retries = kwargs.get("retries", 0)
        if retries > 5:
            raise Exceptions.TooManyRetries

        if self.proxy or kwargs.get("proxy", False):
            import requests

            url = (
                f"{kwargs.get('base_url', self.base_url)}{path}"
                if not path.startswith("http")
                else path
            )
            proxies = {
                "http": self.proxy or kwargs.get("proxy", False),
                "https": self.proxy or kwargs.get("proxy", False),
            }
            try:
                if request_type == "get":
                    response = requests.get(
                        url,
                        params=kwargs.get("params"),
                        headers=kwargs.get("headers", self.headers),
                        proxies=proxies,
                    )
                else:
                    response = requests.post(
                        url,
                        data=kwargs.get("data"),
                        headers=kwargs.get("headers", self.headers),
                        proxies=proxies,
                    )
                if response.status_code == 429:
                    kwargs["retries"] = retries + 1
                    return await self.request(path, **kwargs)
                elif response.status_code == 404:
                    raise Exceptions.PageNotFound(f"Page not found: {url}")
                if kwargs.get("text", False):
                    return response.text
                return response.json()
            except requests.exceptions.ProxyError as exc:
                raise Exceptions.ConnectionError(f"Proxy error: {exc}")
        else:
            session = (
                ClientSession(
                    headers=kwargs.get("headers", self.headers),
                )
                if not self.session or self.session.closed
                else self.session
            )
            try:
                url = (
                    f"{kwargs.get('base_url', self.base_url)}{path}"
                    if not path.startswith("http")
                    else path
                )
                async with (
                    session.get(url, params=kwargs.get("params"))
                    if request_type == "get"
                    else session.post(url, data=kwargs.get("data"))
                ) as response:
                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After", 1)
                        await sleep(float(retry_after))
                        kwargs["retries"] = retries + 1
                        return await self.request(path, **kwargs)
                    elif response.status == 404:
                        raise Exceptions.PageNotFound(f"Page not found: {url}")
                    try:
                        if kwargs.get("text", False):
                            return await response.text()
                        return await response.json()
                    except Exception:
                        return await response.text()
            except OSError:
                kwargs["retries"] = retries + 1
                await sleep(1)
                return await self.request(path, **kwargs)
            finally:
                if kwargs.get("close", True):
                    await session.close()

    async def soup(self, *args, **kwargs):
        return BeautifulSoup(
            *args, **kwargs, features="lxml" if self.lxml else "html.parser"
        )

    def __repr__(self):
        return f"""<{self.__class__.__name__} "{self.base_url}">"""


class Anime(object):
    def __init__(self, *args, **kwargs):
        self.orig_title: str = None
        self.title: str = None
        self.anime_id: int | str = None
        self.id_type: str = None
        self.url: str = None
        self.episodes: List[Anime.Episode] = None
        self.total_episodes: int = None
        self.type: str = self.Type.UNKNOWN
        self.year: int | str = None
        self.parser: Parser = None
        self.translations: dict = None
        self.data: dict = None
        self.language: str = None
        self.status: str = self.Status.UNKNOWN
        self.args = args
        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

    class Episode(dict):
        def __init__(self, **kwargs):
            self.anime_id: int | str = None
            self.anime_url: str = None
            self.id_type: str = None
            self.episode_num = None
            self.episode_id = None
            self.status: str = self.Status.UNKNOWN
            self.title: str = None
            self.date: datetime = None
            self.videos: List = []
            for kwarg in kwargs:
                setattr(self, kwarg, kwargs[kwarg])

        class Status:
            RELEASED = "Released"
            DELAYED = "Delayed"
            ANNOUNCED = "Announced"
            UNKNOWN = "Unknown"

        def __repr__(self):
            return f"""<{self.__class__.__name__} {self.episode_num} "{self.title if self.title and len(self.title) < 50 else (self.title[:47] + '...' if self.title else '')}" ({self.status}{' '+str(self.date.strftime('%Y-%m-%d')) if self.date else ''})>"""

    class Status:
        ONGOING = "Ongoing"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"
        HIATUS = "Hiatus"
        UNKNOWN = "Unknown"

    class Type:
        TV = "TV"
        MOVIE = "Movie"
        OVA = "OVA"
        ONA = "ONA"
        MUSIC = "Music"
        SPECIAL = "Special"
        UNKNOWN = "Unknown"

    def __repr__(self):
        return f"""<{self.__class__.__name__} "{self.title if len(self.title) < 50 else self.title[:47] + '...'}" "{self.orig_title if len(self.orig_title) < 50 else self.orig_title[:47] + '...'}">"""
