from typing import List, Literal
from json import loads
from base64 import b64decode
from ..classes import Anime, Parser, ParserParams, Exceptions, Media


class TempKodikVideo(Media):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser: KodikParser = (
            kwargs["parser"] if "parser" in kwargs else KodikParser()
        )


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

        if not response["total"]:
            raise Exceptions.NothingFound(f'По запросу "{query}" ничего не найдено')

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

    async def translations(self, id: str, id_type: str) -> list:
        data = await self.get_info(id, id_type)
        return data['translations']
    
    async def series_count(self, id: str, id_type: str) -> int:
        data = await self.get_info(id, id_type)
        return data['series_count']

    async def _link_to_info(self, anime_id: str, id_type: Literal["shikimori", "kinopoisk", "imdb"] = "shikimori") -> str:
        data = await self.get(f"https://kodikapi.com/get-player?title=Player&hasPlayer=false&url=https%3A%2F%2Fkodikdb.com%2Ffind-player%3FkinopoiskID%3D{anime_id}&token={self.token}&{'imdbID' if id_type == 'imdb' else ('kinopoiskID' if id_type == 'kinopoisk' else 'shikimoriID')}={anime_id}")
        if 'error' in data.keys() and data['error'] == 'Отсутствует или неверный токен':
            raise Exceptions.PlayerBlocked('Отсутствует или неверный токен')
        elif 'error' in data.keys():
            raise Exceptions.PlayerBlocked(data['error'])
        if not data['found']:
            raise Exceptions.PlayerBlocked(f'Нет данных по {id_type} id "{id}"')
        return 'https:'+data['link']
    
    async def get_info(self, id: str, id_type: str) -> dict:
        if type(id) == int:
            id = str(id)
        elif type(id) != str:
            raise ValueError(f'Для id ожидался тип str, получен "{type(id)}"')

        link = await self._link_to_info(id, id_type)
        data = await self.get(link, text=True)
        soup = await self.soup(data)
        if self._is_serial(link):
            series_count = len(soup.find("div", {"class": "serial-series-box"}).find("select").find_all("option"))
            try:
                translations_div = soup.find("div", {"class": "serial-translations-box"}).find("select").find_all("option")
            except:
                translations_div = None
            return {
                'series_count': series_count,
                'translations': self._generate_translations_dict(translations_div)
            }
        elif self._is_video(link):
            series_count = 0
            try:
                translations_div = soup.find("div", {"class": "movie-translations-box"}).find("select").find_all("option")
            except AttributeError:
                translations_div = None
            return {
                'series_count': series_count,
                'translations': self._generate_translations_dict(translations_div)
            }
        else:
            raise Exceptions.PlayerBlocked('Ссылка на данные не была распознана как ссылка на сериал или фильм')
    
    def _is_serial(self, iframe_url: str) -> bool:
        return True if iframe_url[iframe_url.find(".info/")+6] == "s" else False

    def _is_video(self, iframe_url: str) -> bool:
        return True if iframe_url[iframe_url.find(".info/")+6] == "v" else False
    
    def _generate_translations_dict(self, translations_div) -> dict:
        translations = []
        for translation in translations_div:
            a = {}
            a['id'] = translation['value']
            a['type'] = translation['data-translation-type']
            if a['type'] == 'voice':
                a['type'] = "Озвучка"
            elif a['type'] == 'subtitles':
                a['type'] = "Субтитры"
            a['name'] = translation.text
            translations.append(a)
        else:
            translations = [{"id": "0", "type": "Неизвестно", "name": "Неизвестно"}]
        return translations

    async def get_link(self, id: str, id_type: str, seria_num: int, translation_id: str) -> tuple[str, int]:
        link = await self._link_to_info(id, id_type)
        data = await self.get(link, text=True)
        soup = await self.soup(data)
        urlParams = data[data.find('urlParams')+13:]
        urlParams = loads(urlParams[:urlParams.find(';')-1])
        if translation_id != "0" and seria_num != 0: # Обычный сериал с известной озвучкой на более чем 1 серию
            container = soup.find('div', {'class': 'serial-translations-box'}).find('select')
            media_hash = None
            media_id = None
            for translation in container.find_all('option'):
                if translation.get_attribute_list('data-id')[0] == translation_id:
                    media_hash = translation.get_attribute_list('data-media-hash')[0]
                    media_id = translation.get_attribute_list('data-media-id')[0]
                    break
            url = f'https://kodik.info/serial/{media_id}/{media_hash}/720p?min_age=16&first_url=false&season=1&episode={seria_num}'
            data = await self.get(url, text=True)
            soup = await self.soup(data)
        elif translation_id != "0" and seria_num == 0: # Фильм/одна серия с несколькими переводами
            container = soup.find('div', {'class': 'movie-translations-box'}).find('select')
            media_hash = None
            media_id = None
            for translation in container.find_all('option'):
                if translation.get_attribute_list('data-id')[0] == translation_id:
                    media_hash = translation.get_attribute_list('data-media-hash')[0]
                    media_id = translation.get_attribute_list('data-media-id')[0]
                    break
            url = f'https://kodik.info/video/{media_id}/{media_hash}/720p?min_age=16&first_url=false&season=1&episode={seria_num}'
            data = await self.get(url, text=True)
            soup = await self.soup(data)
        script_url = soup.find_all('script')[1].get_attribute_list('src')[0]

        hash_container = soup.find_all('script')[4].text
        video_type = hash_container[hash_container.find('.type = \'')+9:]
        video_type = video_type[:video_type.find('\'')]
        video_hash = hash_container[hash_container.find('.hash = \'')+9:]
        video_hash = video_hash[:video_hash.find('\'')]
        video_id = hash_container[hash_container.find('.id = \'')+7:]
        video_id = video_id[:video_id.find('\'')]

        link_data, max_quality = await self._get_link_with_data(video_type, video_hash, video_id, urlParams, script_url)

        download_url = str(link_data).replace("https://", '')
        download_url = download_url[2:-26] # :hls:manifest.m3u8

        return download_url, max_quality
    
    async def _get_link_with_data(self, video_type: str, video_hash: str, video_id: str, urlParams: dict, script_url: str):
        params={
            "hash": video_hash,
            "id": video_id,
            "type": video_type,
            'd': urlParams['d'],
            'd_sign': urlParams['d_sign'],
            'pd': urlParams['pd'],
            'pd_sign': urlParams['pd_sign'],
            'ref': '',
            'ref_sign': urlParams['ref_sign'],
            'bad_user': 'true',
            'cdn_is_working': 'true',
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        post_link = await self._get_post_link(script_url)
        data = await self.post(f'https://kodik.info{post_link}', data=params, headers=headers)
        url = self._convert(data['links']['360'][0]['src'])
        max_quality = max([int(x) for x in data['links'].keys()])
        try:
            return b64decode(url.encode()), max_quality
        except:
            return str(b64decode(url.encode()+b'==')).replace("https:", ''), max_quality
        
    def _convert_char(self, char: str):
        low = char.islower()
        alph = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if char.upper() in alph:
            ch = alph[(alph.index(char.upper())+13)%len(alph)]
            if low:
                return ch.lower()
            else:
                return ch
        else:
            return char

    def _convert(self, string: str):
        # Декодирование строки со ссылкой
        return "".join(map(self._convert_char, list(string)))
    
    async def _get_post_link(self, script_url: str):
        data = await self.get('https://kodik.info'+script_url, text=True)
        url = data[data.find("$.ajax")+30:data.find("cache:!1")-3]
        return b64decode(url.encode()).decode()



