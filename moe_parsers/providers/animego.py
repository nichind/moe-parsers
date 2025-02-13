from ..parser import Parser
from ..items import _BaseItem, Anime
from typing import Unpack, AsyncGenerator, List
from datetime import datetime


class AnimegoParser(Parser):
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
        "января": "1",
        "февраля": "2",
        "марта": "3",
        "апреля": "4",
        "августа": "8",
        "сентября": "9",
        "октября": "10",
        "ноября": "11",
        "декабря": "12",
    }

    @classmethod
    def string2datetime(cls, string) -> datetime:
        return datetime.strptime(
            " ".join(
                [
                    x if x not in cls.replace_month else cls.replace_month[x]
                    for x in string.split()
                ]
            ),
            "%d %m %Y",
        )

    async def search(self, q: str) -> List[_BaseItem]:
        results = []
        async for result in self.search_generator(q):
            results.append(result)
        return results

    async def search_generator(self, query: str) -> AsyncGenerator[_BaseItem, None]:
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
                data["thumbnail"] = (
                    thumbnail.get("data-original", None) if thumbnail else None
                )
                self.client.replace_headers(
                    {
                        "Cookie": response.headers["Set-Cookie"],
                    }
                )
                yield data
            except AttributeError:
                continue

    async def get_info(self, url: str) -> dict:
        anime_data = {}
        response = await self.client.get(url)
        soup = self.client.soup(response.text)

        with open("test.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())

        anime_data["url"] = url
        anime_data["animego_id"] = int(url[url.rfind("-") + 1 :])
        anime_data["title"] = (
            soup.find("div", class_="anime-title").find("h1").text.strip()
        )

        # Описание
        description_block = soup.find("div", class_="description")
        anime_data["description"] = (
            description_block.text.strip() if description_block else None
        )

        # Жанры
        genres = soup.select("dd.overflow-h a")
        anime_data["genres"] = [genre.text.strip() for genre in genres]

        # Оценка и количество голосов
        rating_block = soup.find("span", class_="rating-value")
        anime_data["rating"] = (
            float(rating_block.text.strip().replace(",", ".")) if rating_block else None
        )
        rating_count_block = soup.find("div", class_="rating-count")
        anime_data["rating_count"] = (
            int(rating_count_block.text.strip()) if rating_count_block else None
        )

        # Дата выхода
        release_date_block = soup.find("span", {"data-label": True})
        anime_data["release_date"] = (
            release_date_block.text.strip()
            if release_date_block
            else None
        )

        if anime_data["release_date"]:
            if "по" not in anime_data["release_date"]:
                anime_data["started"] = self.string2datetime(
                    anime_data["release_date"].replace("с ", "")
                )
                anime_data["completed"] = (
                    anime_data["started"]
                    if "с " not in anime_data["release_date"]
                    else None
                )
            else:
                anime_data["started"] = self.string2datetime(
                    anime_data["release_date"]
                    .split(" по ")[0]
                    .replace("с ", "")
                    .strip()
                )
                anime_data["completed"] = self.string2datetime(
                    anime_data["release_date"].split(" по ")[1].strip()
                )
        else:
            anime_data["started"], anime_data["completed"] = None, None

        # Длительность
        duration_block = soup.find("dt", string="Длительность")
        if duration_block:
            duration_string = duration_block.find_next_sibling("dd").text.strip()
            try:
                if " ч. " in duration_string:
                    hours, minutes = duration_string.split(" ч. ")
                    hours = int(hours)
                    minutes = (
                        int(minutes.split(" мин.")[0]) if " мин." in minutes else 0
                    )
                    anime_data["episode_duration"] = (hours * 60 + minutes) * 60
                elif " мин." in duration_string:
                    minutes = int(duration_string.split(" мин.")[0])
                    anime_data["episode_duration"] = minutes * 60
                else:
                    anime_data["episode_duration"] = None
            except ValueError:
                anime_data["episode_duration"] = None

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
            seiyuu_tag = char.find_next("span").find_next("span")
            try:
                seiyuu_name = (
                    seiyuu_tag.find("span").text.strip() if seiyuu_tag else None
                )
            except AttributeError:
                seiyuu_name = None
            anime_data["characters"].append({"name": char_name, "seiyuu": seiyuu_name})

        # Картинка
        image_block = soup.find("meta", property="og:image")
        anime_data["image"] = image_block["content"] if image_block else None

        # Трейлер
        trailer_block = soup.select_one("div.video-block a")
        anime_data["trailer"] = trailer_block["href"] if trailer_block else None

        # Кадры
        screenshots = soup.select("div.screenshots-block a img")
        anime_data["screenshots"] = [img["src"] for img in screenshots]

        # Тип
        type_block = soup.find("dt", string="Тип")
        if type_block:
            _type = type_block.find_next_sibling("dd").text.strip()
            anime_data["type"] = (
                Anime.Type.MOVIE
                if _type == "Фильм"
                else (
                    Anime.Type.TV
                    if _type == "ТВ Сериал"
                    else (
                        Anime.Type.OVA
                        if _type == "OVA"
                        else (Anime.Type.ONA if _type == "ONA" else Anime.Type.UNKNOWN)
                    )
                )
            )

        # График выхода серий
        anime_data["episodes"] = await self.get_episodes(url)
        if not anime_data["episodes"] and anime_data["type"] in [Anime.Type.MOVIE]:
            anime_data["episodes"] = [
                Anime.Episode(
                    number="1",
                    title=anime_data["title"],
                    aired=anime_data["completed"],
                    status=Anime.Episode.EpisodeStatus.RELEASED,
                )
            ]

        anime_data["status"] = (
            Anime.Status.COMPLETED if anime_data["completed"] else (Anime.Status.ONGOING if anime_data["started"] else Anime.Status.UNKNOWN)
        )

        anime_data["ids"] = {}
        anime_data["ids"][Anime.IDType.ANIMEGO] = anime_data["animego_id"]
        anime = Anime(**anime_data)

        return anime_data

    async def get_episodes(self, url: str) -> List[Anime.Episode]:
        params = {"type": "episodeSchedule", "episodeNumber": "0"}
        response = await self.client.get(url, params=params)
        soup = self.client.soup(response.json.get("content"))
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
                Anime.Episode(
                    number=num,
                    title=ep_title,
                    aired=ep_date,
                    status=Anime.Episode.EpisodeStatus.ANNOUNCED
                    if ep_status == "анонс"
                    else (
                        Anime.Episode.EpisodeStatus.RELEASED
                        if ep_status == "вышел"
                        else Anime.Episode.EpisodeStatus.UNKNOWN
                    ),
                    id=int(ep_id) if not ep_status == "анонс" else None,
                )
            )

        episodes = sorted(
            episodes_list,
            key=lambda x: int(x.number) if x.number.isdigit() else x.number,
        )
        for i, ep in enumerate(episodes):
            try:
                if ep.aired:
                    episodes[i].aired = self.string2datetime(episodes[i].aired)
            except ValueError:
                episodes[i].aired = None
        return episodes
