import asyncio
import httpx

from app.main import app


async def _post_sample():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        files = {"file": ("sample.docx", b"dummy content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        data = {"compound_a": "Placebo", "compound_b": "Compound X"}
        return await ac.post("/sae_summary", data=data, files=files)


def test_sae_summary_basic():
    resp = asyncio.run(_post_sample())
    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "sample.docx"
    assert body["compound_a"] == "Placebo"
    assert body["compound_b"] == "Compound X"
