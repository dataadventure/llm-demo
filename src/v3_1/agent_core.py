from typing import Iterator, AsyncIterator

from langchain_core.outputs import ChatGenerationChunk
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk
from mock_llm import MockLLM
import asyncio

# 全局变量（确保工具和图实例正确共享）
mcp_client = None
loaded_tools: list[BaseTool] = []  # 重命名为loaded_tools，避免与其他变量冲突
mock_llm = None
graph = None


async def init_mcp():
    """初始化MCP并验证工具加载"""
    global mcp_client, loaded_tools, mock_llm
    try:
        mcp_client = MultiServerMCPClient({
            "weather": {
                "url": "http://localhost:8000/mcp",
                "transport": "streamable_http",
            }
        })

        # 强制获取工具并验证
        loaded_tools = await mcp_client.get_tools()
        if not loaded_tools:
            raise ValueError("MCP服务器未返回任何工具，请检查服务器端工具注册")

        # 打印工具详情，确认工具名称正确
        print("成功加载MCP工具:")
        for tool in loaded_tools:
            print(f"- 名称: {tool.name}, 描述: {tool.description}")

        # 绑定工具到LLM
        mock_llm = MockLLM().bind_tools(loaded_tools)

    except Exception as e:
        print(f"MCP初始化失败: {str(e)}")
        raise


class AgentState(MessagesState):
    session_id: str
    messages = []

async def call_model(state: AgentState) -> AsyncIterator[dict]:
    """模型调用节点（支持流式输出）"""
    if not loaded_tools:
        raise RuntimeError("工具列表为空，请检查MCP连接")
    collected = ""
    async for chunk in mock_llm.astream(state["messages"]):
        delta = chunk.message.content
        collected += delta
        # 每个chunk都返回包含消息的字典
        yield {"messages": [AIMessageChunk(content=delta)]}
    print("\n>>> [流式输出完成]")
    # 最后返回完整消息
    # yield {"messages": [AIMessage(content=collected)]}

def build_graph():
    """构建图时显式传递工具列表"""
    global graph
    if not loaded_tools:
        raise RuntimeError("构建图失败：工具列表为空")

    # 关键修正：显式用loaded_tools创建ToolNode，确保工具被正确传入
    tool_node = ToolNode(loaded_tools)

    builder = StateGraph(AgentState)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        lambda state: "tools" if state["messages"][-1].tool_calls else END
    )
    builder.add_edge("tools", "call_model")

    graph = builder.compile()
    return graph