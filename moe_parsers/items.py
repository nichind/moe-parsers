from typing import List, TypedDict, Unpack, Literal, Dict
from .adapter import _Client
from .parser import _Parser
from enum import Enum
from datetime import datetime


class XEnum(Enum):
    @classmethod
    def values(cls) -> List:
        return [
            value.value
            for key, value in cls.__dict__.items()
            if not key.startswith("_")
        ]

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.value}")'


class _BaseItem:
    class ItemType(XEnum):
        ANIME = "anime"
        MANGA = "manga"
        CHARACTER = "character"
        PERSON = "person"
        OTHER = "other"
        EPISODE = "episode"

    class IDType(XEnum):
        MAL = "mal"
        SHIKIMORI = "shikimori"
        KINPOISK = "kinpoisk"
        ANIMEGO = "animego"
        IMDB = "imdb"
        KODIK = "kodik"

    class Language(XEnum):
        ENGLISH = "en"
        JAPANESE = "jp"
        RUSSIAN = "ru"
        ROMAJI = "ro"
        UNKNOWN = "unknown"

    item_id: str | int
    item_type: ItemType
    parser: _Parser
    client: _Client
    data: dict
    image: str
    thumbnail: str

    @property
    def id(self) -> int:
        return self.item_id

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__})"

    def __init__(self, **params):
        self.__dict__.update(params)


class Anime(_BaseItem):
    class Type(XEnum):
        TV = "tv"
        MOVIE = "movie"
        OVA = "ova"
        ONA = "ona"
        MUSIC = "music"
        SPECIAL = "special"
        UNKNOWN = "unknown"

    class Status(XEnum):
        ANNOUNCED = "announced"
        ONGOING = "ongoing"
        RELEASED = "released"
        CANCELLED = "cancelled"
        HIATUS = "hiatus"
        UNKNOWN = "unknown"

    class AgeRating(XEnum):
        G = "g"
        PG = "pg"
        PG_13 = "pg_13"
        R = "r"
        R_PLUS = "r_plus"
        NC_17 = "nc_17"
        NR = "nr"
        UNKNOWN = "unknown"

    class Episode(_BaseItem):
        item_type = _BaseItem.ItemType.EPISODE
        announced: datetime
        aired: datetime
        number: int
        episode_id: Dict[_BaseItem.IDType, str | int]
        title: Dict[_BaseItem.Language, List[str] | str]
        status: "Anime.Status"

        class Video:
            is_raw: bool
            is_subbed: bool
            is_dubbed: bool
            translation_name: str
            translation_language: _BaseItem.Language | str
            url: str
            quality: Literal[
                "144", "240", "360", "480", "720", "1080", "1440", "2160", "unknown"
            ]

            class Stream:
                data: str
                url: str
                expires_at: datetime

        videos: List[Video]

        def __repr__(self):
            return f'<Episode {self.number} ({self.status.value}{(", " + self.aired.strftime("%Y-%m-%d")) if "aired" in self.__dict__ else ""}) - "{(self.title[:30] + "..." if len(self.title) > 30 else self.title) if "title" in self.__dict__ else "Unknown"}">'

    class Rating:
        rating: float
        votes: int
        max_rating: int
        min_rating: int

        def __init__(self, rating: int):
            super().__init__(rating)
            self.rating = rating

    item_type = _BaseItem.ItemType.ANIME
    type: Type
    ids: Dict[_BaseItem.IDType, str | int]
    status: Status
    episodes: List[Episode]
    title: Dict[_BaseItem.Language, List[str] | str]
    original_title: str
    all_titles: List[str]
    description: Dict[_BaseItem.Language, List[str] | str]
    announced: datetime
    started: datetime
    completed: datetime
    characters: List["Character"]
    data: Dict
    client: _Client
    studios: List[str]
    genres: Dict[_BaseItem.Language, List[str]]
    tags: List[str]
    rating: Rating
    directors: List["Person"]
    actors: List["Person"]
    producers: List["Person"]
    writers: List["Person"]
    editors: List["Person"]
    composers: List["Person"]
    operators: List["Person"]
    designers: List["Person"]
    age_rating: AgeRating
    episode_duration: int

    @property
    def total_duration(self) -> int | None:
        return self.episode_duration * len(self.episodes) if self.episodes else None

    @property
    def released_duration(self) -> int | None:
        if self.total_duration:
            return self.episode_duration * len(
                [
                    episode
                    for episode in self.episodes
                    if episode.status == self.Episode.EpisodeStatus.RELEASED
                ]
            )

    def get_id(
        self,
        id_type: Literal["shikimori", "mal", "kinopoisk", "imdb", "animego", "kodik"],
    ) -> str | int:
        return self.ids.get(_BaseItem.IDType(id_type), None)

    @property
    def shikimori_id(self) -> str | int:
        return self.get_id(id_type=_BaseItem.IDType.SHIKIMORI)

    @property
    def mal_id(self) -> str | int:
        return self.get_id(id_type=_BaseItem.IDType.MAL)

    @property
    def total_episodes(self) -> int | None:
        return len(self.episodes) if self.episodes else None

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__})"


class Manga(_BaseItem):
    class Type(XEnum):
        MANHWA = "manhwa"
        MANHUA = "manhua"
        LIGHT_NOVEL = "light novel"
        NOVEL = "novel"
        ONE_SHOT = "one-shot"
        DOUJIN = "doujin"
        UNKNOWN = "unknown"

    item_type = _BaseItem.ItemType.MANGA
    type: Type
    ids: Dict[_BaseItem.IDType, str | int]
    status: Anime.Status
    volumes: int
    chapters: int


class Character(_BaseItem):
    item_type = _BaseItem.ItemType.CHARACTER


class Person(_BaseItem):
    class Type(XEnum):
        SEIYUU = "voice actor"
        DIRECTOR = "director"
        PRODUCER = "producer"
        WRITER = "writer"
        EDITOR = "editor"
        COMPOSER = "composer"
        OPERATOR = "operator"
        DESIGNER = "designer"

    item_type = _BaseItem.ItemType.PERSON
    type: Type
    name: Dict[_BaseItem.Language, List[str] | str]
    birthdate: datetime
    passingdate: datetime
    cast_in: List[
        Anime | Manga | Dict[_BaseItem.ItemType, Dict[_BaseItem.IDType, str | int]]
    ]
