from ..parser import Parser
from ..items import _BaseItem, Anime
from typing import Unpack, AsyncGenerator
from datetime import datetime


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
        self.client.replace_headers(
            {
                "accept": "application/json, text/javascript, */*; q=0.01",
                "cookie": self.client.headers.get("cookie", ""),
                "referer": "https://animego.org/",
                "x-requested-with": "XMLHttpRequest",
            }
        )
        response = await self.client.get(link + "")
        with open("test.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        soup = self.client.soup(response.text)

        # Основная информация
        anime_data["link"] = link
        anime_data["animego_id"] = link[link.rfind("-") + 1 :]
        anime_data["title"] = (
            soup.find("div", class_="anime-title").find("h1").text.strip()
        )

        # Описание
        description_block = soup.find("div", class_="description")
        anime_data["description"] = (
            description_block.text.strip()
            if description_block
            else "Описание не найдено"
        )

        # Жанры
        genres = soup.select("dd.overflow-h a")
        anime_data["genres"] = [genre.text.strip() for genre in genres]

        # Оценка и количество голосов
        rating_block = soup.find("span", class_="rating-value")
        anime_data["rating"] = (
            rating_block.text.strip() if rating_block else "Нет рейтинга"
        )

        rating_count_block = soup.find("div", class_="rating-count")
        anime_data["rating_count"] = (
            rating_count_block.text.strip() if rating_count_block else "0"
        )

        # Дата выхода
        release_date_block = soup.find("span", {"data-label": True})
        anime_data["release_date"] = (
            release_date_block.text.strip()
            if release_date_block
            else "Дата выхода не найдена"
        )

        # Длительность
        duration_block = soup.find("dt", string="Длительность")
        if duration_block:
            anime_data["duration"] = duration_block.find_next_sibling("dd").text.strip()

        # Студия
        studio_block = soup.find("dt", string="Студия")
        if studio_block:
            anime_data["studio"] = studio_block.find_next_sibling("dd").text.strip()

        # MPAA рейтинг
        mpaa_block = soup.find("dt", string="Рейтинг MPAA")
        if mpaa_block:
            anime_data["mpaa"] = mpaa_block.find_next_sibling("dd").text.strip()

        # Возрастной рейтинг
        age_block = soup.find("dt", string="Возрастные ограничения")
        if age_block:
            anime_data["age_rating"] = age_block.find_next_sibling("dd").text.strip()

        # Озвучка
        dubbing_block = soup.find("dt", string="Озвучка")
        if dubbing_block:
            dubbing_list = dubbing_block.find_next_sibling("dd").find_all("a")
            anime_data["dubbing"] = [dubbing.text.strip() for dubbing in dubbing_list]

        # Главные герои
        anime_data["characters"] = []
        character_blocks = soup.select("dd a[href*='/character/']")
        for char in character_blocks:
            char_name = char.text.strip()
            seiyuu_tag = char.find_next("a", class_="text-link-gray text-underline")
            seiyuu_name = seiyuu_tag.text.strip() if seiyuu_tag else "Неизвестно"

            anime_data["characters"].append({"name": char_name, "seiyuu": seiyuu_name})

        # Картинка
        image_block = soup.find("meta", property="og:image")
        anime_data["image"] = (
            image_block["content"] if image_block else "Нет изображения"
        )

        # Трейлер
        trailer_block = soup.select_one("div.video-block a")
        anime_data["trailer"] = (
            trailer_block["href"] if trailer_block else "Нет трейлера"
        )

        # Кадры
        screenshots = soup.select("div.screenshots-block a img")
        anime_data["screenshots"] = [img["src"] for img in screenshots]

        # График выхода серий
        soup = self.client.soup(
            (
                await self.client.get(
                    link, params={"type": "episodeSchedule", "episodeNumber": "9999"}
                )
            ).text
        )
        episodes_list = []
        for ep in soup.find_all("div", {"class": ["row", "m-0"]}):
            items = ep.find_all("div")
            num = items[0].find("meta").get_attribute_list("content")[0]
            ep_title = items[1].text.strip() if items[1].text else ""
            ep_date = (
                items[2].find("span").get_attribute_list("data-label")[0]
                if items[2].find("span")
                else ""
            )
            ep_id = (
                items[3].find("span").get_attribute_list("data-watched-id")[0]
                if items[3].find("span")
                else None
            )
            ep_status = "анонс" if items[3].find("span") is None else "вышел"
            episodes_list.append(
                {
                    "num": num,
                    "title": ep_title,
                    "date": ep_date,
                    "status": ep_status,
                    "episode_id": ep_id,
                }
            )

        episodes = sorted(
            episodes_list,
            key=lambda x: int(x["num"]) if x["num"].isdigit() else x["num"],
        )
        for i, ep in enumerate(episodes):
            try:
                if ep["date"]:
                    replace_month = {
                        "янв.": "1",
                        "февр.": "2",
                        "мар.": "3",
                        "апр.": "4",
                        "мая": "5",
                        "июня": "6",
                        "июля": "7",
                        "авг.": "8",
                        "сент.": "9",
                        "окт.": "10",
                        "нояб.": "11",
                        "дек.": "12",
                        "июл.": "7",
                        "июн.": "6",
                    }
                    episodes[i]["date"] = datetime.strptime(
                        " ".join(
                            [
                                x if x not in replace_month else replace_month[x]
                                for x in episodes[i]["date"].split()
                            ]
                        ),
                        "%d %m %Y",
                    )
            except ValueError as exc:
                episodes[i]["date"] = None
        anime_data["episodes"] = episodes
        return anime_data
