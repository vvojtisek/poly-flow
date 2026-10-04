import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.enums import CefrLevel
from app.domain.progression import CURRICULUM_END, MILESTONES, frequency_band, is_extension
from app.main import app


def test_milestone_sequence():
    assert [m.rank for m in MILESTONES] == [100, 500, 1000, 2500, 4000, 5000, 6000]
    by_rank = {m.rank: m for m in MILESTONES}
    assert by_rank[100].cefr is None
    assert by_rank[500].cefr is CefrLevel.A1
    assert by_rank[1000].cefr is CefrLevel.A2
    assert by_rank[2500].cefr is CefrLevel.B1
    assert by_rank[4000].cefr is by_rank[5000].cefr is CefrLevel.B2


def test_nothing_past_curriculum_is_required_or_claims_cefr():
    for m in MILESTONES:
        past = m.rank > CURRICULUM_END
        assert m.voluntary is past
        assert m.passive_focus is past
        if past:
            assert m.cefr is None  # no C1 claim from vocabulary drills


@pytest.mark.parametrize(
    ("rank", "band"),
    [
        (1, 100),
        (100, 100),
        (101, 500),
        (1000, 1000),
        (1001, 2500),
        (2501, 4000),
        (4001, 5000),
        (5000, 5000),
        (5001, 6000),
        (6000, 6000),
        (6001, 7000),
        (12345, 13000),
    ],
)
def test_frequency_band(rank, band):
    assert frequency_band(rank) == band


def test_frequency_band_rejects_non_positive():
    with pytest.raises(ValueError):
        frequency_band(0)


def test_is_extension():
    assert not is_extension(5000)
    assert is_extension(5001)


async def test_milestones_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/progression/milestones")
    assert r.status_code == 200
    body = r.json()
    assert body["curriculum_end"] == 5000
    assert body["milestones"][-1] == {
        "rank": 6000,
        "key": "extension_passive",
        "cefr": None,
        "voluntary": True,
        "passive_focus": True,
    }
