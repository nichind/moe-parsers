from re import S
from select import KQ_NOTE_LOWAT
from time import strftime

from pkg_resources import yield_lines
from ..parser import Parser
from ..items import _BaseItem, Anime, Character, Person
from typing import Literal, TypedDict, Unpack, AsyncGenerator, List
from datetime import datetime
from cutlet import Cutlet
from difflib import SequenceMatcher


class ShikimoriParser(Parser):
    def __init__(self, **kwargs: Unpack[Parser.ParserParams]):
        self.language = Parser.Language.RU
        super().__init__(**kwargs)
        self.client.replace_headers(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Referer": "https://shikimori.one/",
                "User-Agent": "https://github.com/nichind/moe-parsers",
            }
        )
        self.client.base_url = "https://shikimori.one/"

    class SearchArguments(TypedDict, total=False):
        searachType: (
            List[Literal["animes", "mangas", "character", "person"]]
            | Literal["autocomplete", "all"]
        )
        startPage: int
        endPage: int
        limit: int
        order: Literal[
            "id",
            "id_desc",
            "ranked",
            "kind",
            "popularity",
            "name",
            "aired_on",
            "episodes",
            "status",
            "random",
            "ranked_random",
            "ranked_shiki",
            "created_at",
            "created_at_desc",
        ]
        kind: (
            List[
                Literal[
                    "movie",
                    "music",
                    "ona",
                    "ova",
                    "special",
                    "tv",
                    "tv_13",
                    "tv_24",
                    "tv_48",
                    "tv_special",
                    "pv",
                    "cm",
                    "!movie",
                    "!music",
                    "!ona",
                    "!ova",
                    "!special",
                    "!tv",
                    "!tv_13",
                    "!tv_24",
                    "!tv_48",
                    "!tv_special",
                    "!pv",
                    "!cm",
                ]
            ]
            | str
        )
        status: (
            List[
                Literal[
                    "anons", "ongoing", "released", "!anons", "!ongoing", "!released"
                ]
            ]
            | str
        )
        season: List[str] | str
        score: int
        duration: List[Literal["S", "D", "F", "!S", "!D", "!F"]] | str
        rating: (
            List[
                Literal[
                    "none",
                    "g",
                    "pg",
                    "pg_13",
                    "r",
                    "r_plus",
                    "rx",
                    "!none",
                    "!g",
                    "!pg",
                    "!pg_13",
                    "!r",
                    "!r_plus",
                    "!rx",
                ]
            ]
            | str
        )
        origin: (
            List[
                Literal[
                    "card_game",
                    "novel",
                    "radio",
                    "game",
                    "unknown",
                    "book",
                    "light_novel",
                    "web_novel",
                    "original",
                    "picture_book",
                    "music",
                    "manga",
                    "visual_novel",
                    "other",
                    "web_manga",
                    "four_koma_manga",
                    "mixed_media",
                    "!card_game",
                    "!novel",
                    "!radio",
                    "!game",
                    "!unknown",
                    "!book",
                    "!light_novel",
                    "!web_novel",
                    "!original",
                    "!picture_book",
                    "!music",
                    "!manga",
                    "!visual_novel",
                    "!other",
                    "!web_manga",
                    "!four_koma_manga",
                    "!mixed_media",
                ]
            ]
            | str
        )
        genre: str | list
        studio: str | list
        franchaise: str | list
        censored: bool
        mylist: (
            List[
                Literal[
                    "planned",
                    "!planned",
                    "watching",
                    "!watching",
                    "rewatching",
                    "!rewatching",
                    "completed",
                    "!completed",
                    "on_hold",
                    "!on_hold",
                    "dropped",
                    "!dropped",
                ]
            ]
            | str
        )
        ids: str | list
        excludeIds: str | list
        search: str

    async def search_generator(
        self, **kwargs: Unpack[SearchArguments]
    ) -> AsyncGenerator[_BaseItem, None]:
        if "startPage" not in kwargs:
            kwargs["startPage"] = 1
        if "endPage" not in kwargs:
            kwargs["endPage"] = 1
        if "limit" not in kwargs:
            kwargs["limit"] = 50
        for page in range(kwargs["endPage"] - kwargs["startPage"] + 1):
            response = await self.client.get(
                url="https://shikimori.one/api/animes", page=page + 1, params={**kwargs}
            )
            yield response.json

    async def w(self):
        await self.search_generator()
