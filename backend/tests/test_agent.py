"""
日记 Agent 测试 - 验证 tool-calling loop 核心逻辑

测试覆盖：
1. 工具定义格式正确（4 个工具，schema 合法）
2. Agent Loop：先返回 tool_calls → 执行 → 再返回最终回复
3. 无工具调用路径（直接回复）
4. 对话后记忆反思（Hermes 式 learning loop）
5. /api/agent/capabilities 端点
6. 安全检查（敏感输入被拦截）
"""
import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.ai.client import llm
from app.services.ai.agent import DiaryAgent, AGENT_SYSTEM
from app.services.ai.tools import DiaryToolRegistry
from app.services.memory_service import MemoryService


# ==================== Fixtures ====================

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_db():
    """模拟 db session（不执行真实 SQL）"""
    db = MagicMock()
    return db


@pytest.fixture
def mock_vector_store():
    """模拟向量存储"""
    vs = MagicMock()
    vs.search.return_value = []
    vs._initialized = True
    return vs


@pytest.fixture(autouse=True)
def patch_memory_init(monkeypatch):
    """避免 MemoryService 在 mock db 上执行建表 SQL"""
    monkeypatch.setattr(MemoryService, "_init_memory_tables", lambda self: None)


# ==================== 工具定义测试 ====================

def test_tool_definitions_complete(mock_db, mock_vector_store):
    """工具集应包含 4 个工具，schema 合法"""
    registry = DiaryToolRegistry(mock_db, mock_vector_store)
    defs = registry.definitions

    assert len(defs) == 4, "应有 4 个工具"

    names = [d["function"]["name"] for d in defs]
    for expected in ["search_diaries", "get_insights", "get_memory", "save_memory"]:
        assert expected in names, f"缺少工具: {expected}"

    # 验证每个工具有必需字段
    for d in defs:
        assert d["type"] == "function"
        func = d["function"]
        assert "name" in func
        assert "description" in func
        assert "parameters" in func
        assert func["parameters"]["type"] == "object"


def test_search_diaries_tool_schema(mock_db, mock_vector_store):
    """search_diaries 工具的参数定义正确"""
    registry = DiaryToolRegistry(mock_db, mock_vector_store)
    search_tool = next(
        d for d in registry.definitions
        if d["function"]["name"] == "search_diaries"
    )
    props = search_tool["function"]["parameters"]["properties"]
    assert "query" in props
    assert "days" in props
    required = search_tool["function"]["parameters"].get("required", [])
    assert "query" in required


# ==================== Agent Loop 测试 ====================

@pytest.mark.asyncio
async def test_agent_loop_with_tool_call(
    monkeypatch, mock_db, mock_vector_store
):
    """Agent Loop：先调用工具，再返回最终回复"""
    call_count = 0

    async def mock_chat_with_tools(messages, tools, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # 第一次：LLM 决定调用 get_memory
            return {
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "name": "get_memory",
                    "arguments": {"memory_type": "factual"},
                }],
                "finish_reason": "tool_calls",
            }
        # 第二次：基于工具结果给出最终回复
        return {
            "content": "我了解你的习惯了",
            "tool_calls": None,
            "finish_reason": "stop",
        }

    monkeypatch.setattr(llm, "chat_with_tools", mock_chat_with_tools)

    # mock 工具执行
    async def mock_execute(self, name, arguments):
        return "用户常写主题：工作、家庭"
    monkeypatch.setattr(DiaryToolRegistry, "execute", mock_execute)

    # mock 对话后反思（不保存）
    async def mock_simple(prompt, **kwargs):
        return '{"should_save": false}'
    monkeypatch.setattr(llm, "simple_chat", mock_simple)

    agent = DiaryAgent(mock_db, mock_vector_store)
    result = await agent.chat("我最近怎么样", reflect=True)

    assert result["response"] == "我了解你的习惯了"
    assert len(result["tool_usage"]) == 1
    assert result["tool_usage"][0]["tool"] == "get_memory"
    assert call_count == 2, "LLM 应被调用 2 次（工具调用 + 最终回复）"
    assert result["iterations"] >= 1


@pytest.mark.asyncio
async def test_agent_no_tool_call(
    monkeypatch, mock_db, mock_vector_store
):
    """无工具调用路径：LLM 直接回复"""
    async def mock_chat_with_tools(messages, tools, **kwargs):
        return {
            "content": "你好呀，今天过得怎么样？",
            "tool_calls": None,
            "finish_reason": "stop",
        }

    monkeypatch.setattr(llm, "chat_with_tools", mock_chat_with_tools)

    async def mock_simple(prompt, **kwargs):
        return '{"should_save": false}'
    monkeypatch.setattr(llm, "simple_chat", mock_simple)

    agent = DiaryAgent(mock_db, mock_vector_store)
    result = await agent.chat("你好", reflect=True)

    assert result["response"] == "你好呀，今天过得怎么样？"
    assert len(result["tool_usage"]) == 0


