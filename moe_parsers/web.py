from aiohttp import ClientSession
from typing import TypedDict
from faker import Faker


class RequestArgs(TypedDict):
    session: ClientSession
    url: str
    method: str


class _RequestResponse:
    status: int
    headers: dict
    text: str
    json: dict
    data: bytes


    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)
        
    def __repr__(self):
        return str(self.__dict__)

    def json(self):
        return self.__dict__.get("json", None)
    

class _Adapter:
    async def request(self, **kwargs: RequestArgs) -> _RequestResponse:
        session = kwargs.get(
            "session",
            ClientSession(
                headers=kwargs.get(
                    "headers",
                    self.__dict__.get(
                        "user_agent", self.default_session_params.get("headers")
                    ),
                )
            ),
        )
        if not kwargs.get("url", None):
            raise Exception("Missing url")
        if kwargs.get("retries", 0) > self.__dict__.get("max_retries", None):
            raise Exception("Too many retries")
        if kwargs.get("method", "get") == "get":
            response = await session.get(kwargs.get("url"))
        elif kwargs.get("method", "get") == "post":
            response = await session.post(kwargs.get("url"))
        else:
            raise Exception("Invalid method")
            
        
    
class Adapter(_Adapter):
    fake = Faker()
    user_agent = fake.user_agent()
    max_retries = 5
    
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)