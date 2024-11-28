from re import compile, sub
from typing import List
from json import loads
from datetime import datetime
from ..classes import Anime, Parser, ParserParams, Exceptions, MPDPlaylist


class AniboomEpisode(Anime.Episode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser: AniboomParser = (
            kwargs["parser"] if "parser" in kwargs else AniboomParser()
        )

    async def get_video(self, translation_id: int | str = "1") -> MPDPlaylist:
        for video in self.videos:
            if video["translation_id"] == translation_id and video["content"]:
                return video["content"]
        content = await self.parser.get_mpd_content(
            self.anime_id, self.episode_num, translation_id
        )
        result = {"translation_id": translation_id, "content": content}
        if result not in self.videos:
            self.videos.append(result)
        return content

    async def get_videos(self) -> List[dict]:
        for translation in self.translations if self.translations else (await self.parser.get_translations(self.anime_id)):
            try:
                await self.get_video(translation_id=translation["translation_id"])
            except Exception as exc:
                print(exc)
        return self.videos


class AniboomAnime(Anime):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser: AniboomParser = (
            kwargs["parser"] if "parser" in kwargs else AniboomParser()
        )

    async def get_episodes(self) -> List[AniboomEpisode]:
        if self.episodes:
            return self.episodes
        self.episodes: List[AniboomEpisode] = await self.parser.get_episodes(self.url)
        self.total_episodes = int(self.episodes[-1].get("episode_num", 0)) or len(self.episodes)
        return self.episodes

    async def get_translations(self) -> dict:
        if self.translations and len(self.translations) > 0:
            return self.translations
        self.translations = await self.parser.get_translations(self.anime_id)
        return self.translations

    async def get_info(self) -> dict:
        self.data = await self.parser.get_info(self.url)
        self.episodes = self.data.get("episodes", [])
        self.translations = self.data["translations"]
        self.status = (
            Anime.Status.COMPLETED
            if self.data.get("status", "") == "Вышел"
            else (
                Anime.Status.ONGOING
                if "/" in self.data.get("status", "")
                else Anime.Status.UNKNOWN
            )
        )
        self.type = (
            Anime.Type.TV
            if self.data.get("type", "") == "ТВ Сериал"
            else (
                Anime.Type.MOVIE
                if self.data.get("type", "") == "Фильм"
                else (
                    Anime.Type.OVA
                    if self.data.get("type", "") == "OVA"
                    else (
                        Anime.Type.SPECIAL
                        if self.data.get("type", "") == "Спешл"
                        else (Anime.Type.UNKNOWN)
                    )
                )
            )
        )
        return self.data

    async def get_video(
        self, episode: int | str, translation_id: int | str
    ) -> MPDPlaylist:
        return await self.parser.get_mpd_content(self.anime_id, episode, translation_id)

    async def get_videos(self) -> List[dict]:
        """
        Get all videos for all episodes.
        Very long process, can take a while. Probably shouldn't be used on prod

        Returns:
            List[dict]: List of videos for each episode
        """
        for episode in self.episodes if self.episodes else await self.get_episodes():
            try:
                await episode.get_videos()
            except Exception:
                continue
        return [episode.videos for episode in self.episodes]

    async def get_shikimori_id(self, url: str = None) -> str | None:
        response = await self.parser.get(
            "https://raw.githubusercontent.com/nichind/anime-chains/refs/heads/main/json/shikimori2animego.json"
        )
        data = loads(response)
        for shikimori_id, _url in data.items():
            if _url.strip() == (self.url if not url else url).strip():
                return shikimori_id


class AniboomParser(Parser):
    def __init__(self, params: ParserParams = None, **kwargs):
        """
        Aniboom (animego.org) Parser

        [!] This parser parser videos from animego.org with aniboom as a player, not all players avaliable on the site, if you want to parse different players, use AnimegoParser instead.

        Args:
            **kwargs: Additional keyword arguments to pass to the parent Parser class.

        Original code reference: https://github.com/YaNesyTortiK/AnimeParsers
        """
        self.params = ParserParams(
            base_url="https://animego.org/",
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://animego.org/",
            },
            language="ru",
        )
        if params:
            self.params = params
        super().__init__(self.params, **kwargs)

    async def convert2anime(self, **kwargs) -> AniboomAnime:
        anime = AniboomAnime(
            orig_title=kwargs["other_title"],
            title=kwargs["title"],
            anime_id=kwargs["id"],
            url=kwargs["link"],
            parser=self,
            id_type="animego",
            language=self.language,
            data=kwargs["data"],
        )
        return anime

    async def search(self, query: str) -> List[AniboomAnime]:
        """
        Search anime on Aniboom (animego.org).

        Args:
            query (str): Anime title to search for.

        Returns:
            List[AniboomAnime]: List of matching anime.
        """
        content = (await self.get("search/all", params={"type": "small", "q": query}))[
            "content"
        ]

        page = await self.soup(content)
        try:
            results_list = page.find("div", {"class": "result-search-anime"}).find_all(
                "div", {"class": "result-search-item"}
            )
        except AttributeError:
            return []

        results = []
        for result in results_list:
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
                "a", {"href": compile(r".*anime/type.*")}
            ).text.strip()
            data["link"] = (
                self.base_url[:-1] + result.find("h5").find("a").attrs["href"]
            )
            data["id"] = data["link"][data["link"].rfind("-") + 1 :]
            data["data"]["year"] = result.find(
                "span", {"class": "anime-year"}
            ).text.strip()
            results.append(await self.convert2anime(**data))

        return results

    async def get_episodes(self, link: str) -> List[AniboomEpisode]:
        """
        Fetches and parses anime episodes from a given link.

        Args:
            link (str): The URL of the anime page to retrieve episodes from.

        Returns:
            List[dict]: A list of dictionaries containing various details about each episode,
                including:
                    num (str): The episode number.
                    title (str): The episode title.
                    date (str): The episode's release date.
                    status (str): The episode's status, either "анонс" or "вышел".
        """
        params = {"type": "episodeSchedule", "episodeNumber": "9999"}
        response = await self.get(link, params=params)
        soup = await self.soup(response["content"])
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
                print(exc)
                episodes[i]["date"] = None
            episodes[i] = AniboomEpisode(
                episode_num=ep["num"],
                title=ep["title"],
                status=Anime.Episode.Status.RELEASED
                if ep["status"] == "вышел"
                else (
                    Anime.Episode.Status.ANNOUNCED
                    if ep["status"] == "анонс"
                    else Anime.Episode.Status.UNKNOWN
                ),
                date=ep["date"],
                anime_id=sub(r"\D", "", link[link.rfind("-") + 1 :]),
                anime_url=link,
                episode_id=ep["episode_id"],
            )
        if not episodes:
            episodes = [
                AniboomEpisode(
                    episode_num="0",
                    status=Anime.Episode.Status.UNKNOWN,
                    anime_id=sub(r"\D", "", link[link.rfind("-") + 1 :]),
                    anime_url=link,
                )
            ]
        return episodes

    async def get_info(self, link: str) -> dict:
        """
        Fetches and parses anime information from a given link.

        Args:
            link (str): The URL of the anime page to retrieve information from.

        Returns:
            dict: A dictionary containing various details about the anime, including:
                - link (str): The URL of the anime page.
                - animego_id (str): The ID of the anime extracted from the link.
                - title (str): The main title of the anime.
                - other_titles (list of str): A list of alternative titles.
                - poster_url (str): URL to the anime's poster image.
                - genres (list of str): A list of genres associated with the anime.
                - episodes (str): Information about the episodes.
                - status (str): Current status of the anime (e.g., ongoing, completed).
                - type (str): Type of the anime (e.g., TV, movie).
                - description (str): A brief description of the anime.
                - screenshots (list of str): URLs of screenshot images.
                - trailer (str or None): URL to the anime's trailer, if available.
                - translations (list): List of available translations.
                - other_info (dict): Additional information about the anime, such as main characters.
        """
        anime_data = {}
        response = await self.get(link)
        soup = await self.soup(response)
        
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
            f'{self.base_url[:-1]}{poster_path[poster_path.find("/upload"):]}'
            if poster_path
            else ""
        )

        anime_info = soup.find("div", class_="anime-info").find("dl")
        keys = anime_info.find_all("dt")
        values = anime_info.find_all("dd")

        anime_data["other_info"] = {}
        for key, value in zip(keys, values):
            key_text = key.text.strip()
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
            f"{self.base_url[:-1]}{screenshot.get('href')}"
            for screenshot in soup.find_all("a", class_="screenshots-item")
        ]

        trailer_container = soup.find("div", class_="video-block")
        anime_data["trailer"] = (
            trailer_container.find("a", class_="video-item").get("href")
            if trailer_container
            else None
        )

        anime_data["episodes"] = await self.get_episodes(link)

        try:
            anime_data["translations"] = await self.get_translations(
                anime_data["animego_id"]
            )
        except Exception as e:
            print(e)
            anime_data["translations"] = []

        return anime_data

    async def get_translations(self, animego_id: int | str) -> dict:
        """
        Get translations for animego_id.

        Args:
        animego_id: str or int, animego id of anime.

        Returns:
        dict: translations with names and translation ids.
        """
        params = {
            "_allow": "true",
        }
        response = await self.get(f"anime/{animego_id}/player", params=params)
        soup = await self.soup(response["content"])

        if soup.find("div", {"class": "player-blocked"}):
            reason_elem = soup.find("div", {"class": "h5"})
            reason = reason_elem.text if reason_elem else None
            raise Exceptions.PlayerBlocked(f"Player is blocked: {reason}")

        try:
            translations_elem = soup.find("div", {"id": "video-dubbing"}).find_all(
                "span", {"class": "video-player-toggle-item"}
            )
            translations = {}
            for translation in translations_elem:
                dubbing = translation.get_attribute_list("data-dubbing")[0]
                name = translation.text.strip()
                translations[dubbing] = {"name": name}

            players_elem = soup.find("div", {"id": "video-players"}).find_all(
                "span", {"class": "video-player-toggle-item"}
            )
            for player in players_elem:
                if player.get_attribute_list("data-provider")[0] == "24":
                    dubbing = player.get_attribute_list("data-provide-dubbing")[0]
                    translation_id = player.get_attribute_list("data-player")[0]
                    translation_id = translation_id[translation_id.rfind("=") + 1 :]
                    translations[dubbing]["translation_id"] = translation_id

            filtered_translations = []
            for translation in translations.values():
                if "translation_id" in translation:
                    filtered_translations.append(translation)

        except Exception as e:
            print(e)
            filtered_translations = []

        return filtered_translations

    async def get_embed_link(self, animego_id: int | str) -> str:
        params = {"_allow": "true"}
        headers = {"X-Requested-With": "XMLHttpRequest"}
        response = await self.get(
            f"anime/{animego_id}/player", params=params, headers=headers
        )
        if response["status"] != "success":
            raise Exception(f'Unexpected status: {response["status"]}')
        soup = await self.soup(response["content"])
        if soup.find("div", {"class": "player-blocked"}):
            reason = soup.find("div", {"class": "h5"}).text
            raise Exceptions.PlayerBlocked(f"Content is blocked: {reason}")
        player_container = soup.find("div", {"id": "video-players"})
        player_link = player_container.find(
            "span", {"class": "video-player-toggle-item"}
        ).get_attribute_list("data-player")[0]
        return "https:" + player_link[: player_link.rfind("?")]

    async def get_embed(self, embed_link: str, episode: int, translation: str) -> str:
        if episode != 0:
            params = {
                "episode": str(episode),
                "translation": str(translation),
            }
        else:
            params = {
                "translation": str(translation),
            }
        try:
            return await self.get(embed_link, params=params, text=True)
        except Exceptions.PageNotFound:
            if str(episode) == "0":
                params["episode"] = "1"
            else:
                params[episode] = "0"
            return await self.get(embed_link, params=params, text=True)

    async def get_mpd_playlist(
        self, embed_link: str, episode: int, translation_id: str
    ) -> MPDPlaylist:
        embed = await self.get_embed(embed_link, episode, translation_id)
        soup = await self.soup(embed)
        data = loads(soup.find("div", {"id": "video"}).get("data-parameters"))
        media_src = loads(data["dash"])["src"]

        headers = {
            "Origin": "https://aniboom.one",
            "Referer": "https://aniboom.one/",
        }

        playlist = await self.get(media_src, headers=headers, text=True)

        filename = media_src[media_src.rfind("/") + 1 : media_src.rfind(".")]
        server_path = media_src[: media_src.rfind(".")]
        playlist = playlist.replace(filename, server_path)

        return MPDPlaylist(media_src, playlist)

    async def get_mpd_content(
        self, animego_id: int | str, episode: int, translation_id: int
    ) -> MPDPlaylist:
        """
        Retrieves the MPD playlist file content for a given anime episode and translation.

        Args:
            animego_id (int | str): The unique identifier of the anime.
            episode (int): The episode number of the anime.
            translation_id (int): The translation identifier for the episode.

        Returns:
            MPDPlaylist: The MPD playlist containing the DASH streaming content for the specified episode and translation.
        """
        embed_link = await self.get_embed_link(animego_id)
        return await self.get_mpd_playlist(embed_link, episode, translation_id)
