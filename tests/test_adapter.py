import pytest
from moe_parsers.core.adapter import Client


@pytest.mark.asyncio
async def test_adapter():
    client = Client()
    result = await client.get("https://httpbin.org/get")
    assert result.status == 200
    