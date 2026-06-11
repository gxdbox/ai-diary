"""
后端API测试
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    """测试健康检查"""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root(client):
    """测试根路由"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_clean_text(client):
    """测试文本清洗"""
    response = await client.post(
        "/api/diary/clean",
        json={"raw_text": "嗯，今天天气不错啊，我想出去走走。"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "cleaned_text" in data
    assert "嗯" not in data["cleaned_text"] or len(data["cleaned_text"]) < len("嗯，今天天气不错啊，我想出去走走。")


@pytest.mark.asyncio
async def test_analyze(client):
    """测试文本分析"""
    response = await client.post(
        "/api/analysis/analyze",
        json={"text": "今天工作很顺利，心情很好，完成了重要项目。"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "emotion" in data
    assert "topics" in data


@pytest.mark.asyncio
async def test_search_suggestions(client):
    """测试搜索建议"""
    response = await client.get("/api/search/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0


@pytest.mark.asyncio
async def test_stats(client):
    """测试统计接口"""
    response = await client.get("/api/analysis/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_diaries" in data
    assert "total_words" in data
    assert "streak_days" in data