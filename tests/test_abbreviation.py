import pytest

from qfxaile.abbreviation import AbbreviationService


class Response:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return [{"trans": ["很好", "明白"]}]


class Client:
    async def post(self, *args, **kwargs):
        return Response()


@pytest.mark.asyncio
async def test_abbreviation_query_parses_translations():
    assert (
        await AbbreviationService("https://example.test", 5, Client()).query("nbnhhsh")
        == "nbnhhsh: 很好, 明白"
    )


@pytest.mark.asyncio
async def test_abbreviation_query_rejects_invalid_input():
    assert (
        await AbbreviationService("https://example.test", 5, Client()).query("中文")
        == "没有找到这个缩写"
    )
