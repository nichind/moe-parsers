from ..parser import Parser
from ..items import Anime
from typing import Unpack, List
from re import compile as re_compile


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
            "search/all", params={"type": "small", "q": query}
        )
        content = response.json.get("content", '')
        page = self.client.soup(content)
        results_list = page.find("div", {"class": "result-search-anime"}).find_all(
            "div", {"class": "result-search-item"}
        )
        results = []
        for result in results_list:
            print(result)
            data = {}
            data["data"] = {}
            data["title"] = result.find("h5").text.strip()
            data["year"] = result.find("span", {"class": "anime-year"}).text.strip()
            data["other_title"] = (
                result.find("div", {"class": "text-truncate"}).text.strip()
                if result.find("div", {"class": "text-truncate"})
                else ""
            )
            data["type"] = result.find(
                "a", {"href": re_compile(r".*anime/type.*")}
            ).text.strip()
            data["url"] = self.client.base_url[:-1] + result.find("h5").find("a").attrs["href"]
            data["anime_id"] = data["url"][data["url"].rfind("-") + 1 :]
            results.append(data)

        return results
    