import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, AsyncGenerator
import asyncio
from collections import defaultdict
from agent_core import init_mcp, build_graph, AgentState
from langchain_core.messages import BaseMessage

app = FastAPI(title="MCP Agent Server")

# 内存会话存储：session_id -> chat_history
session_store: Dict[str, List[BaseMessage]] = defaultdict(list)

# 请求模型
class AgentRequest(BaseModel):
    session_id: str
    query: str
    stream: bool = True  # 是否流式输出


async def main2(session_id: str, query: str):
    await init_mcp()
    graph = build_graph()

    # 获取会话历史
    chat_history = session_store[session_id].copy()
    input_messages = chat_history + [{"role": "user", "content": query}]
    final_messages = None

    try:
        # 1. 流式执行 LangGraph，实时返回中间步骤
        async for step in graph.astream({
            "messages": input_messages,
            "session_id": session_id
        }):
            print(step)
            # 模型推理步骤
            if "call_model" in step:
                msg = step["call_model"]["messages"][0]

                # 同步更新临时消息列表（用于最终历史存储）
                chat_history.append(msg)
                # 工具调用步骤
            elif "tools" in step:
                msg = step["tools"]["messages"][0]

                chat_history.append(msg)

        # 2. 获取最终结果并返回
        final_state = await graph.ainvoke(
            {
                "messages": input_messages,
                "session_id": session_id
            }
        )
        final_msg = final_state["messages"][-1]
        final_messages = final_state["messages"]  # 用于更新会话历史


    finally:
        # 确保会话历史被更新（即使过程出错）
        if final_messages:
            session_store[session_id] = final_messages

async def main1(session_id: str, query: str):

    await init_mcp()
    graph = build_graph()
    chat_history = session_store[session_id]
    final_state = await graph.ainvoke({
        "messages": chat_history + [{"role": "user", "content": query}],
        "session_id": session_id
    })
    session_store[session_id] = final_state["messages"]
    print(final_state)
    return {
        "session_id": session_id,
        "result": final_state["messages"][-1].content
    }


if __name__ == "__main__":
    session_id = "abcdef0123456789"
    query = "上海天气怎么样?"
    asyncio.run(main2(session_id, query))