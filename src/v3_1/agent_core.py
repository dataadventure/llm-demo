from typing import Iterator, AsyncIterator, Annotated

from langchain_core.outputs import ChatGenerationChunk
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk, AnyMessage
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
    # 注意：下面定义的merge_two_chunks只会对Node之间的消息合并其作用，而不是Node内部的多个Chunk进行合并
    #messages: Annotated[List[AnyMessage], merge_two_chunks]

async def call_model(state: AgentState) -> AsyncIterator[dict]:
    # print(f"call_model is called ... state={state}")
    """模型调用节点（支持流式输出）"""

    collected_chunks = []
    async for chunk in mock_llm.astream(state["messages"]):
        # 只有{}才会被合并 并更新到state["messages"]中去替换旧的message。这里需要注意的是。
        if isinstance(chunk.message, AIMessageChunk):
            # 输出格式：{"messages": [AIMessageChunk]}，确保状态合并
            yield {"messages": [chunk.message]}
            collected_chunks.append(chunk.message)

        """
            下面这种做法有问题，我们不能在一个步骤中去处理state的messages字段，因为这个字段只会在最后一行代码运行结束后，将最后一次yield的结果放到messages中
            即使最后一行代码将messages中新增了完整的Chunk，也会被最后一次yield的不完整内容给覆盖
        """
        # 将Chunk汇聚成一个AIMessage然后传递给下游
        # 默认情况下也会Merge，不过使用的是默认的Merge函数
        # merged_message = merge_chunks(collected_chunks)
        # state["messages"].append(merged_message)

    s = ""
    tool_calls = []
    for chk in collected_chunks:
        s += chk.content
        if chk.tool_calls:
            tool_calls = chk.tool_calls
    # print(f"s={s}")
    msg = AIMessage(content=s, additional_kwargs={'whole': True})
    if tool_calls:
        msg.tool_calls = tool_calls
    yield {"messages": [msg]}

def should_continue(state: AgentState):
    # print(f"in should_conintue ... state={state}")
    if not state["messages"]:
        raise ValueError("state should have messages.")
    # print(f"state has {len(state['messages'])} messages. state={state}")
    msg = state["messages"][-1]
    #print(f"under check message: {msg},  type={type(msg)}")
    if not isinstance(msg, AIMessage):
        raise ValueError(f"Type exception: type={type(msg)}, it should be AIMessage")
    tool_calls = msg.tool_calls
    return "tools" if tool_calls else END


def build_graph():

    tool_node = ToolNode(loaded_tools)

    builder = StateGraph(AgentState)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", tool_node)

    builder.set_entry_point("call_model")

    builder.add_conditional_edges(
        "call_model",
        should_continue
    )
    builder.add_edge("tools", "call_model")

    graph = builder.compile()
    return graph