# langgraph_agent.py
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from mock_llm import MockLLM


# 定义状态结构
class AgentState(MessagesState):
    pass


async def main():
    # 1. 连接MCP服务器，加载工具
    client = MultiServerMCPClient({
        "weather": {
            "url": "http://localhost:8000/mcp",  # 对应MCP服务器地址
            "transport": "streamable_http",
        }
    })
    tools = await client.get_tools()
    print("加载的工具:", [tool.name for tool in tools])

    # 2. 初始化Mock LLM
    mock_llm = MockLLM().bind_tools(tools)

    # 3. 定义模型节点：调用Mock LLM生成工具调用
    async def call_model(state: AgentState):
        response = await mock_llm.ainvoke(state["messages"])
        return {"messages": [response]}

    # 4. 定义工具节点：执行工具调用
    tool_node = ToolNode(tools)

    # 5. 定义条件边：判断是否需要调用工具
    def should_continue(state: AgentState):
        last_msg = state["messages"][-1]
        if last_msg.tool_calls:
            return "tools"  # 有工具调用，进入工具节点
        return END  # 无工具调用，结束流程

    # 6. 构建图
    builder = StateGraph(AgentState)
    builder.add_node("call_model", call_model)  # 模型节点
    builder.add_node("tools", tool_node)  # 工具节点
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges("call_model", should_continue)
    builder.add_edge("tools", "call_model")  # 工具调用后返回模型节点

    # 7. 编译图并测试
    graph = builder.compile()
    result = await graph.ainvoke({
        # "messages": [{"role": "user", "content": "今天天气怎么样？"}]
        "messages": [{"role": "user", "content": "今天心情怎么样"}]
    })

    # 打印最终结果
    print("\n最终输出:", result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())