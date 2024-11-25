from typing import List, Literal
from json import loads
from base64 import b64decode
from ..classes import Anime, Parser, ParserParams, Exceptions, MPDPlaylist


class KodikAnime(Anime):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser: KodikParser = (
            kwargs["parser"] if "parser" in kwargs else KodikParser()
        )


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
                "Referer": "https://animego.org/",
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
        limit: int = 10,
        id_type: Literal["shikimori", "kinopoisk", "imdb"] = "shikimori",
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

        if isinstance(query, int):
            search_params[f"{id_type}_id"] = query
        else:
            search_params["title"] = query

        response = await self.post("https://kodikapi.com/search", data=search_params)

        if response["total"] == 0:
            raise Exception(f'По запросу "{query}" ничего не найдено')

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
                        "title_orig": result.get("title_orig", None),
                        "other_title": result.get("other_title", None),
                        "type": result.get("type", None),
                        "year": result.get("year", None),
                        "screenshots": result.get("screenshots", None),
                        "shikimori_id": result.get("shikimori_id", None),
                        "kinopoisk_id": result.get("kinopoisk_id", None),
                        "imdb_id": result.get("imdb_id", None),
                        "worldart_link": result.get("worldart_link", None),
                        "link": result.get("link", None),
                    }
                )
                added_titles.add(result["title"])

        for i, result in enumerate(animes):
            animes[i] = await self.convert2anime(**result)

        return animes

    async def get_info(
        self,
        id: str | int,
        id_type: Literal["shikimori", "kinopoisk", "imdb"] = "shikimori",
    ) -> dict:
        id_param_map = {
            "shikimori": "shikimoriID",
            "kinopoisk": "kinopoiskID",
            "imdb": "imdbID",
        }
        if not self.token:
            await self.obtain_token()

        url = f"https://kodikapi.com/get-player?title=Player&hasPlayer=false&url=https%3A%2F%2Fkodikdb.com%2Ffind-player%3F{id_param_map[id_type]}%3D{id}&token={self.token}&{id_param_map[id_type]}={id}"

        data = await self.get(url)

        if "error" in data:
            raise Exception(data["error"])
        if not data["found"]:
            raise Exception(f'No data found for {id_type} id "{id}"')

        link = data["link"]
        response = await self.get(link, text=True, base_url="https:")
        soup = await self.soup(response)

        def _generate_translations_dict(translations_div):
            translations = []
            if translations_div:
                for translation in translations_div:
                    a = {
                        "id": translation["value"],
                        "type": "voice"
                        if translation["data-translation-type"] == "voice"
                        else "subtitles",
                        "name": translation.text,
                    }
                    translations.append(a)
            else:
                translations = [{"id": "0", "type": "unknown", "name": "unknown"}]
            return translations

        is_serial = link[link.find(".info/") + 6] == "s"
        is_video = link[link.find(".info/") + 6] == "v"

        if is_serial:
            series_count = len(
                soup.find("div", {"class": "serial-series-box"})
                .find("select")
                .find_all("option")
            )
            translations_div = (
                soup.find("div", {"class": "serial-translations-box"})
                .find("select")
                .find_all("option")
                if soup.find("div", {"class": "serial-translations-box"})
                else None
            )
        elif is_video:
            series_count = 0
            translations_div = (
                soup.find("div", {"class": "movie-translations-box"})
                .find("select")
                .find_all("option")
                if soup.find("div", {"class": "movie-translations-box"})
                else None
            )
        else:
            raise Exception("Link was not recognized as a link to a serial or video")

        return {
            "series_count": series_count,
            "translations": _generate_translations_dict(translations_div),
        }

    async def _link_to_info(self, vid_id: str, id_type: str, https: bool = True) -> str:
        if id_type == "shikimori":
            serv = f"https://kodikapi.com/get-player?title=Player&hasPlayer=false&url=https%3A%2F%2Fkodikdb.com%2Ffind-player%3FshikimoriID%3D{id}&token={self.token}&{'shikimoriID' if id_type == 'shikimori' else ('kinopoiskID' if id_type == 'kinopoisk' else 'imdbID')}={vid_id}"
        data = await self.get(serv)
        if "error" in data.keys():
            raise Exception(data["error"])
        if not data["found"]:
            raise Exception(f'Нет данных по {id_type} id "{vid_id}"')
        return "https:" + data["link"] if https else "http:" + data["link"]

    def _is_serial(self, iframe_url: str) -> bool:
        return True if iframe_url[iframe_url.find(".info/") + 6] == "s" else False

    def _is_video(self, iframe_url: str) -> bool:
        return True if iframe_url[iframe_url.find(".info/") + 6] == "v" else False

    def _generate_translations_dict(self, translations_div) -> dict:
        if translations_div:
            translations = []
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
        else:
            translations = [{"id": "0", "type": "Неизвестно", "name": "Неизвестно"}]
        return translations

    async def _link_to_info(self, id: str, id_type: str, https: bool = True) -> str:
        if self.token is None:
            await self.obtain_token()
        serv = f"https://kodikapi.com/get-player?title=Player&hasPlayer=false&url=https%3A%2F%2Fkodikdb.com%2Ffind-player%3FshikimoriID%3D{id}&token={self.token}&{'shikimoriID' if id_type == 'shikimori' else ('kinopoiskID' if id_type == 'kinopoisk' else 'imdbID')}={id}"
        data = await self.get(serv)
        if "error" in data.keys() and data["error"] == "Отсутствует или неверный токен":
            raise Exception
        elif "error" in data.keys():
            print(data["error"])
        if not data["found"]:
            raise Exception(f'Нет данных по {id_type} id "{id}"')
        return "https:" + data["link"] if https else "http:" + data["link"]

    async def get_link(
        self, id: str, id_type: str, seria_num: int, translation_id: str
    ) -> tuple[str, int]:
        """
        ### Для использования требуется токен kodik
        Возвращает ссылку на видео файл.

        :id: id медиа
        :id_type: тип id (возможные: shikimori, kinopoisk, imdb)
        :seria_num: номер серии (если фильм или одно видео, укажите 0)
        :translation_id: id перевода (прим: Anilibria = 610, если неизвестно - 0)

        Возвращает ссылку в стиле:
        //cloud.kodik-storage.com/useruploads/351182fc-e1ac-4521-a9e3-261303e69687/ba18e7c1a8ac055a61b0d2e528f9eb8c:2024062702/
        В конце ссылки нужно добавить качество видео: 720.mp4 / 480.mp4 / 360.mp4
        В начале ссылки нужно добавить: http: / https:

        И максимально возможное качество.
        """
        # Проверка переданных параметров на правильность типа
        link = await self._link_to_info(id, id_type)
        data = await self.get(link, text=True)
        soup = await self.soup(data)
        urlParams = data[data.find("urlParams") + 13 :]
        urlParams = loads(urlParams[: urlParams.find(";") - 1])
        if (
            translation_id != "0" and seria_num != 0
        ):  # Обычный сериал с известной озвучкой на более чем 1 серию
            container = soup.find("div", {"class": "serial-translations-box"}).find(
                "select"
            )
            media_hash = None
            media_id = None
            for translation in container.find_all("option"):
                if translation.get_attribute_list("data-id")[0] == translation_id:
                    media_hash = translation.get_attribute_list("data-media-hash")[0]
                    media_id = translation.get_attribute_list("data-media-id")[0]
                    break
            url = f"https://kodik.info/serial/{media_id}/{media_hash}/720p?min_age=16&first_url=false&season=1&episode={seria_num}"
            data = await self.get(url, test=True)
            soup = await self.soup(data)
        elif (
            translation_id != "0" and seria_num == 0
        ):  # Фильм/одна серия с несколькими переводами
            container = soup.find("div", {"class": "movie-translations-box"}).find(
                "select"
            )
            media_hash = None
            media_id = None
            for translation in container.find_all("option"):
                if translation.get_attribute_list("data-id")[0] == translation_id:
                    media_hash = translation.get_attribute_list("data-media-hash")[0]
                    media_id = translation.get_attribute_list("data-media-id")[0]
                    break
            url = f"https://kodik.info/video/{media_id}/{media_hash}/720p?min_age=16&first_url=false&season=1&episode={seria_num}"
            data = await self.get(url, text=True)
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
        download_url = download_url[2:-26]  # :hls:manifest.m3u8

        return download_url, max_quality

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
        print(data)
        url = self._convert(data["links"]["360"][0]["src"])
        max_quality = max([int(x) for x in data["links"].keys()])
        try:
            return b64decode(url.encode()), max_quality
        except:
            return str(b64decode(url.encode() + b"==")).replace(
                "https:", ""
            ), max_quality

    async def _get_post_link(self, script_url: str):
        data = await self.get("https://kodik.info" + script_url, text=True)
        url = data[data.find("$.ajax") + 30 : data.find("cache:!1") - 3]
        return b64decode(url.encode()).decode()

    def _convert(self, string: str):
        return "".join(map(self._convert_char, list(string)))
