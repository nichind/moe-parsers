from ..parser import Parser
from ..items import _BaseItem
from typing import Unpack, AsyncGenerator


class AniboomParser(Parser):
    def __init__(self, **kwargs: Unpack[Parser.ParserParams]):
        self.language = Parser.Language.RU
        super().__init__(**kwargs)
        self.client.replace_headers(
            {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://animego.org/",
                "Sec-Fetch-Site": "same-origin",
            }
        )
        self.client.base_url = "https://animego.org/"

    async def search(self, query: str) -> AsyncGenerator[_BaseItem, None]:
        response = await self.client.get(
            "search/all", params={"type": "big", "q": query}
        )
        page = self.client.soup(response.text)  # yummy!
        items = page.find_all("div", {"class": "animes-grid-item"})

        for item in items:
            try:
                data = {}
                data["data"] = item.find("a", {"class": "d-block"})
                data["url"] = data["data"].attrs["href"]
                data["type"] = data["url"].rsplit("/", 2)[-2]

                if data["type"] not in ["character", "person"]:
                    data["item_id"] = data["url"].split("-")[-1]
                else:
                    data["item_id"] = data["url"].split("/")[-1].split("-")[0]
                data["title"] = {}
                if data["type"] not in ["character", "person"]:
                    title_ru = item.find("a", {"href": data["url"], "title": True})
                    data["title"]["ru"] = title_ru["title"] if title_ru else None
                    title_en_container = item.find(
                        "div", {"class": "text-gray-dark-6 small mb-1"}
                    ) or item.find(
                        "div",
                        {"class": "text-gray-dark-6 small mb-1 d-none d-sm-block"},
                    )
                    data["title"]["en"] = (
                        title_en_container.div.text if title_en_container else None
                    )
                else:
                    data["title"]["en"] = (
                        item.find(
                            "div", {"class": "text-gray-dark-6 small mb-1"}
                        ).div.text
                        if item.find("div", {"class": "text-gray-dark-6 small mb-1"})
                        else None
                    )
                    data["title"]["ru"] = (
                        item.find("h3", {"class": "h5 font-weight-normal"}).find("a")[
                            "title"
                        ]
                        if item.find("h3", {"class": "h5 font-weight-normal"})
                        else None
                    )

                thumbnail = item.find("div", {"class": "anime-grid-lazy lazy"})
                data["thumbnail"] = thumbnail["data-original"] if thumbnail else None
                self.client.replace_headers(
                    {
                        "Cookie": response.headers["Set-Cookie"],
                    }
                )
                yield data
            except AttributeError as e:
                continue

    async def get_info(self, link: str) -> dict:
        anime_data = {}
        self.client.replace_headers({
                "accept": "application/json, text/javascript, */*; q=0.01",
                "cookie": self.client.headers.get("cookie", ""),
                "referer": "https://animego.org/",
                "x-requested-with": "XMLHttpRequest"
            })
        response = await self.client.get(link + "")
        soup = self.client.soup(response.text)
        anime_data["link"] = link
        anime_data["animego_id"] = link[link.rfind("-") + 1 :]
        anime_data["title"] = (
            soup.find("div", class_="anime-title").find("h1").text.strip()
        )

        anime_data["other_titles"] = [
            syn.text.strip()
            for syn in soup.find("div", class_="anime-synonyms").find_all("li")
        ]

        poster_path = soup.find("img").get("src", "")
        anime_data["poster_url"] = (
            f'{self.client.base_url[:-1]}{poster_path[poster_path.find("/upload"):]}'
            if poster_path
            else ""
        )

        anime_info = soup.find("div", class_="anime-info").find("dl")
        keys = anime_info.find_all("dt")
        values = anime_info.find_all("dd")

        anime_data["other_info"] = {}
        for key, value in zip(keys, values):
            key_text = key.text.strip().replace("  ", " ")
            if value.get("class") == ["mt-2", "col-12"] or value.find("hr"):
                continue
            if key_text == "Озвучка":
                continue
            if key_text == "Жанр":
                anime_data["genres"] = [genre.text for genre in value.find_all("a")]
            elif key_text == "Главные герои":
                anime_data["other_info"]["Главные герои"] = [
                    hero.text for hero in value.find_all("a")
                ]
            elif key_text == "Эпизоды":
                anime_data["episodes"] = value.text
            elif key_text == "Статус":
                anime_data["status"] = value.text
            elif key_text == "Тип":
                anime_data["type"] = value.text
            else:
                anime_data["other_info"][key_text] = value.text.strip()

        anime_data["description"] = soup.find("div", class_="description").text.strip()

        anime_data["screenshots"] = [
            f"{self.client.base_url[:-1]}{screenshot.get('href')}"
            for screenshot in soup.find_all("a", class_="screenshots-item")
        ]

        trailer_container = soup.find("div", class_="video-block")
        anime_data["trailer"] = (
            trailer_container.find("a", class_="video-item").get("href")
            if trailer_container
            else None
        )

        # anime_data["episodes"] = await self.get_episodes(link)

        try:
            anime_data["translations"] = await self.get_translations(
                anime_data["animego_id"]
            )
        except Exception as exc:
            anime_data["translations"] = []

        anime_data["all_titles"] = [anime_data["title"]]
        anime_data["all_titles"] += [anime_data["other_title"]] if "other_title" in anime_data else []
        anime_data["all_titles"] += [anime_data["orig_title"]] if "oring_title" in anime_data else []

        return anime_data
    