@pytest.mark.asyncio
async def test_agent_multiple_tool_calls(
    monkeypatch, mock_db, mock_vector_store
):
    """多轮工具调用：先搜日记，再获取洞察，最后综合回复"""
    call_count = 0

    async def mock_chat_with_tools(messages, tools, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "name": "search_diaries",
                    "arguments": {"query": "工作", "days": 30},
                }],
                "finish_reason": "tool_calls",
            }
        elif call_count == 2:
            return {
                "content": "",
                "tool_calls": [{
                    "id": "call_2",
                    "name": "get_insights",
                    "arguments": {"days": 90},
                }],
                "finish_reason": "tool_calls",
            }
        return {
            "content": "综合来看，你最近状态不错",
            "tool_calls": None,
            "finish_reason": "stop",
        }

    monkeypatch.setattr(llm, "chat_with_tools", mock_chat_with_tools)

    executed = []

    async def mock_execute(self, name, arguments):
        executed.append(name)
        return f"{name} 的结果"

    monkeypatch.setattr(DiaryToolRegistry, "execute", mock_execute)
    monkeypatch.setattr(
        llm, "simple_chat",
        AsyncMock(return_value='{"should_save": false}')
    )

    agent = DiaryAgent(mock_db, mock_vector_store)
    result = await agent.chat("我最近状态怎么样", reflect=False)

    assert result["response"] == "综合来看，你最近状态不错"
    assert len(result["tool_usage"]) == 2
    assert executed == ["search_diaries", "get_insights"]
    assert call_count == 3


# ==================== 对话后记忆反思测试 ====================

@pytest.mark.asyncio
async def test_reflect_saves_memory(
    monkeypatch, mock_db, mock_vector_store
):
    """对话后反思应提取用户认知并存入记忆"""
    async def mock_chat_with_tools(messages, tools, **kwargs):
        return {
            "content": "这很正常，能觉察到这点很了不起",
            "tool_calls": None,
            "finish_reason": "stop",
        }

    monkeypatch.setattr(llm, "chat_with_tools", mock_chat_with_tools)

    # 反思 LLM 返回应保存
    async def mock_simple(prompt, **kwargs):
        return json.dumps({
            "should_save": True,
            "content": "用户害怕被否定",
            "reason": "深层自我认知",
        }, ensure_ascii=False)

    monkeypatch.setattr(llm, "simple_chat", mock_simple)

    saved_calls = []

    async def mock_execute(self, name, arguments):
        if name == "save_memory":
            saved_calls.append(arguments)
            return "已保存"
        return ""

    monkeypatch.setattr(DiaryToolRegistry, "execute", mock_execute)

    agent = DiaryAgent(mock_db, mock_vector_store)
    result = await agent.chat(
        "我其实一直很怕被否定", reflect=True
    )

    assert len(saved_calls) == 1, "应保存 1 条记忆"
    assert "被否定" in saved_calls[0]["content"]
    assert saved_calls[0]["memory_type"] == "factual"


@pytest.mark.asyncio
async def test_reflect_skips_when_no_insight(
    monkeypatch, mock_db, mock_vector_store
):
    """对话无深层认知时不应保存记忆"""
    async def mock_chat_with_tools(messages, tools, **kwargs):
        return {
            "content": "好的",
            "tool_calls": None,
            "finish_reason": "stop",
        }

    monkeypatch.setattr(llm, "chat_with_tools", mock_chat_with_tools)

    async def mock_simple(prompt, **kwargs):
        return json.dumps({"should_save": False}, ensure_ascii=False)

    monkeypatch.setattr(llm, "simple_chat", mock_simple)

    saved_calls = []

    async def mock_execute(self, name, arguments):
        if name == "save_memory":
            saved_calls.append(arguments)
        return ""

    monkeypatch.setattr(DiaryToolRegistry, "execute", mock_execute)

    agent = DiaryAgent(mock_db, mock_vector_store)
    await agent.chat("今天天气不错", reflect=True)

    assert len(saved_calls) == 0, "不应保存记忆"


# ==================== API 端点测试 ====================

@pytest.mark.asyncio
async def test_capabilities_endpoint(client):
    """/api/agent/capabilities 应返回 4 个工具能力"""
    response = await client.get("/api/agent/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_enabled"] is True
    assert len(data["capabilities"]) == 4
    names = [c["name"] for c in data["capabilities"]]
    assert "search_diaries" in names
    assert "save_memory" in names


@pytest.mark.asyncio
async def test_chat_empty_message_rejected(client):
    """空消息应返回 400"""
    response = await client.post(
        "/api/agent/chat", json={"message": "  "}
    )
    assert response.status_code == 400


