"""
后端API测试
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    """测试深度健康检查"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回结构
    assert "status" in data
    assert "timestamp" in data
    assert "checks" in data
    
    # 验证状态值合法
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    # 验证各个检查项存在
    checks = data["checks"]
    assert "database" in checks
    assert "chromadb" in checks
    assert "disk_space" in checks
    
    # 验证每个检查项都有 status 和 message
    for check_name, check_data in checks.items():
        assert "status" in check_data
        assert "message" in check_data
        assert check_data["status"] in ["ok", "warning", "error"]


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