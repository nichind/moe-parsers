from typing import List, TypedDict, Unpack, Literal, Dict, Self
from .adapter import _Client
from .parser import _Parser
from enum import Enum
from datetime import datetime


class XEnum(Enum):
    @classmethod
    def values(cls) -> List:
        return [value.value for key, value in cls.__dict__.items() if not key.startswith("_")]

    def __str__(self):
        return self.value

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.value}")'

    def __eq__(self, other):
        """
        Basically makes the enum comparing to string work; when compared not to the string compare using default enum behavior
        """
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

    def __hash__(self):
        return super().__hash__()


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
    def id(self) -> str | int | None:
        """
        Retrieves the ID of the item using the MyAnimeList ID type.

        Returns
        -------
        str or int
            The ID associated with the MAL ID type, or None if not available.
        """
        return self.ids.get(_BaseItem.IDType.MAL, None)

    def get_id(
        self,
        id_type: Literal["shikimori", "mal", "kinopoisk", "imdb", "animego", "kodik"] = "mal",
    ) -> str | int:
        """
        Retrieves the ID of the item using the specified ID type.

        Parameters
        ----------
        id_type : str
            The ID type to use for retrieval. Defaults to "mal".

        Returns
        -------
        str or int
            The ID associated with the specified ID type, or None if not available.
        """
        return self.ids.get(_BaseItem.IDType(id_type), None)

    @property
    def shikimori_id(self) -> str | int:
        """
        Retrieves the ID of the item using the Shikimori ID type.

        Returns
        -------
        str or int
            The ID associated with the Shikimori ID type, or None if not available.
        """
        return self.get_id(id_type=_BaseItem.IDType.SHIKIMORI)
    
    mal = id

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__})"

    def __init__(self, **params):
        """
        Initialize a new instance of the class.

        Parameters
        ----------
        **params : dict
            The parameters to initialize the new instance with.

        Notes
        -----
        This method updates the current instance's __dict__ with the given
        parameters, so it is possible to pass any keyword argument to it and
        it will be set as an attribute of the instance.
        """
        self.__dict__.update(params)

    def __iter__(self):
        """
        Called when code tries to iterate over an instance of the class.
        Made to avoid exceptions when only 1 item was fetched but the code logic expects a list of items
        
        Example:
        >>> item = Anime()
        >>> for i in item:
        >>>     print(i)   # Will print the item, close the loop
        """
        yield self


class Anime(_BaseItem):
    class Type(XEnum):
        TV = "tv"
        MOVIE = "movie"
        OVA = "ova"
        ONA = "ona"
        MUSIC = "music"
        TV_SPECIAL = "tv_special"
        SPECIAL = "special"
        UNKNOWN = "unknown"

    class Status(XEnum):
        ANNOUNCED = "announced"
        ONGOING = "ongoing"
        RELEASED = "released"
        CANCELLED = "cancelled"
        HIATUS = "hiatus"
        PAUSED = "paused"
        UNKNOWN = "unknown"

    class AgeRating(XEnum):
        G = "g"
        PG = "pg"
        PG_13 = "pg_13"
        R = "r"
        R_PLUS = "r_plus"
        RX = "rx"
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
            quality: Literal["144", "240", "360", "480", "720", "1080", "1440", "2160", "unknown"]

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
    released: datetime
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
    related: List[Dict[str, _BaseItem]]
    videos: List[Dict[str, str]]
    screenshots: List[Dict[str, str]]
    external_links = List[Dict[str, str]]

    @property
    def total_duration(self) -> int | None:
        """
        Total duration of all episodes (even if episode is not released yet) in minutes

        Returns:
            int | None: Total duration in minutes if episodes are present, None otherwise
        """
        return self.episode_duration * len(self.episodes) if self.episodes else None

    @property
    def released_duration(self) -> int | None:
        """
        Total duration of all released episodes in minutes
        """
        if self.total_duration:
            return self.episode_duration * len(
                [episode for episode in self.episodes if episode.status == self.Episode.EpisodeStatus.RELEASED]
            )

    @property
    def people(self) -> List["Person"]:
        """
        List of all people in the anime (directors, actors, producers, writers, editors, composers, operators, designers)
        """
        return [
            getattr(self, name)
            for name in (
                "directors",
                "actors",
                "producers",
                "writers",
                "editors",
                "composers",
                "operators",
                "designers",
            )
            if name in self.__dict__
        ]

    @property
    def total_episodes(self) -> int | None:
        """
        The total number of episodes in the anime. If the anime has no episodes,
        this property will be None.

        Returns:
            int | None: The total number of episodes or None
        """
        return len(self.episodes) if self.episodes else None

    @property
    def all_titles(self) -> str:
        """
        All titles of the anime in all languages

        Returns:
            str: A string of all titles in all languages separated by commas
        """
        return [str(y) for x in self.title.values() if len(x) > 0 for y in x if y]

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__})"


class Manga(_BaseItem):
    class Type(XEnum):
        MANGA = "manga"
        MANHWA = "manhwa"
        MANHUA = "manhua"
        LIGHT_NOVEL = "light_novel"
        NOVEL = "novel"
        ONE_SHOT = "one_shot"
        DOUJIN = "doujin"
        UNKNOWN = "unknown"

    Status = Anime.Status
    item_type = _BaseItem.ItemType.MANGA
    type: Type
    ids: Dict[_BaseItem.IDType, str | int]
    status: Anime.Status
    volumes: int
    chapters: int
    characters: List["Character"]
    external_links = List[Dict[str, str]]
    data: Dict
    all_titles = Anime.all_titles


class Character(_BaseItem):
    class Type(XEnum):
        MAIN = "main"
        SUPPORTING = "supporting"

    item_type = _BaseItem.ItemType.CHARACTER
    type: Type
    ids: Dict[_BaseItem.IDType, str | int]
    name: Dict[_BaseItem.Language, List[str] | str]
    description: Dict[_BaseItem.Language, List[str] | str]
    url: str


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
    cast_in: List[Anime | Manga | Dict[_BaseItem.ItemType, Dict[_BaseItem.IDType, str | int]]]
