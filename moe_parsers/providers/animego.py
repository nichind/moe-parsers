from ..parser import Parser
from ..items import Anime
from typing import Unpack, List
from re import compile as re_compile
from json import loads


class AniboomParser(Parser):
    def __init__(self, **kwargs: Unpack[Parser.ParserParams]):
        super().__init__(**kwargs)
        self.client.replace_headers(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://animego.org/",
            }
        )
        self.client.base_url = "https://animego.org/"

    async def search(self, query: str) -> List[Anime]:
        response = await self.client.get(
            "search/all", params={"type": "big", "q": query}
        )
        # print(response.text)
        page = self.client.soup(response.text)
        results = []
        _ = page.find_all("div", {"class": "animes-grid-item"})
        for item in _:
            try:
                data = {}
                data["data"] = item.find("a", {"class": "d-block"})
                data["url"] = data["data"].attrs["href"]
                data["type"] = data["url"].rsplit("/", 2)[-2]
                data["item_id"] = (
                    data["url"][data["url"].rfind("-") + 1 :]
                    if data["type"] not in ["character", "person"]
                    else data["url"][data["url"].rfind("/") + 1 : data["url"].find("-")]
                )
                data["title"] = {}
                if data["type"] not in ["character", "person"]:
                    data["title"]["ru"] = item.find("a", {"href": data["url"], "title": True}.text)
                    try:
                        data["title"]["en"] = item.find("div", {"class": "text-gray-dark-6 small mb-1 d-none d-sm-block"}).find("div").text
                    except Exception:
                        ...
                else:
                    data["title"]["en"] = item.find("h3").find("a").text
                data["thumbnail"] = data["data"].find("div").attrs["data-original"]
            except AttributeError:
                print(">>>", item)
        return results
