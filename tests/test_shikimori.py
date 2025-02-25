import pytest
from moe_parsers.providers.shikimori import ShikimoriParser, Anime


@pytest.mark.asyncio
async def test_search():
    parser = ShikimoriParser()
    item = await parser.search(limit=1, search="plastic memories", searchType="animes")
    assert isinstance(item, Anime)
    assert len(item.characters) > 0
    assert len(item.directors) > 0
    assert item.status == Anime.Status.RELEASED
    assert item.type == Anime.Type.TV
    assert item.thumbnail
