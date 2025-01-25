from .adapter import Client
from typing import TypedDict, Unpack, Literal
from enum import Enum


class _Parser:
    class Language(Enum):
        EN = "en"
        JP = "jp"
        RU = "ru"

    class ParserParams(TypedDict, total=False):
        client: Client
        language: Literal["EN", "JP", "RU"]

    def __init__(self, **params: Unpack[ParserParams]):
        self.__dict__.update(**params)


class Parser(_Parser):
    def __init__(self, **params: Unpack[_Parser.ParserParams]):
        self.language = "EN"
        self.client = Client()
        self.__dict__.update(**params)