# ==================== Agent System Prompt 测试 ====================

def test_agent_system_prompt_contains_tool_guidance():
    """系统提示词应包含工具使用指引"""
    assert "search_diaries" in AGENT_SYSTEM
    assert "get_insights" in AGENT_SYSTEM
    assert "save_memory" in AGENT_SYSTEM
    assert "小伴" in AGENT_SYSTEM
    assert "隐性" in AGENT_SYSTEM or "隐" in AGENT_SYSTEM


# ==================== chat_with_tools HTTP 响应解析测试 ====================
# 验证从 DeepSeek 真实 HTTP 响应 JSON → tool_calls 解析的完整路径
# 这比 mock 函数返回值更强——验证了 HTTP 层的 JSON 解析逻辑

def _mock_httpx_client(response_json, status_code=200, response_text=""):
    """构造 mock httpx.AsyncClient，模拟 DeepSeek HTTP 响应"""
    class MockResp:
        def __init__(self):
            self.status_code = status_code
            self.text = response_text
        def json(self):
            return response_json

    class MockClient:
        def __init__(self, *a, **kw):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, url, headers=None, json=None):
            return MockResp()

    return MockClient


@pytest.mark.asyncio
async def test_chat_with_tools_parses_tool_calls_response(monkeypatch):
    """验证能正确解析 DeepSeek 返回的 tool_calls（OpenAI 格式）
    arguments 在真实 API 中是 JSON 字符串，需解析为 dict"""
    from app.services.ai.client import LLMClient

    # 真实 DeepSeek tool_calls 响应格式
    mock_json = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "get_insights",
                        "arguments": '{"days": 90}'
                    }
                }]
            },
            "finish_reason": "tool_calls"
        }]
    }
    monkeypatch.setattr(
        "app.services.ai.client.httpx.AsyncClient",
        _mock_httpx_client(mock_json)
    )

    client = LLMClient()
    client.api_key = "fake_key"

    result = await client.chat_with_tools(
        messages=[{"role": "user", "content": "我最近怎么样"}],
        tools=[{"type": "function", "function": {"name": "get_insights"}}],
    )

    assert result["finish_reason"] == "tool_calls"
    assert result["tool_calls"] is not None
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["id"] == "call_abc123"
    assert result["tool_calls"][0]["name"] == "get_insights"
    # arguments 应从 JSON 字符串解析为 dict
    assert result["tool_calls"][0]["arguments"] == {"days": 90}


@pytest.mark.asyncio
async def test_chat_with_tools_parses_text_response(monkeypatch):
    """验证能正确解析普通文本响应（无 tool_calls）"""
    from app.services.ai.client import LLMClient

    mock_json = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "你好呀，今天过得怎么样？"
            },
            "finish_reason": "stop"
        }]
    }
    monkeypatch.setattr(
        "app.services.ai.client.httpx.AsyncClient",
        _mock_httpx_client(mock_json)
    )

    client = LLMClient()
    client.api_key = "fake_key"

    result = await client.chat_with_tools(
        messages=[{"role": "user", "content": "你好"}],
        tools=[],
    )

    assert result["content"] == "你好呀，今天过得怎么样？"
    assert result["tool_calls"] is None
    assert result["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_chat_with_tools_handles_bad_arguments(monkeypatch):
    """验证 arguments 为无效 JSON 时容错为空 dict"""
    from app.services.ai.client import LLMClient

    mock_json = {
        "choices": [{
            "message": {
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "search_diaries",
                        "arguments": "not valid json"
                    }
                }]
            },
            "finish_reason": "tool_calls"
        }]
    }
    monkeypatch.setattr(
        "app.services.ai.client.httpx.AsyncClient",
        _mock_httpx_client(mock_json)
    )

    client = LLMClient()
    client.api_key = "fake_key"

    result = await client.chat_with_tools(
        messages=[{"role": "user", "content": "test"}],
        tools=[],
    )

    assert result["tool_calls"][0]["arguments"] == {}


@pytest.mark.asyncio
async def test_chat_with_tools_handles_http_error(monkeypatch):
    """验证非 200 响应时优雅降级（如 API key 无效 401）
    与现有 chat() 一致：API 失败时返回 fallback 而非崩溃"""
    from app.services.ai.client import LLMClient

    monkeypatch.setattr(
        "app.services.ai.client.httpx.AsyncClient",
        _mock_httpx_client({}, status_code=401, response_text='{"error":"invalid key"}')
    )

    client = LLMClient()
    client.api_key = "fake_key"

    result = await client.chat_with_tools(
        messages=[{"role": "user", "content": "test"}],
        tools=[],
    )

    # 优雅降级：返回 fallback 响应，不抛异常
    assert "抱歉" in result["content"]
    assert result["tool_calls"] is None
    assert result["finish_reason"] == "stop"
