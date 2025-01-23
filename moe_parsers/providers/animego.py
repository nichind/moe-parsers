from ..parser import Parser
from ..items import Anime
from typing import Unpack, List


class AniboomParser(Parser):
    def __init__(self, **kwargs: Unpack[Parser.ParserParams]):
        super().__init__(**kwargs)
        self.client.replace_headers({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://animego.org/",
        })
        self.client.base_url = "https://animego.org/"

    async def search(self, query: str) -> List[Anime]:
        ...
