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
graph = None


# 启动时初始化
@app.on_event("startup")
async def startup_event():
    global graph
    await init_mcp()
    graph = build_graph()


# 请求模型
class AgentRequest(BaseModel):
    session_id: str
    query: str
    stream: bool = True  # 是否流式输出


# 【关键修正】流式响应生成器（返回合规的 SSE 格式）
async def stream_agent_response(session_id: str, query: str) -> AsyncGenerator[str, None]:
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
            # 模型推理步骤
            if "call_model" in step:
                msg = step["call_model"]["messages"][0]
                # SSE 格式：每个 chunk 用 "data:" 开头，换行分隔
                yield f"""data: {json.dumps({
                    'type': 'model',
                    'content': msg.content,
                    'session_id': session_id
                })}\n\n"""
                # 同步更新临时消息列表（用于最终历史存储）
                chat_history.append(msg)
                # 工具调用步骤
            elif "tools" in step:
                msg = step["tools"]["messages"][0]
                yield f"""data: {json.dumps({
                    'type': 'tool',
                    'content': f'工具返回: {msg.content}',
                    'session_id': session_id
                })}\n\n"""
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

        # 返回最终结果 chunk
        yield f"""data: {json.dumps({
            'type': 'result',
            'content': final_msg.content,
            'session_id': session_id
    
        })}\n\n"""

        # 3. 标记流结束（SSE 规范）
        yield "data: [DONE]\n\n"
    finally:
        # 确保会话历史被更新（即使过程出错）
        if final_messages:
            session_store[session_id] = final_messages


# 【关键修正】Agent 接口（使用合规的 StreamingResponse）
@app.post("/agent/invoke")
async def invoke_agent(request: AgentRequest):
    if not graph:
        raise HTTPException(status_code=500, detail="服务未初始化")

    if request.stream:
        return StreamingResponse(
            stream_agent_response(request.session_id, request.query),
            media_type="text/event-stream",  # 明确 SSE 媒体类型
            headers={
                "Cache-Control": "no-cache",  # 禁止缓存流式数据
                "Connection": "keep-alive"  # 保持长连接
            }
        )
    else:
        # 非流式处理（保持不变）
        chat_history = session_store[request.session_id]
        final_state = await graph.ainvoke({
            "messages": chat_history + [{"role": "user", "content": request.query}],
            "session_id": request.session_id
        })
        session_store[request.session_id] = final_state["messages"]
        return {
            "session_id": request.session_id,
            "result": final_state["messages"][-1].content
        }


# 获取会话历史（保持不变）
@app.get("/agent/history/{session_id}")
async def get_history(session_id: str):
    return {
        "session_id": session_id,
        "history": [{"role": m.role, "content": m.content}
                    for m in session_store[session_id]]
    }


if __name__ == "__main__":
    import uvicorn

    # 启动时指定 workers=1（流式处理不建议多进程，避免会话混乱）
    uvicorn.run("agent_server:app", host="0.0.0.0", port=8001, reload=True, workers=1)
