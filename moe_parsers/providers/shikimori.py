from ..core.parser import Parser
from ..core.items import _BaseItem, Anime, Character, Person, Manga
from typing import Literal, TypedDict, Unpack, AsyncGenerator, List
from datetime import datetime
from cutlet import Cutlet
from difflib import SequenceMatcher


katsu = Cutlet()


class Shikimori(Parser):
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
        "mangas": "{mangas({params}) {id malId name russian licenseNameRu english japanese synonyms kind score status volumes chapters airedOn {date} releasedOn {date} url poster {id originalUrl mainUrl} licensors createdAt updatedAt isCensored genres {id name russian kind} publishers {id name} externalLinks {id kind url createdAt updatedAt} personRoles {id rolesRu rolesEn person {id malId name russian japanese synonyms url isSeyu isMangaka isProducer website createdAt updatedAt birthOn {date} deceasedOn {date} poster {id originalUrl mainUrl previewUrl}}} characterRoles {id rolesRu rolesEn character {id malId name russian japanese synonyms description url createdAt updatedAt isAnime isManga isRanobe poster {id originalUrl mainUrl previewUrl} description descriptionHtml descriptionSource}} related {id anime {id name} manga {id name} relationKind relationText} scoresStats {score count} statusesStats {status count} description descriptionHtml descriptionSource}}",
        "animes": "{animes({params}) {id malId name russian licenseNameRu english japanese synonyms kind rating score status episodes episodesAired duration airedOn {date} releasedOn {date} url season poster {id originalUrl mainUrl} fansubbers fandubbers licensors nextEpisodeAt isCensored genres {id name russian kind} studios {id name imageUrl} externalLinks {id kind url createdAt updatedAt} personRoles {id rolesRu rolesEn person {id malId name russian japanese synonyms url isSeyu isMangaka isProducer website birthOn {date} deceasedOn {date} poster {id originalUrl mainUrl previewUrl}}} characterRoles {id rolesRu rolesEn character {id malId name russian japanese synonyms description url isAnime isManga isRanobe poster {id originalUrl mainUrl previewUrl} description descriptionHtml descriptionSource}} related {id anime {id name} manga {id name} relationKind relationText} videos {id url name kind playerUrl imageUrl} screenshots {id originalUrl x166Url} scoresStats {score count} statusesStats {status count} description descriptionSource}}",
        "characters": "{characters({params}) {id malId name russian japanese synonyms url createdAt updatedAt isAnime isManga isRanobe poster {id originalUrl mainUrl} description descriptionHtml descriptionSource}}",
        "people": "{people({params}) {id malId name russian japanese synonyms url isSeyu isMangaka isProducer website createdAt updatedAt birthOn {date} deceasedOn {date} poster {id originalUrl mainUrl}}}",
        "autocomplete": "{animes({params}) {id malId name russian licenseNameRu english japanese synonyms kind rating score status season poster {previewUrl} nextEpisodeAt genres {id name russian kind} studios {id name}} mangas({params}) {id malId name russian licenseNameRu english japanese synonyms kind score status volumes chapters poster {previewUrl} isCensored genres {id name russian kind} publishers {id name}}}",
    }

    @classmethod
    def data2anime(cls, data) -> Anime:
        anime = Anime()
        anime.data = data
        anime.ids = {
            _BaseItem.IDType.MAL: data.get("malId"),
            _BaseItem.IDType.SHIKIMORI: data.get("id"),
        }
        anime.age_rating = data.get("rating", "unknown") if str(data.get("rating")).lower() != "none" else "unknown"
        anime.title = {
            _BaseItem.Language.RUSSIAN: [data.get("russian", "")],
            _BaseItem.Language.ENGLISH: [data.get("english", "")],
            _BaseItem.Language.JAPANESE: [data.get("japanese", "")],
            _BaseItem.Language.ROMAJI: [],
        }
        for title in anime.title[_BaseItem.Language.JAPANESE]:
            rom = katsu.romaji(title).title()
            if rom in anime.title[_BaseItem.Language.ENGLISH]:
                continue
            if rom and len(rom.strip()) // 2 > rom.count("?") and rom not in anime.title[_BaseItem.Language.ROMAJI]:
                anime.title[_BaseItem.Language.ROMAJI].append(rom)
        anime.thumbnail = data.get("poster", {}).get("mainUrl")
        anime.type = data.get("kind", "unknown")
        anime.status = data.get("status", "unknown").replace("anons", "announced")
        anime.episode_duration = data.get("duration", 0)
        anime.started = (
            datetime.strptime(data.get("airedOn", {}).get("date", ""), "%Y-%m-%d")
            if data.get("airedOn", {}).get("date")
            else None
        )
        anime.released = (
            datetime.strptime(data.get("releasedOn", {}).get("date", ""), "%Y-%m-%d")
            if data.get("releasedOn", {}).get("date")
            else None
        )
        anime.studios = [studio["name"] for studio in data.get("studios", [])]
        anime.genres = {genre["kind"]: genre["name"] for genre in data.get("genres", [])}
        anime.directors = [
            cls.data2person(p["person"]) for p in data.get("personRoles", []) if "Director" in p.get("rolesEn", [])
        ]
        anime.producers = [
            cls.data2person(p["person"]) for p in data.get("personRoles", []) if "Producer" in p.get("rolesEn", [])
        ]
        anime.actors = [
            cls.data2person(p["person"]) for p in data.get("personRoles", []) if "Voice Actor" in p.get("rolesEn", [])
        ]
        anime.writers = [
            cls.data2person(p["person"]) for p in data.get("personRoles", []) if "Script" in p.get("rolesEn", [])
        ]
        anime.composers = [
            cls.data2person(p["person"]) for p in data.get("personRoles", []) if "Music" in p.get("rolesEn", [])
        ]
        anime.characters = [
            Character(
                type=Character.Type(character.get("rolesEn", ["unknown"])[0].lower()),
                **cls.data2character(character.get("character", {})).__dict__,
            )
            for character in data.get("characterRoles", [])
        ]
        anime.screenshots = data.get("screenshots", [])
        anime.related = data.get("related", [])
        anime.videos = data.get("videos", [])
        anime.description = {
            _BaseItem.Language.RUSSIAN: data.get("description", ""),
        }
        anime.external_links = data.get("externalLinks", [])
        return anime

    @classmethod
    def data2manga(cls, data) -> Manga:
        manga = Manga()
        manga.data = data
        manga.ids = {
            _BaseItem.IDType.MAL: data.get("malId"),
            _BaseItem.IDType.SHIKIMORI: data.get("id"),
        }
        manga.age_rating = data.get("rating", "unknown") if str(data.get("rating")).lower() != "none" else "unknown"
        manga.title = {
            _BaseItem.Language.RUSSIAN: [data.get("russian", "")],
            _BaseItem.Language.ENGLISH: [data.get("english", "")],
            _BaseItem.Language.JAPANESE: [data.get("japanese", "")],
            _BaseItem.Language.ROMAJI: [],
        }
        for title in manga.title[_BaseItem.Language.JAPANESE]:
            if katsu.romaji(title).title() not in manga.title[_BaseItem.Language.ROMAJI]:
                manga.title[_BaseItem.Language.ROMAJI].append(katsu.romaji(title).title())
        manga.status = data.get("status", "unknown").replace("anons", "announced")
        for title in manga.title[_BaseItem.Language.JAPANESE]:
            rom = katsu.romaji(title).title()
            if rom in manga.title[_BaseItem.Language.ENGLISH]:
                continue
            if rom and len(rom.strip()) // 2 > rom.count("?") and rom not in manga.title[_BaseItem.Language.ROMAJI]:
                manga.title[_BaseItem.Language.ROMAJI].append(rom)
        manga.thumbnail = data.get("poster", {}).get("mainUrl")
        manga.type = data.get("kind", "unknown")
        manga.status = data.get("status", "unknown")
        manga.volumes = data.get("volumes", 0)
        manga.chapters = data.get("chapters", 0)
        manga.started = (
            datetime.strptime(data.get("airedOn", {}).get("date", ""), "%Y-%m-%d")
            if data.get("airedOn", {}).get("date")
            else None
        )
        manga.released = (
            datetime.strptime(data.get("releasedOn", {}).get("date", ""), "%Y-%m-%d")
            if data.get("releasedOn", {}).get("date")
            else None
        )
        manga.studios = [studio["name"] for studio in data.get("studios", [])]
        manga.genres = {genre["kind"]: genre["name"] for genre in data.get("genres", [])}
        manga.characters = [
            Character(
                type=Character.Type(character.get("rolesEn", ["unknown"])[0].lower()),
                **cls.data2character(character.get("character", {})).__dict__,
            )
            for character in data.get("characterRoles", [])
        ]
        manga.description = {
            _BaseItem.Language.RUSSIAN: data.get("description", ""),
        }
        manga.external_links = data.get("externalLinks", [])
        return manga

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
            _BaseItem.Language.ROMAJI: [],
        }
        for name in person.name[_BaseItem.Language.JAPANESE]:
            if katsu.romaji(name).title() not in person.name[_BaseItem.Language.ROMAJI]:
                person.name[_BaseItem.Language.ROMAJI].append(katsu.romaji(name).title())
        person.thumbnail = data.get("poster", {}).get("mainUrl") if data.get("poster") else None
        person.image = data.get("poster", {}).get("mainUrl") if data.get("poster") else None
        person.birthdate = (
            datetime.strptime(data.get("birthOn", {}).get("date", ""), "%Y-%m-%d")
            if data.get("birthOn", {}).get("date")
            else None
        )
        person.passingdate = (
            datetime.strptime(data.get("deceasedOn", {}).get("date", ""), "%Y-%m-%d")
            if data.get("deceasedOn", {}).get("date")
            else None
        )
        person.url = data.get("url", "")
        person.description = {
            _BaseItem.Language.RUSSIAN: data.get("description", ""),
        }
        return person

    @classmethod
    def data2character(cls, data) -> Character:
        character = Character()
        character.data = data
        character.ids = {
            _BaseItem.IDType.MAL: data.get("malId"),
            _BaseItem.IDType.SHIKIMORI: data.get("id"),
        }
        character.name = {
            _BaseItem.Language.RUSSIAN: [data.get("russian", "")],
            _BaseItem.Language.ENGLISH: [data.get("name", "")],
            _BaseItem.Language.JAPANESE: [data.get("japanese", "")],
            _BaseItem.Language.ROMAJI: [],
        }
        for name in character.name[_BaseItem.Language.JAPANESE]:
            character.name[_BaseItem.Language.ROMAJI].append(katsu.romaji(name).title())
        character.thumbnail = data.get("poster", {}).get("previewUrl", None) if data.get("poster") else None
        character.description = {
            _BaseItem.Language.RUSSIAN: data.get("description", ""),
        }
        character.url = data.get("url", "")
        return character

    async def search_generator(
        self, *args, **kwargs: Unpack["SearchArguments"]
    ) -> AsyncGenerator[Anime | Manga | Character | Person, None]:
        start_page = kwargs.get("startPage", 1)
        end_page = kwargs.get("endPage", start_page)
        limit = kwargs.get("limit", 20)
        kwargs["limit"] = limit
        search_types = kwargs.get("searchType", ["animes", "mangas"])
        if search_types == "all":
            search_types = ["animes", "mangas", "people", "characters"]
        if not isinstance(search_types, list):
            search_types = [search_types]
        if "searchType" in kwargs:
            del kwargs["searchType"]
        if not kwargs.get("search", None) and len(args) == 1 and isinstance(args[0], str):
            kwargs["search"] = args[0]
        for page in range(start_page, end_page + 1):
            kwargs["page"] = page
            for path in search_types:
                if path == "autocomplete":
                    async for item in self.autocomplete_generator(**kwargs):
                        yield item
                else:
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
                                    if not isinstance(value, (int, float)) and key not in ["order"]
                                    else f"{key}: {value}"
                                    for key, value in kwargs.items()
                                    if key not in ["startPage", "endPage"]
                                ),
                            ),
                        },
                    )
                    for result_type, results in response.json.get("data", {}).items():
                        for result in results:
                            yield {
                                "animes": self.data2anime,
                                "mangas": self.data2manga,
                                "characters": self.data2character,
                                "people": self.data2person,
                            }[result_type](result)

    async def search(
        self, sort_by_match: bool = False, **kwargs: Unpack["SearchArguments"]
    ) -> List[Anime | Manga | Character | Person]:
        results = [item async for item in self.search_generator(**kwargs)]
        if kwargs.get("searchType", "animes") == "autocomplete" and kwargs.get("search", None):
            if results:
                search_query = kwargs.get("search", None)
                if search_query and sort_by_match:
                    results.sort(
                        key=lambda item: SequenceMatcher(
                            None,
                            search_query.lower(),
                            (
                                item.title.get(_BaseItem.Language.ROMAJI, [None])[0]
                                or item.title.get(_BaseItem.Language.ENGLISH, [None])[0]
                                or item.name.get(_BaseItem.Language.ROMAJI, [None])[0]
                                or item.name.get(_BaseItem.Language.ENGLISH, [None])[0]
                            ).lower(),
                        ).ratio(),
                        reverse=True,
                    )
        return results[0] if len(results) == 1 else results

    async def autocomplete_generator(
        self, **kwargs: Unpack["SearchArguments"]
    ) -> AsyncGenerator[Anime | Manga | Character | Person, None]:
        yield _BaseItem()

    async def get_info_generator(
        self,
        item_type: Literal["animes", "mangas", "characters", "people"]
        | List[Literal["animes", "mangas", "characters", "people"]],
        item_id: int | str,
    ) -> AsyncGenerator[
        Anime | Manga | Character | Person | List[Anime | Manga | Character | Person],
        None,
    ]:
        async for result in self.search_generator(
            ids=item_id,
            searchType=item_type,
            limit=str(item_id).count(",") if str(item_id).count(",") > 0 else 1,
        ):
            yield result

    async def get_info(
        self,
        item_type: Literal["animes", "mangas", "characters", "people"]
        | List[Literal["animes", "mangas", "characters", "people"]],
        item_id: int | str,
        item: Anime | Manga | Character | Person = None,
    ) -> List[Anime | Manga | Character | Person] | Anime | Manga | Character | Person:
        results = []
        async for result in self.get_info_generator(item_type, item_id):
            results += [result]
        if len(results) == 1:
            if item and isinstance(item, type(results[0])):
                item.__dict__ == results[0].__dict__
        return results[0] if len(results) == 1 else results

    class SearchArguments(TypedDict, total=False):
        searchType: (
            List[Literal["animes", "mangas", "characters", "people"]]
            | Literal["autocomplete", "all", "animes", "mangas", "characters", "people"]
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
        status: List[Literal["anons", "ongoing", "released", "!anons", "!ongoing", "!released"]] | str
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
