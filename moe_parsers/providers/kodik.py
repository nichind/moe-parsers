from typing import List, Literal
from json import loads
from base64 import b64decode
from ..classes import Anime, Parser, ParserParams, Exceptions, M3U8Playlist


class KodikVideo:
    def __init__(self, **kwargs):
        """
        Kodik player cloud video, file access is temporary, should be used only for downloading or otherwise be ready for 403 (Forbidden)
        """
        self.cloud_url: str = kwargs["cloud_url"] if "cloud_url" in kwargs else None
        self.max_quality: int = (
            kwargs["max_quality"] if "max_quality" in kwargs else None
        )
        self.iframe: str = kwargs["iframe"] if "iframe" in kwargs else None
        self.episode_num: int = (
            kwargs["episode_num"] if "episode_num" in kwargs else None
        )
        self.translation_id: int = (
            kwargs["translation_id"] if "translation_id" in kwargs else None
        )
        self.parser: KodikParser = (
            kwargs["parser"] if "parser" in kwargs else KodikParser()
        )

    async def get_m3u8(self) -> str:
        return await self.parser.get_m3u8(self.cloud_url)


class KodikEpisode(Anime.Episode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser: KodikParser = (
            kwargs["parser"] if "parser" in kwargs else KodikParser()
        )


class KodikAnime(Anime):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser: KodikParser = (
            kwargs["parser"] if "parser" in kwargs else KodikParser()
        )

    async def get_info(self) -> dict:
        return await self.parser.get_info(self.anime_id, self.id_type)

    async def get_videos(self) -> List[KodikVideo]:
        pass


class KodikParser(Parser):
    def __init__(self, **kwargs):
        """
        Kodik Parser

        Args:
            **kwargs: Additional keyword arguments to pass to the parent Parser class.

        Original code reference: https://github.com/YaNesyTortiK/AnimeParsers
        """
        self.params = ParserParams(
            base_url="https://kodik.info/",
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
            },
            language="ru",
        )
        self.token = None
        super().__init__(self.params, **kwargs)

    async def convert2anime(self, **kwargs) -> KodikAnime:
        anime = KodikAnime(
            orig_title=kwargs["title_orig"],
            title=kwargs["title"],
            anime_id=kwargs["shikimori_id"],
            url="https:" + kwargs["link"],
            parser=self,
            id_type="shikimori",
            language=self.language,
            data=kwargs,
        )
        return anime

    async def obtain_token(self) -> str:
        script_url = "https://kodik-add.com/add-players.min.js?v=2"
        data = await self.get(script_url, text=True)
        token = data[data.find("token=") + 7 :]
        token = token[: token.find('"')]
        self.token = token
        return token

    async def search(
        self,
        query: str | int,
        limit: int = 25,
        id_type: Literal["shikimori", "kinopoisk", "imdb"] = None,
        strict: bool = False,
    ) -> List[KodikAnime]:
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

        response = await self.post("https://kodikapi.com/search", data=search_params)

        if not response["total"]:
            return []

        results = response["results"]
        animes = []
        added_titles = set()

        for result in results:
            if result["type"] not in ["anime-serial", "anime"]:
                continue

            if result["title"] not in added_titles:
                animes.append(
                    {
                        "id": result["id"],
                        "title": result["title"],
                        "title_orig": result.get("title_orig"),
                        "other_title": result.get("other_title"),
                        "type": result.get("type"),
                        "year": result.get("year"),
                        "screenshots": result.get("screenshots"),
                        "shikimori_id": result.get("shikimori_id"),
                        "kinopoisk_id": result.get("kinopoisk_id"),
                        "imdb_id": result.get("imdb_id"),
                        "worldart_link": result.get("worldart_link"),
                        "link": result.get("link"),
                    }
                )
                added_titles.add(result["title"])

        for i, result in enumerate(animes):
            animes[i] = await self.convert2anime(**result)

        return animes

    async def translations(self, anime_id: str, id_type: str) -> list:
        data = await self.get_info(anime_id, id_type)
        return data["translations"]

    async def series_count(self, anime_id: str, id_type: str) -> int:
        data = await self.get_info(anime_id, id_type)
        return data["series_count"]

    async def _link_to_info(
        self,
        anime_id: str,
        id_type: Literal["shikimori", "kinopoisk", "imdb"] = "shikimori",
    ) -> str:
        if id_type == "shikimori":
            url = f"https://kodikapi.com/get-player?title=Player&hasPlayer=false&url=https%3A%2F%2Fkodikdb.com%2Ffind-player%3FshikimoriID%3D{anime_id}&token={self.token}&shikimoriID={anime_id}"
        elif id_type == "kinopoisk":
            url = f"https://kodikapi.com/get-player?title=Player&hasPlayer=false&url=https%3A%2F%2Fkodikdb.com%2Ffind-player%3FkinopoiskID%3D{anime_id}&token={self.token}&kinopoiskID={anime_id}"
        elif id_type == "imdb":
            url = f"https://kodikapi.com/get-player?title=Player&hasPlayer=false&url=https%3A%2F%2Fkodikdb.com%2Ffind-player%3FkinopoiskID%3D{anime_id}&token={self.token}&imdbID={anime_id}"
        data = await self.get(url)
        if "error" in data.keys() and data["error"] == "Отсутствует или неверный токен":
            raise Exceptions.PlayerBlocked("Отсутствует или неверный токен")
        elif "error" in data.keys():
            raise Exceptions.PlayerBlocked(data["error"])
        if not data["found"]:
            raise Exceptions.PlayerBlocked(f'Нет данных по {id_type} id "{id}"')
        return "https:" + data["link"]

    async def get_info(self, anime_id: str, id_type: str) -> dict:
        link = await self._link_to_info(anime_id, id_type)
        data = await self.get(link, text=True)
        soup = await self.soup(data)
        if self._is_serial(link):
            series_count = len(
                soup.find("div", {"class": "serial-series-box"})
                .find("select")
                .find_all("option")
            )
            try:
                translations_div = (
                    soup.find("div", {"class": "serial-translations-box"})
                    .find("select")
                    .find_all("option")
                )
            except AttributeError:
                translations_div = None
            return {
                "series_count": series_count,
                "translations": self._generate_translations_dict(translations_div),
            }
        elif self._is_video(link):
            series_count = 0
            try:
                translations_div = (
                    soup.find("div", {"class": "movie-translations-box"})
                    .find("select")
                    .find_all("option")
                )
            except AttributeError:
                translations_div = None
            return {
                "series_count": series_count,
                "translations": self._generate_translations_dict(translations_div),
            }
        else:
            raise Exceptions.PageNotFound(
                "Ссылка на данные не была распознана как ссылка на сериал или фильм"
            )

    def _is_serial(self, iframe_url: str) -> bool:
        return True if iframe_url[iframe_url.find(".info/") + 6] == "s" else False

    def _is_video(self, iframe_url: str) -> bool:
        return True if iframe_url[iframe_url.find(".info/") + 6] == "v" else False

    def _generate_translations_dict(self, translations_div) -> dict:
        translations = []
        if not translations_div:
            return [{"id": "0", "type": "Неизвестно", "name": "Неизвестно"}]
        for translation in translations_div:
            a = {}
            a["id"] = translation["value"]
            a["type"] = translation["data-translation-type"]
            if a["type"] == "voice":
                a["type"] = "Озвучка"
            elif a["type"] == "subtitles":
                a["type"] = "Субтитры"
            a["name"] = translation.text
            translations.append(a)
        if not translations:
            translations = [{"id": "0", "type": "Неизвестно", "name": "Неизвестно"}]
        return translations

    async def get_iframe(
        self,
        anime_id: str | int,
        id_type: Literal["shikimori", "kinopoisk", "imdb"],
        episode_num: int = None,
        translation_id: str | int = "0",
    ) -> tuple[str, int]:
        link = await self._link_to_info(anime_id, id_type)
        data = await self.get(link, text=True)
        soup = await self.soup(data)
        container = soup.find("div", {"class": "serial-translations-box"}).find(
            "select"
        )
        media_hash = None
        media_id = None
        for translation in container.find_all("option"):
            if (
                str(translation.get_attribute_list("data-id")[0]) == str(translation_id)
                or translation_id == "0"
            ):
                media_hash = translation.get_attribute_list("data-media-hash")[0]
                media_id = translation.get_attribute_list("data-media-id")[0]
                break
        url = f"https://kodik.info/serial/{media_id}/{media_hash}/720p?min_age=16&first_url=false&season=1&episode={episode_num}"
        return url

    async def get_video(
        self,
        anime_id: str | int,
        id_type: Literal["shikimori", "kinopoisk", "imdb"],
        episode_num: int = None,
        translation_id: str | int = "0",
    ) -> KodikVideo:
        link = await self._link_to_info(anime_id, id_type)
        data = await self.get(link, text=True)
        urlParams = data[data.find("urlParams") + 13 :]
        urlParams = loads(urlParams[: urlParams.find(";") - 1])
        iframe = await self.get_iframe(anime_id, id_type, episode_num, translation_id)
        data = await self.get(iframe, text=True)
        soup = await self.soup(data)
        script_url = soup.find_all("script")[1].get_attribute_list("src")[0]

        hash_container = soup.find_all("script")[4].text
        video_type = hash_container[hash_container.find(".type = '") + 9 :]
        video_type = video_type[: video_type.find("'")]
        video_hash = hash_container[hash_container.find(".hash = '") + 9 :]
        video_hash = video_hash[: video_hash.find("'")]
        video_id = hash_container[hash_container.find(".id = '") + 7 :]
        video_id = video_id[: video_id.find("'")]
        link_data, max_quality = await self._get_link_with_data(
            video_type, video_hash, video_id, urlParams, script_url
        )
        download_url = str(link_data).replace("https://", "")
        return KodikVideo(
            cloud_url="https:" + download_url[2:-26],
            max_quality=max_quality,
            iframe=iframe,
            episode_num=episode_num,
            translation_id=translation_id,
            parser=self,
        )

    async def _get_link_with_data(
        self,
        video_type: str,
        video_hash: str,
        video_id: str,
        urlParams: dict,
        script_url: str,
    ):
        params = {
            "hash": video_hash,
            "id": video_id,
            "type": video_type,
            "d": urlParams["d"],
            "d_sign": urlParams["d_sign"],
            "pd": urlParams["pd"],
            "pd_sign": urlParams["pd_sign"],
            "ref": "",
            "ref_sign": urlParams["ref_sign"],
            "bad_user": "true",
            "cdn_is_working": "true",
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        post_link = await self._get_post_link(script_url)
        data = await self.post(
            f"https://kodik.info{post_link}", data=params, headers=headers
        )
        url = self._convert(data["links"]["360"][0]["src"])
        max_quality = max([int(x) for x in data["links"].keys()])
        try:
            return b64decode(url.encode()), max_quality
        except Exception:
            return str(b64decode(url.encode() + b"==")).replace(
                "https:", ""
            ), max_quality

    def _convert_char(self, char: str):
        low = char.islower()
        alph = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if char.upper() in alph:
            ch = alph[(alph.index(char.upper()) + 13) % len(alph)]
            if low:
                return ch.lower()
            else:
                return ch
        else:
            return char

    def _convert(self, string: str):
        return "".join(map(self._convert_char, list(string)))

    async def _get_post_link(self, script_url: str):
        data = await self.get("https://kodik.info" + script_url, text=True)
        url = data[data.find("$.ajax") + 30 : data.find("cache:!1") - 3]
        return b64decode(url.encode()).decode()

    async def get_m3u8(self, cloud_url: str) -> M3U8Playlist:
        page_content = await self.get(cloud_url, text=True)
        for quality in ["720", "480", "360"]:
            if f"{quality}.mp4" in page_content:
                playlist_content = await self.get(
                    f"{cloud_url}{quality}.mp4:hls:manifest.m3u8", text=True
                )
                break
        else:
            raise ValueError("No valid quality found in page content.")

        for quality in ["720", "480", "360"]:
            if f"{quality}.mp4" in playlist_content:
                filename = f"./{quality}.mp4:hls"
                playlist_content = playlist_content.replace(
                    filename, filename.replace("./", cloud_url)
                )
                break

        return M3U8Playlist(cloud_url, playlist_content)
