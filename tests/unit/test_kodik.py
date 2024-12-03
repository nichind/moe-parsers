import pytest
from moe_parsers.providers.kodik import KodikParser, KodikAnime, KodikEpisode, KodikIframe


@pytest.mark.asyncio
async def test_kodik_search():
    parser = KodikParser()
    res = await parser.search("plastic memories")
    assert len(res) > 0
    assert "27775" in res[0].anime_id
    
@pytest.mark.asyncio
async def test_kodik_get_video():
    parser = KodikParser()
    res = await parser.search("plastic memories")
    assert len(res) > 0
    await res[0].get_video(1)
    assert len(res[0].episodes) > 0
    assert isinstance(res[0].episodes[0], KodikEpisode)
    