from typing import List, TypedDict, Unpack, Literal, Dict
from .adapter import _Client
from enum import Enum
from datetime import datetime


class _Anime:
    class Type(Enum):
        TV = "TV"
        MOVIE = "Movie"
        OVA = "OVA"
        ONA = "ONA"
        MUSIC = "Music"
        SPECIAL = "Special"
        UNKNOWN = "Unknown"

    class Status(Enum):
        ONGOING = "Ongoing"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"
        HIATUS = "Hiatus"
        UNKNOWN = "Unknown"

    class Language(Enum):
        EN = "en"
        JP = "jp"
        RU = "ru"
        UNKNOWN = "unknown"

    class Episode:
        announced: datetime
        completed: datetime
        episode_number: int
        episode_id: str

        class EpisodeStatus(Enum):
            RELEASED = "Released"
            DELAYED = "Delayed"
            ANNOUNCED = "Announced"
            UNKNOWN = "Unknown"

        episode_status: Literal["Released", "Delayed", "Announced", "Unknown"]

        class Video:
            is_raw: bool
            is_subbed: bool
            is_dubbed: bool
            translation_name: str
            translation_language: str
            url: str
            quality: Literal[
                "144", "240", "360", "480", "720", "1080", "1440", "2160", "unknown"
            ]

            class Stream:
                data: str
                url: str

        videos: List[Video]

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Params(TypedDict, total=False):
        anime_type: Literal["TV", "MOVIE", "OVA", "ONA", "MUSIC", "SPECIAL", "UNKNOWN"]
        ids: Dict[Literal["id_type"], str]
        status: Literal["ONGOING", "COMPLETED", "CANCELLED", "HIATUS", "UNKNOWN"]
        language: Literal["EN", "JP", "RU", "UNKNOWN"]
        episodes: List["_Anime._Episode"]
        title: str
        original_title: str
        all_titles: List[str]
        description: dict
        announced: datetime
        completed: datetime
        data: dict
        client: _Client

    @property
    def mal_id(self) -> int:
        return self.ids.get("mal", None)

    @property
    def total_episodes(self) -> int:
        return len(self.episodes)

    def __init__(self, **params: Unpack["_Anime.Params"]):
        self.__dict__.update(params)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__})"


class Anime(_Anime):
    def __init__(self, **params: Unpack["_Anime.Params"]):
        super().__init__(**params)
        self.anime_type = self.Type.UNKNOWN
        self.status = self.Status.UNKNOWN
        self.language = self.Language.UNKNOWN
        self.episodes = []
        self.ids = {}
