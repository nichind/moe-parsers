from re import compile
from typing import List
from ..classes import Anime, Parser, ParserParams, Exceptions, Media
from .aniboom import AniboomParser, MPDPlaylist, AniboomAnime, AniboomEpisode
from .kodik import KodikIframe
import asyncio


class AnimegoEpisode(Anime.Episode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser: AnimegoParser = (
            kwargs["parser"] if "parser" in kwargs else AnimegoParser()
        )
        if not isinstance(self.parser, AnimegoParser):
            self.parser = AnimegoParser(proxy=kwargs["parser"].__dict__.get("proxy", None) if "parser" in kwargs else None)

    async def get_video(self, translation_id: int | str = None, provider_id: int | str = None) -> Media:
        if not self.videos:
            await self.get_videos()
        for video in self.videos:
            if translation_id and video["translation_id"] != translation_id:
                continue
            if provider_id and video["provider_id"] != provider_id:
                continue
            media = KodikIframe(url=video["content"], parser=self.parser) if "kodik" in video["content"] else Media(url=video["content"])
            if media not in self.videos:
                self.videos.append(media)
            return media
        

    async def get_videos(self) -> List[dict]:
        if self.status != "Released":
            return []
        self.videos = await self.parser.get_videos(self.episode_id)
        res = []
        async with asyncio.Semaphore(6):
            tasks = []
            for video in self.videos.values():
                for player in video["players"]:
                    if player["name"] == "AniBoom":
                        tasks += [
                            asyncio.create_task(
                                self._get_mpd_for_player(
                                    player["url"].split("?")[0],
                                    self.episode_num,
                                    compile(r"translation=(\d+)")
                                    .search(player["url"])
                                    .group(1),
                                    player["provider_id"],
                                )
                            )
                        ]
                    elif "kodik" in player["url"]:
                        res += [
                            {
                                "translation_id": video["dub_id"],
                                "content": KodikIframe(url=player["url"], parser=self.parser),
                                "provider_id": player["provider_id"],
                                "provider_name": player["name"],
                            }
                        ]
                    else:
                        res += [
                            {
                                "translation_id": video["dub_id"],
                                "content": player["url"],
                                "provider_id": player["provider_id"],
                                "provider_name": player["name"],
                            }
                        ]
            for task in asyncio.as_completed(tasks):
                url = (await task)[0]
                res += [
                    {
                        "translation_id": video["dub_id"],
                        "content": url,
                        "provider_id": player["provider_id"],
                        "provider_name": "AniBoom",
                    }
                ]
        self.videos = res
        return self.videos

    async def _get_mpd_for_player(
        self, url: str, episode_num: int, translation_id: str, provider_id: str
    ) -> MPDPlaylist:
        return (
            await AniboomParser().get_mpd_playlist(url, episode_num, translation_id),
        )


class AnimegoAnime(Anime):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser: AnimegoParser = (
            kwargs["parser"] if "parser" in kwargs else AnimegoParser()
        )

    async def get_episodes(self) -> List[AnimegoEpisode]:
        await AniboomAnime.get_episodes()
        for i, episode in enumerate(self.episodes):
            self.episodes[i] = AnimegoEpisode(**episode.__dict__)
        return self.episodes

    async def get_translations(self) -> dict:
        self.translations = await AniboomAnime.get_translations(self)
        return self.translations

    async def get_info(self) -> dict:
        await AniboomAnime.get_info(self)
        for i, episode in enumerate(self.episodes):
            if not isinstance(episode, AnimegoEpisode):
                self.episodes[i] = AnimegoEpisode(**episode.__dict__)
        return self.data

    async def get_video(
        self,
        episode_num: int | str,
        translation_id: int | str = None,
        provider_id: int | str = None,
    ):
        for episode in self.episodes if self.episodes else await self.get_episodes():
            episode: AnimegoEpisode
            if episode.episode_num == str(episode_num):
                videos = await episode.get_videos()
                for name, video in videos.items():
                    if (
                        name == str(translation_id)
                        or video["dub_id"] == str(translation_id)
                    ) or translation_id is None:
                        for player in video["players"]:
                            if (
                                player["name"] == str(provider_id)
                                or player["provider_id"] == str(provider_id)
                            ) or provider_id is None:
                                return player["url"]
        return None

    async def get_videos(self) -> List[dict]:
        """
        Get all videos for all episodes.
        Very long process, can take a while. Probably shouldn't be used on prod

        Returns:
            List[dict]: List of videos for each episode
        """
        for episode in self.episodes if self.episodes else await self.get_episodes():
            pass
        results = [[] for _ in range(len(self.episodes))]
        for i, episode in enumerate(self.episodes):
            videos = await episode.get_videos()
            results[i] = videos
        return results

    async def get_shikimori_id(self, url: str = None) -> str | None:
        return await AniboomAnime().get_shikimori_id(self.url if not url else url)


class AnimegoParser(Parser):
    def __init__(self, **kwargs):
        """
        Animego.org Parser

        Args:
            **kwargs: Additional keyword arguments to pass to the parent Parser class.
        """
        self.params = ParserParams(
            base_url="https://animego.org/",
            headers={
                "User-Agent": "",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://animego.org/",
            },
            language=Parser.Language.RU,
        )
        super().__init__(self.params, **kwargs)
        self._parser = AniboomParser(params=self.params, **kwargs)

    async def convert2anime(self, **kwargs) -> AnimegoAnime:
        kwargs["parser"] = self
        anime = AnimegoAnime(
            **kwargs
        )
        return anime

    async def search(self, query: str) -> List[AnimegoAnime]:
        animes = await self._parser.search(query)
        for i, anime in enumerate(animes):
            animes[i] = await self.convert2anime(**anime.__dict__)
        return animes

    async def get_info(self, url: str) -> dict:
        return await self._parser.get_info(url)

    async def get_episodes(self, url: str) -> List[AnimegoEpisode]:
        episodes = await self._parser.get_episodes(url)
        for i, episode in enumerate(episodes):
            episodes[i] = AnimegoEpisode(**episode.__dict__)
        return episodes

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
            dubs = {}
            for translation in translations_elem:
                dubbing = translation.get_attribute_list("data-dubbing")[0]
                name = translation.text.strip()
                dubs[dubbing] = name

            translations = []
            added = []
            players_elem = soup.find("div", {"id": "video-players"}).find_all(
                "span", {"class": "video-player-toggle-item"}
            )
            for player in players_elem:
                dubbing = player.get_attribute_list("data-provide-dubbing")[0]
                translation_id = player.get_attribute_list("data-player")[0]
                translation_id = translation_id[translation_id.rfind("=") + 1 :]
                if dubs[dubbing] in added:
                    continue
                added += [dubs[dubbing]]
                translations += [{"name": dubs[dubbing], "translation_id": dubbing}]

        except Exception as exc:
            print(exc)

        return translations

    async def get_videos(self, episode_id: int | str):
        response = await self.get(f"https://animego.org/anime/series?id={episode_id}")
        soup = await self.soup(response["content"])
        videos = {}
        dubs = {}
        for dub in soup.find("div", {"id": "video-dubbing"}).find_all(
            "span", {"class": "video-player-toggle-item"}
        ):
            videos[dub.text.strip()] = {
                "dub_id": dub.get_attribute_list("data-dubbing")[0],
                "players": [],
            }
            dubs[str(dub.get_attribute_list("data-dubbing")[0])] = dub.text.strip()
        for player in soup.find("div", {"id": "video-players"}).find_all(
            "span", {"class": "video-player-toggle-item"}
        ):
            name = player.find("span").text.strip()
            url = "https:" + player.get_attribute_list("data-player")[0]
            videos[dubs[player.get_attribute_list("data-provide-dubbing")[0]]][
                "players"
            ].append(
                {
                    "name": name,
                    "provider_id": player.get_attribute_list("data-provider")[0],
                    "url": url,
                }
            )
        return videos

    async def get_video(
        self, episode_id: int | str, dub_id: int | str, provider_id: int | str
    ):
        videos = await self.get_videos(episode_id)
        for dub in videos.values():
            if str(dub_id) == dub["dub_id"]:
                for player in dub["players"]:
                    if str(provider_id) == player["provider_id"]:
                        return player["url"]
