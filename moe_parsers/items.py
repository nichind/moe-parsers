from typing import List, TypedDict, Unpack, Literal, Dict
from .adapter import _Client
from .parser import _Parser
from enum import Enum
from datetime import datetime


class _BaseItem:
    class ItemType(Enum):
        ANIME = "Anime"
        MANGA = "Manga"
        CHARACTER = "Character"
        PERSON = "Person"
        OTHER = "Other"

    class IDType(Enum):
        MAL = "mal"
        SHIKIMORI = "shikimori"
        KINPOISK = "kinpoisk"
        ANIMEGO = "animego"
        IMDB = "imdb"
        KODIK = "kodik"

    class Language(Enum):
        ENGLISH = "en"
        JAPANESE = "jp"
        RUSSIAN = "ru"
        UNKNOWN = "unknown"

    item_type: ItemType
    parser: _Parser
    client: _Client
    data: dict

    @property
    def id(self) -> int:
        return self.item_id


class Anime(_BaseItem):
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

    class Rating(Enum):
        G = "G"
        PG = "PG"
        PG_13 = "PG-13"
        R = "R"
        R_PLUS = "R+"
        NC_17 = "NC-17"
        NR = "NR"
        UNKNOWN = "unknown"

    class Episode(_BaseItem):
        item_type = "episode"
        announced: datetime
        aired: datetime
        number: int
        id: str | int
        title: str

        class EpisodeStatus(Enum):
            RELEASED = "Released"
            DELAYED = "Delayed"
            ANNOUNCED = "Announced"
            UNKNOWN = "Unknown"

        status: EpisodeStatus

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

        def __repr__(self):
            return f'<Episode {self.number} ({self.status.value}{(", " + self.aired.strftime("%Y-%m-%d")) if self.aired else ""}) - "{self.title[:30] + "..." if len(self.title) > 30 else self.title}">'

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    item_type = _BaseItem.ItemType.ANIME
    type: Type
    ids: Dict[_BaseItem.IDType, str]
    status: Status
    language: Language
    episodes: List[Episode]
    title: str
    original_title: str
    all_titles: List[str]
    description: dict
    announced: datetime
    started: datetime
    completed: datetime
    data: dict
    client: _Client
    studios: List[str]
    genres: List[str]
    tags: List[str]
    rating: float
    directors: List[str]
    actors: List[str]
    producers: List[str]
    writers: List[str]
    editors: List[str]
    composers: List[str]
    operators: List[str]
    designers: List[str]
    age_rating: Rating
    episode_duration: int

    @property
    def total_duration(self) -> int:
        return self.episode_duration * len(self.episodes)
    
    @property
    def released_duration(self) -> int:
        return self.total_duration * [episode.status == self.Episode.EpisodeStatus.RELEASED for episode in self.episodes].count(True)

    def get_id(self, id_type: _BaseItem.IDType) -> str | int:
        return self.ids.get(id_type, None)

    @property
    def shikimori_id(self) -> str | int:
        return self.get_id(id_type=_BaseItem.IDType.SHIKIMORI)

    @property
    def mal_id(self) -> str | int:
        return self.get_id(id_type=_BaseItem.IDType.MAL)

    @property
    def total_episodes(self) -> int:
        return len(self.episodes)

    def __init__(self, **params):
        self.__dict__.update(params)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__})"


class Character(_BaseItem):
    item_type = _BaseItem.ItemType.CHARACTER


class Person(_BaseItem):
    item_type = _BaseItem.ItemType.PERSON
    