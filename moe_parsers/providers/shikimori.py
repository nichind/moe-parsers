from ..parser import Parser
from ..items import _BaseItem, Anime, Character, Person, Manga
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

    graphql_query = {
        "mangas": """{\n  mangas({params}) {\n    id\n    malId\n    name\n    russian\n    licenseNameRu\n    english\n    japanese\n    synonyms\n    kind\n    score\n    status\n    volumes\n    chapters\n    airedOn {\n      year\n      month\n      day\n      date\n    }\n    releasedOn {\n      year\n      month\n      day\n      date\n    }\n    url\n    poster {\n      id\n      originalUrl\n      mainUrl\n    }\n    licensors\n    createdAt\n    updatedAt\n    isCensored\n    genres {\n      id\n      name\n      russian\n      kind\n    }\n    publishers {\n      id\n      name\n    }\n    externalLinks {\n      id\n      kind\n      url\n      createdAt\n      updatedAt\n    }\n    personRoles {\n      id\n      rolesRu\n      rolesEn\n      person {\n        id\n        name\n        poster {\n          id\n        }\n      }\n    }\n    characterRoles {\n      id\n      rolesRu\n      rolesEn\n      character {\n        id\n        name\n        poster {\n          id\n        }\n      }\n    }\n    related {\n      id\n      anime {\n        id\n        name\n      }\n      manga {\n        id\n        name\n      }\n      relationKind\n      relationText\n    }\n    scoresStats {\n      score\n      count\n    }\n    statusesStats {\n      status\n      count\n    }\n    description\n    descriptionHtml\n    descriptionSource\n  }\n}\n""",
        "animes": "{\n  animes({params}) {\n    id\n    malId\n    name\n    russian\n    licenseNameRu\n    english\n    japanese\n    synonyms\n    kind\n    rating\n    score\n    status\n    episodes\n    episodesAired\n    duration\n    airedOn {\n      year\n      month\n      day\n      date\n    }\n    releasedOn {\n      year\n      month\n      day\n      date\n    }\n    url\n    season\n    poster {\n      id\n      originalUrl\n      mainUrl\n    }\n    fansubbers\n    fandubbers\n    licensors\n    createdAt\n    updatedAt\n    nextEpisodeAt\n    isCensored\n    genres {\n      id\n      name\n      russian\n      kind\n    }\n    studios {\n      id\n      name\n      imageUrl\n    }\n    externalLinks {\n      id\n      kind\n      url\n      createdAt\n      updatedAt\n    }\n    personRoles {\n      id\n      rolesRu\n      rolesEn\n      person {\n        id\n        name\n        poster {\n          id\n        }\n      }\n    }\n    characterRoles {\n      id\n      rolesRu\n      rolesEn\n      character {\n        id\n        name\n        poster {\n          id\n        }\n      }\n    }\n    related {\n      id\n      anime {\n        id\n        name\n      }\n      manga {\n        id\n        name\n      }\n      relationKind\n      relationText\n    }\n    videos {\n      id\n      url\n      name\n      kind\n      playerUrl\n      imageUrl\n    }\n    screenshots {\n      id\n      originalUrl\n      x166Url\n      x332Url\n    }\n    scoresStats {\n      score\n      count\n    }\n    statusesStats {\n      status\n      count\n    }\n    description\n    descriptionHtml\n    descriptionSource\n  }\n}\n",
        "character": "{\n  characters({params}) {\n    id\n    malId\n    name\n    russian\n    japanese\n    synonyms\n    url\n    createdAt\n    updatedAt\n    isAnime\n    isManga\n    isRanobe\n    poster {\n      id\n      originalUrl\n      mainUrl\n    }\n    description\n    descriptionHtml\n    descriptionSource\n  }\n}\n",
        "person": "{\n  people({params}) {\n    id\n    malId\n    name\n    russian\n    japanese\n    synonyms\n    url\n    isSeyu\n    isMangaka\n    isProducer\n    website\n    createdAt\n    updatedAt\n    birthOn {\n      year\n      month\n      day\n      date\n    }\n    deceasedOn {\n      year\n      month\n      day\n      date\n    }\n    poster {\n      id\n      originalUrl\n      mainUrl\n    }\n  }\n}\n",
    }

    @classmethod
    def data2anime(cls, data) -> Anime:
        anime = Anime()
        anime.ids = {
            _BaseItem.IDType.MAL: data.get("malId"),
            _BaseItem.IDType.SHIKIMORI: data.get("id"),
        }
        anime.age_rating = Anime.AgeRating(data.get("rating", "unknown"))
        anime.title = {
            _BaseItem.Language.RUSSIAN: [data.get("russian", "")],
            _BaseItem.Language.ENGLISH: [data.get("english", "")],
            _BaseItem.Language.JAPANESE: [data.get("japanese", "")],
        }
        anime.type = Anime.Type(data.get("kind", "unknown"))
        anime.status = Anime.Status(data.get("status", "unknown"))
        anime.episode_duration = data.get("duration", 0)
        anime.started = datetime.strptime(data.get("airedOn", {}).get("date", ""), "%Y-%m-%d") if data.get("airedOn", {}).get("date") else None
        anime.released = datetime.strptime(data.get("releasedOn", {}).get("date", ""), "%Y-%m-%d") if data.get("releasedOn", {}).get("date") else None
        anime.studios = [studio["name"] for studio in data.get("studios", [])]
        anime.genres = {genre["kind"]: genre["name"] for genre in data.get("genres", [])}
        anime.directors = [Person(ids={_BaseItem.IDType.SHIKIMORI: p["person"]["id"], _BaseItem.IDType.MAL: p["person"].get("malId")}, name={_BaseItem.Language.ENGLISH: [p["person"]["name"]]}) for p in data.get("personRoles", []) if "Director" in p.get("rolesEn", [])]
        anime.producers = [Person(ids={_BaseItem.IDType.SHIKIMORI: p["person"]["id"], _BaseItem.IDType.MAL: p["person"].get("malId")}, name={_BaseItem.Language.ENGLISH: [p["person"]["name"]]}) for p in data.get("personRoles", []) if "Producer" in p.get("rolesEn", [])]
        anime.actors = [Person(ids={_BaseItem.IDType.SHIKIMORI: p["person"]["id"], _BaseItem.IDType.MAL: p["person"].get("malId")}, name={_BaseItem.Language.ENGLISH: [p["person"]["name"]]}) for p in data.get("personRoles", []) if "Voice Actor" in p.get("rolesEn", [])]
        anime.writers = [Person(ids={_BaseItem.IDType.SHIKIMORI: p["person"]["id"], _BaseItem.IDType.MAL: p["person"].get("malId")}, name={_BaseItem.Language.ENGLISH: [p["person"]["name"]]}) for p in data.get("personRoles", []) if "Script" in p.get("rolesEn", [])]
        anime.composers = [Person(ids={_BaseItem.IDType.SHIKIMORI: p["person"]["id"], _BaseItem.IDType.MAL: p["person"].get("malId")}, name={_BaseItem.Language.ENGLISH: [p["person"]["name"]]}) for p in data.get("personRoles", []) if "Music" in p.get("rolesEn", [])]
        anime.characters = [Character(ids={_BaseItem.IDType.SHIKIMORI: c["character"]["id"], _BaseItem.IDType.MAL: c["character"].get("malId")}, name={_BaseItem.Language.ENGLISH: [c["character"]["name"]]}, type=Character.Type(c["rolesEn"][0].lower())) for c in data.get("characterRoles", [])]
        anime.screenshots = data.get("screenshots", [])
        anime.related = data.get("related", [])
        anime.videos = data.get("videos", [])
        return anime

    @classmethod
    def data2person(cls, data) -> Person:
        person = Person()
        person.ids = {
            _BaseItem.IDType.MAL: data.get("malId"),
            _BaseItem.IDType.SHIKIMORI: data.get("id"),
        }
        person.name = {
            _BaseItem.Language.RUSSIAN: [data.get("russian", "")],
            _BaseItem.Language.ENGLISH: [data.get("name", "")],
            _BaseItem.Language.JAPANESE: [data.get("japanese", "")],
        }
        person.birthdate = datetime.strptime(data.get("birthOn", {}).get("date", ""), "%Y-%m-%d") if data.get("birthOn", {}).get("date") else None
        person.passingdate = datetime.strptime(data.get("deceasedOn", {}).get("date", ""), "%Y-%m-%d") if data.get("deceasedOn", {}).get("date") else None
        person.url = data.get("url", "")
        return person

    @classmethod
    def data2character(cls, data) -> Character:
        character = Character()
        character.ids = {
            _BaseItem.IDType.MAL: data.get("malId"),
            _BaseItem.IDType.SHIKIMORI: data.get("id"),
        }
        character.name = {
            _BaseItem.Language.RUSSIAN: [data.get("russian", "")],
            _BaseItem.Language.ENGLISH: [data.get("name", "")],
            _BaseItem.Language.JAPANESE: [data.get("japanese", "")],
        }
        character.description = data.get("description", "")
        character.url = data.get("url", "")
        return character



    class SearchArguments(TypedDict, total=False): 
        searchType: (
            List[Literal["animes", "mangas", "character", "person"]]
            | Literal["autocomplete", "all", "animes", "mangas", "character", "person"]
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
        if not isinstance(search_types, list):
            search_types = [search_types]
        if search_types == "all":
            search_types = ["animes", "mangas", "person", "character"]
        if "searchType" in kwargs:
            del kwargs["searchType"]
        for page in range(start_page, end_page + 1):
            for path in search_types:
                response = await self.client.post(
                    url=self.client.base_url + "api/graphql",
                    page=page,
                    json={
                        "operationName": None,
                        "variables": {},
                        "query": self.graphql_query.get(path).replace(
                            "{params}",
                            ", ".join(
                                f'{key}: "{",".join(value) if isinstance(value, list) else value}"'
                                if not isinstance(value, (int, float))
                                else f"{key}: {value}"
                                for key, value in kwargs.items()
                                if key not in ["startPage", "endPage"]
                            ),
                        ),
                    },
                )
                for result in response.json.get("data").get(path):
                    for key, value in {
                        "people": Person,
                        "character": Character,
                        "anime": Anime,
                        "manga": Manga,
                    }.items():
                        ...
                    yield self.data2anime(result)

    async def search(self, **kwargs: Unpack[SearchArguments]) -> List[_BaseItem]:
        return [item async for item in self.search_generator(**kwargs)]

    async def get_info(
        self,
        item_type: Literal["anime", "manga", "character", "person"],
        item_id: int,
        item: _BaseItem | Anime | Manga | Character | Person = None,
    ) -> _BaseItem:
        if item_type == "person":
            item_type = "people"
        elif item_type == "character":
            item_type = "characters"
        response = await self.client.get(
            url=self.client.base_url + "api/" + item_type + "/" + str(item_id),
        )
        data = response.json

        return data
