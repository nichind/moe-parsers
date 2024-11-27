import pytest
from moe_parsers.providers.animego import AnimegoParser, AnimegoEpisode, AnimegoAnime


@pytest.mark.asyncio
async def test_animego_search():
    parser = AnimegoParser()
    res = await parser.search("plastic memoires")
    assert len(res) > 0
    assert "plastic memories" in res[0].orig_title.lower()


@pytest.mark.asyncio
async def test_animego_get_info():
    parser = AnimegoParser()
    data = await parser.get_info(
        "https://animego.org/anime/atri-moi-dorogie-momenty-2595"
    )
    assert data["animego_id"] == "2595"


@pytest.mark.asyncio
async def test_animego_get_episodes():
    parser = AnimegoParser()
    episodes = await parser.get_episodes(
        "https://animego.org/anime/atri-moi-dorogie-momenty-2595"
    )
    assert len(episodes) == 13
    assert isinstance(episodes[0], AnimegoEpisode)


@pytest.mark.asyncio
async def test_animego_get_translations():
    parser = AnimegoParser()
    translations = await parser.get_translations("2595")
    assert len(translations) >= 1

@pytest.mark.asyncio
async def test_animego_get_episode_videos():
    parser = AnimegoParser()
    anime = (await parser.search("plastic memories"))[0]
    await anime.get_episodes()
    await anime.get_translations()
    for episode in anime.episodes:
        assert len(await episode.get_videos()) > 0
        break

@pytest.mark.asyncio
async def test_animego_get_videos():
    parser = AnimegoParser()
    videos = await parser.get_videos("30387")
    assert len(videos) >= 1


@pytest.mark.asyncio
async def test_animego_get_shikimori_id():
    assert (
        await AnimegoAnime().get_shikimori_id(
            "https://animego.org/anime/plastikovye-vospominaniya-2318"
        )
        == "27775"
    )
