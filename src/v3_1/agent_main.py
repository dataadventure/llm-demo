import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, AsyncGenerator
import asyncio
from collections import defaultdict
from agent_core import init_mcp, build_graph, AgentState
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, AIMessageChunk

app = FastAPI(title="MCP Agent Server")

# 内存会话存储：session_id -> chat_history
session_store: Dict[str, List[BaseMessage]] = defaultdict(list)

# 请求模型
class AgentRequest(BaseModel):
    session_id: str
    query: str
    stream: bool = True  # 是否流式输出


async def main1(session_id: str, query: str):
    await init_mcp()
    graph = build_graph()

    chat_history = session_store[session_id].copy()
    id = str(uuid.uuid4())
    input_messages = chat_history + [HumanMessage(content=query, id=id)]
    async for event in graph.astream_events(
            {"messages": input_messages, "session_id": session_id},
            stream_mode="updates"
    ):


        if event["event"] == "on_chain_stream":  # call_model节点的每个chunk
            chunk = event["data"]
            if 'messages' in chunk['chunk']:
                kw = chunk['chunk'].get('additional_kwargs')
                # print(f"chunk={chunk['chunk']}   kw={kw}")
                msg = chunk['chunk']['messages'][0]
                # print(f'chunk={chunk}')
                if msg.additional_kwargs.get('whole') or not isinstance(msg, AIMessageChunk):
                    continue
                print(chunk['chunk']['messages'][0].content, end='', flush=True)
            elif 'tools' in chunk['chunk']:
                # print(chunk['chunk'])
                print('\n Tool calling result:')
                print(chunk['chunk']['tools']['messages'][0].content, flush=True)
        elif event["event"] == "on_chain_end":
            # print("✅ 节点结束:", event["name"])
            pass



if __name__ == "__main__":
    session_id = "abcdef0123456789"
    query = "上海天气怎么样?"
    asyncio.run(main1(session_id, query))