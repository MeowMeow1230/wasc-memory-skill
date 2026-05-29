"""MCP Memory Server — 對外暴露記憶管理 API"""

import json
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationCapabilities
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

from src.llm import LLMClient
from src.store import MemoryStore
from src.agent import MemoryAgent

load_dotenv()

# 初始化
store = MemoryStore(user_id="wasc_user")
client = LLMClient()
agent = MemoryAgent(client=client, store=store)

server = Server("wasc-memory-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="reset_memory",
            description="清空所有記憶，回歸空白狀態。評審必須能從空白狀態開始測試。",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="view_memories",
            description="查看所有活躍記憶的結構化列表，包含 type/scope/priority/source。",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_deprecated": {
                        "type": "boolean",
                        "description": "是否包含已淘汰的記憶",
                        "default": False,
                    }
                },
            },
        ),
        Tool(
            name="edit_memory",
            description="編輯指定記憶的內容、scope、priority 等欄位。",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "記憶 ID"},
                    "updates": {
                        "type": "object",
                        "description": "要更新的欄位，例如 {\"content\": \"新內容\", \"priority\": 8}",
                    },
                },
                "required": ["memory_id", "updates"],
            },
        ),
        Tool(
            name="delete_memory",
            description="刪除指定記憶，並確保後續任務不再使用該記憶。",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "要刪除的記憶 ID"},
                },
                "required": ["memory_id"],
            },
        ),
        Tool(
            name="chat",
            description="與 Agent 對話。Agent 會自動注入相關記憶並在需要時提取新記憶。",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "用戶訊息"},
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="run_test_harness",
            description="執行 8 步自動化測試並輸出預估分數和裁判備註。",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "reset_memory":
        result = agent.reset()
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    elif name == "view_memories":
        include = arguments.get("include_deprecated", False)
        mems = agent.view_memories(include_deprecated=include)
        return [TextContent(type="text", text=json.dumps(mems, ensure_ascii=False, indent=2))]

    elif name == "edit_memory":
        result = agent.edit_memory(arguments["memory_id"], arguments["updates"])
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    elif name == "delete_memory":
        result = agent.delete_memory(arguments["memory_id"])
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    elif name == "chat":
        reply = agent.chat(arguments["message"])
        return [TextContent(type="text", text=reply)]

    elif name == "run_test_harness":
        from tests.test_harness import MemoryTestHarness
        harness = MemoryTestHarness(agent)
        report = harness.run_all()
        return [TextContent(type="text", text=json.dumps(report, ensure_ascii=False, indent=2))]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationCapabilities(
                sampling={},
                experimental={},
            ),
            NotificationOptions(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
