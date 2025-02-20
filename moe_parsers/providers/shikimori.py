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
        searchType: (
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
                    "doujin",
                    "manga",
                    "manhua",
                    "manhwa",
                    "light_novel",
                    "novel",
                    "one_shot",
                    "!doujin",
                    "!manga",
                    "!manhua",
                    "!manhwa",
                    "!light_novel",
                    "!novel",
                    "!one_shot",
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
        publisher: str | list
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
        isSeyu: bool
        isProducer: bool
        isMangaka: bool
        search: str

    async def search_generator(
        self, **kwargs: Unpack[SearchArguments]
    ) -> AsyncGenerator[_BaseItem, None]:
        """A generator which yields search results from Shikimori."""
        start_page = kwargs.get("startPage", 1)
        end_page = kwargs.get("endPage", start_page)
        limit = kwargs.get("limit", 20)
        kwargs["limit"] = limit
        search_types = kwargs.get("searchType", ["animes", "mangas"])

        if "searchType" in kwargs:
            del kwargs["searchType"]

        if "person" in search_types:
            search_types.remove("person")
            search_types.append("people/search")

        if "character" in search_types:
            search_types.remove("character")
            search_types.append("character/search")

        for page in range(start_page, end_page + 1):
            for path in search_types:
                response = await self.client.get(
                    url="https://shikimori.one/api/" + path,
                    page=page,
                    params={
                        key: ",".join(value) if isinstance(value, list) else value
                        for key, value in kwargs.items()
                    },
                )
                for result in response.json:
                    # item = 
                    yield result

    async def search(self, **kwargs: Unpack[SearchArguments]) -> List[_BaseItem]:
        return [item async for item in self.search_generator(**kwargs)]
