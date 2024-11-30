import pytest
from moe_parsers.providers.aniboom import AniboomParser, AniboomAnime, AniboomEpisode


@pytest.mark.asyncio
async def test_aniboom_search():
    parser = AniboomParser()
    res = await parser.search("plastic memoires")
    assert len(res) > 0
    assert "plastic memories" in res[0].orig_title.lower()


@pytest.mark.asyncio
async def test_aniboom_get_info():
    parser = AniboomParser()
    data = await parser.get_info(
        "https://animego.org/anime/atri-moi-dorogie-momenty-2595"
    )
    assert data["animego_id"] == "2595"
    assert data["status"] == "Вышел"
    assert len(data["translations"]) >= 1


@pytest.mark.asyncio
async def test_aniboom_get_episodes():
    parser = AniboomParser()
    episodes = await parser.get_episodes(
        "https://animego.org/anime/atri-moi-dorogie-momenty-2595"
    )
    assert len(episodes) == 13
    assert isinstance(episodes[0], AniboomEpisode)


@pytest.mark.asyncio
async def test_aniboom_get_episode_videos():
    parser = AniboomParser()
    anime = (await parser.search("plastic memories"))[0]
    await anime.get_info()
    videos = await anime.get_videos()
    assert isinstance(videos[0][0], dict)
    assert len(videos[0]) >= 1


@pytest.mark.asyncio
async def test_aniboom_get_translations():
    parser = AniboomParser()
    translations = await parser.get_translations("2595")
    assert len(translations) >= 1


@pytest.mark.asyncio
async def test_aniboom_get_playlist():
    parser = AniboomParser()
    playlist = await parser.get_mpd_content("2318", 1, "1")
    assert len(playlist.content) >= 256


@pytest.mark.asyncio
async def test_aniboom_get_shikimori_id():
    assert (
        await AniboomAnime().get_shikimori_id(
            "https://animego.org/anime/plastikovye-vospominaniya-2318"
        )
        == "27775"
    )
