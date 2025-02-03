from ..parser import Parser
from ..items import _BaseItem
from typing import Unpack, AsyncGenerator, Literal, TypedDict, List


class KodikParser(Parser):
    def __init__(self, **kwargs: Unpack[Parser.ParserParams]):
        self.language = Parser.Language.RU
        self.token = None
        super().__init__(**kwargs)
        self.client.replace_headers(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Site": "same-origin",
            }
        )
        self.client.base_url = "https://kodik.info/"

    async def obtain_token(self) -> str:
        script_url = "https://kodik-add.com/add-players.min.js?v=2"
        response = await self.client.get(script_url)
        text = response.text
        token = text[text.find("token=") + 7 :]
        token = token[: token.find('"')]
        self.token = token
        return token
    
    class _SearchParams(TypedDict, total=False):
        query: str | int
        limit: int = 25
        id_type: Literal["shikimori", "kinopoisk", "imdb"] = None
        strict: bool = False
        with_details: bool = False,
        
    async def chunk_search(self, query: str | int, limit: int = 25, id_type: Literal["shikimori", "kinopoisk", "imdb"] = None, strict: bool = False, with_details: bool = False) -> AsyncGenerator[_BaseItem, None]:
        if not self.token:
            await self.obtain_token()

        search_params = {
            "token": self.token,
            "limit": limit,
            "with_material_data": "true",
            "strict": "true" if strict else "false",
        }

        if isinstance(query, int) or id_type:
            search_params[f"{id_type}_id"] = query
        else:
            search_params["title"] = query

        response = await self.client.post("https://kodikapi.com/search", data=search_params)
        response = response.json
        print(response)
        if not response["total"]:
            return
        
        results = response["results"]
        animes = []
        added_titles = set()

        for result in results:
            if result["type"] not in ["anime-serial", "anime"]:
                continue

            if result["title"] not in added_titles:
                info = {}
                if with_details:
                    info = await self.get_anime_info(result["id"])
                animes.append(
                    {
                        "id": result["id"],
                        "title": result["title"],
                        "title_orig": result.get("title_orig"),
                        "other_title": (result.get("other_title", [])).split(" / "),
                        "type": result.get("type"),
                        "year": result.get("year"),
                        "screenshots": result.get("screenshots"),
                        "shikimori_id": result.get("shikimori_id"),
                        "kinopoisk_id": result.get("kinopoisk_id"),
                        "imdb_id": result.get("imdb_id"),
                        "worldart_link": result.get("worldart_link"),
                        "link": result.get("link"),
                        "all_status": result.get("all_status"),
                        "description": result.get("material_data", {}).get(
                            "description", None
                        ),
                        "other_titles_en": result.get("other_titles_en", []),
                        "other_titles_jp": result.get("other_titles_jp", []),
                        "episode_count": info.get("episode_count", 0),
                        "translations": info.get("translations", None),
                    }
                )
                added_titles.add(result["title"])

        for i, result in enumerate(animes):
            yield animes[i]
        
    async def search(
        self,
        query: str | int,
        limit: int = 25,
        id_type: Literal["shikimori", "kinopoisk", "imdb"] = None,
        strict: bool = False,
        with_details: bool = False,
    ) -> List[_BaseItem]:
        results = []
        async for result in self.chunk_search(query, limit, id_type, strict, with_details):
            results.append(result)
        return results
    