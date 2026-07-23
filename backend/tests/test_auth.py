"""
用户认证系统测试
"""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import init_db


@pytest.fixture
async def client():
    """初始化数据库并创建测试客户端"""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _unique_email() -> str:
    """生成唯一测试邮箱"""
    return f"test_{uuid.uuid4().hex[:8]}@test.com"


async def _register_and_login(client, email: str = None, password: str = "test123456"):
    """辅助函数：注册并返回 auth header"""
    email = email or _unique_email()
    resp = await client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "nickname": email.split("@")[0],
    })
    assert resp.status_code == 200, f"注册失败: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


@pytest.mark.asyncio
async def test_register_success(client):
    """测试注册成功"""
    email = _unique_email()
    response = await client.post("/api/auth/register", json={
        "email": email,
        "password": "mypassword123",
        "nickname": "新用户",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email
    assert data["user"]["nickname"] == "新用户"
    assert "hashed_password" not in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate(client):
    """测试重复邮箱注册"""
    email = _unique_email()
    payload = {"email": email, "password": "test123456", "nickname": "dup"}
    # 第一次注册
    resp1 = await client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 200
    # 第二次注册同一邮箱
    resp2 = await client.post("/api/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "已被注册" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client):
    """测试登录成功"""
    email = _unique_email()
    # 先注册
    await client.post("/api/auth/register", json={
        "email": email,
        "password": "test123456",
        "nickname": "登录用户",
    })
    # 登录（OAuth2 form-urlencoded）
    response = await client.post("/api/auth/login", data={
        "username": email,
        "password": "test123456",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == email


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """测试错误密码登录"""
    email = _unique_email()
    await client.post("/api/auth/register", json={
        "email": email,
        "password": "correct123",
        "nickname": "test",
    })
    response = await client.post("/api/auth/login", data={
        "username": email,
        "password": "wrongpassword",
    })
    assert response.status_code == 401
    assert "错误" in response.json()["detail"]


@pytest.mark.asyncio
async def test_me_without_token(client):
    """测试无 token 访问 /me"""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client):
    """测试带 token 访问 /me"""
    headers, email = await _register_and_login(client)
    response = await client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client):
    """测试无 token 访问受保护端点"""
    response = await client.get("/api/diary/list")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stats_without_token(client):
    """测试无 token 访问统计端点"""
    response = await client.get("/api/analysis/stats")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_short_password(client):
    """测试密码过短"""
    response = await client.post("/api/auth/register", json={
        "email": "short@test.com",
        "password": "123",
        "nickname": "test",
    })
    assert response.status_code == 422  # Pydantic validation error
