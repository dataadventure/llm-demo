import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, AsyncGenerator
import asyncio
from collections import defaultdict
from agent_core import init_mcp, build_graph, AgentState
from langchain_core.messages import BaseMessage
# 新增 CORS 支持
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MCP Agent Server")

# 配置 CORS - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境可指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 内存会话存储：session_id -> chat_history
session_store: Dict[str, List[BaseMessage]] = defaultdict(list)

# 请求模型
class AgentRequest(BaseModel):
    session_id: str
    query: str
    stream: bool = True  # 是否流式输出

# 流式响应生成器
async def stream_agent_response(session_id: str, query: str) -> AsyncGenerator[str, None]:
    await init_mcp()
    graph = build_graph()

    # 获取会话历史
    chat_history = session_store[session_id].copy()
    input_messages = chat_history + [{"role": "user", "content": query}]
    final_messages = None

    try:
        # 流式执行 LangGraph
        async for step in graph.astream({
            "messages": input_messages,
            "session_id": session_id
        }):
            # 模型推理步骤
            if "call_model" in step and step["call_model"] is not None:
                msg = step["call_model"]["messages"][0]
                yield f"""data: {json.dumps({
                    'type': 'model',
                    'content': msg.content,
                    'session_id': session_id
                })}\n\n"""
                chat_history.append(msg)
            # 工具调用步骤
            elif "tools" in step and step["tools"] is not None:
                msg = step["tools"]["messages"][0]
                yield f"""data: {json.dumps({
                    'type': 'tool',
                    'content': f'工具返回: {msg.content}',
                    'session_id': session_id
                })}\n\n"""
                chat_history.append(msg)

        # 获取最终结果
        final_state = await graph.ainvoke({
            "messages": input_messages,
            "session_id": session_id
        })
        final_msg = final_state["messages"][-1]
        final_messages = final_state["messages"]

        # 返回最终结果
        yield f"""data: {json.dumps({
            'type': 'result',
            'content': final_msg.content,
            'session_id': session_id
        })}\n\n"""

        # 标记流结束
        yield "data: [DONE]\n\n"
    finally:
        if final_messages:
            session_store[session_id] = final_messages

# Agent 接口
@app.post("/agent/invoke")
async def invoke_agent(request: AgentRequest):
    return StreamingResponse(
        stream_agent_response(request.session_id, request.query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

# 获取会话历史
@app.get("/agent/history/{session_id}")
async def get_history(session_id: str):
    return {
        "session_id": session_id,
        "history": [{"role": m.role, "content": m.content}
                    for m in session_store[session_id]]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent_server:app", host="0.0.0.0", port=8001, reload=True, workers=1)