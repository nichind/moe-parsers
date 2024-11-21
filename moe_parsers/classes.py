from aiohttp import ClientSession
from bs4 import BeautifulSoup
from asyncio import sleep
from io import BytesIO


class Errors:
    class PageNotFound(Exception):
        pass

    class PlayerBlocked(Exception):
        pass

    class TooManyRetries(Exception):
        pass


class VideoStream(object):
    def __init__(self, url: str, **kwargs):
        self.url = url
        self.content = None
        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

    def __repr__(self):
        return f"<{self.__class__.__name__} {', '.join([f'{k}={v}' for k, v in self.__dict__.items() if k != 'content'])}>"


class MPDPlaylist(VideoStream):
    def __init__(self, url: str, content: str, **kwargs):
        super().__init__(url, **kwargs)
        self.content = content

    def to_buffer(self):
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
    ):
        self.base_url = base_url
        self.headers = headers
        self.session = session
        self.proxy = proxy
        self.proxy_auth = proxy_auth

    def __repr__(self):
        return f'<{self.__class__.__name__} {", ".join([f"{k}={v}" for k, v in self.__dict__.items()])}>'


class Parser(object):
    def __init__(self, params: ParserParams, **kwargs):
        self.base_url = None
        self.headers = {}
        self.args = []
        self.session = None
        self.proxy = None
        self.proxy_auth = None

        try:
            import lxml

            self.lxml = True
        except ImportError:
            self.lxml = False

        for kwarg in params.__dict__:
            setattr(self, kwarg, params.__dict__[kwarg])

        for kwarg in kwargs:
            print(kwarg, kwargs[kwarg])
            setattr(self, kwarg, kwargs[kwarg])

    async def get(self, path: str, **kwargs) -> dict | str:
        if "retries" in kwargs and kwargs["retries"] > 30:
            raise Errors.TooManyRetries
        session = (
            ClientSession(
                headers=self.headers if "headers" not in kwargs else kwargs["headers"],
                proxy=self.proxy,
                proxy_auth=self.proxy_auth,
            )
            if not self.session or self.session.closed
            else self.session
        )
        try:
            url = (
                ""
                if self.base_url is None or path.startswith("http")
                else self.base_url
            ) + path
            async with session.get(
                url,
                params=kwargs["params"] if "params" in kwargs else None,
            ) as response:
                if response.status == 429:
                    await sleep(
                        response.headers["Retry-After"]
                        if "retry-after" in response.headers
                        else 1
                    )
                    return await self.get(
                        path,
                        retries=1 if "retries" not in kwargs else kwargs["retries"] + 1,
                        **kwargs,
                    )
                elif response.status == 404:
                    raise Errors.PageNotFound(f"Page not found: {url}")
                try:
                    if "text" in kwargs.keys() and kwargs["text"]:
                        raise Exception
                    response = await response.json()
                except Exception:
                    response = await response.text()
        finally:
            if "close" in kwargs and kwargs["close"] is False:
                return response
            await session.close()
        return response

    async def soup(self, *args, **kwargs):
        return BeautifulSoup(
            *args, **kwargs, features="lxml" if self.lxml else "html.parser"
        )

    def __repr__(self):
        return f"""<{self.__class__.__name__} "{self.base_url}">"""


class Anime(object):
    def __init__(self, *args, **kwargs):
        self.orig_title = None
        self.title = None
        self.anime_id = None
        self.id_type = None
        self.url = None
        self.episodes = None
        self.total_episodes = None
        self.type = None
        self.status = None
        self.year = None
        self.parser = None
        self.translations = None
        self.data = None
        self.args = args
        for kwarg in kwargs:
            setattr(self, kwarg, kwargs[kwarg])

    def __repr__(self):
        return f"""<{self.__class__.__name__} "{self.title if len(self.title) < 30 else self.title[:30] + '...'}">"""
