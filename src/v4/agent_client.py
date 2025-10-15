import aiohttp
import asyncio
import json
from typing import AsyncGenerator, Dict


class AgentClient:
    def __init__(self, server_url: str = "http://localhost:8001"):
        self.server_url = server_url

    async def invoke_stream(self, session_id: str, query: str, stream: bool) -> AsyncGenerator[Dict, None]:
        """流式调用Agent（适配 SSE 格式）"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/agent/invoke",
                json={"session_id": session_id, "query": query, "stream": stream},
                timeout=None,  # 禁用超时（适应长耗时工具调用）
                headers={"Accept": "text/event-stream"}  # 告诉服务端需要 SSE 格式
            ) as resp:
                if resp.status != 200:
                    yield {
                        "type": "error",
                        "content": f"请求失败，状态码：{resp.status}",
                        "session_id": session_id
                    }
                    return

                # 逐行读取 SSE 数据
                async for line in resp.content:
                    line_str = line.strip().decode("utf-8")
                    if not line_str:
                        continue  # 忽略空行

                    # 解析 SSE 格式（只处理 "data:" 开头的行）
                    if line_str.startswith("data:"):
                        data = line_str[len("data:"):].strip()
                        if data == "[DONE]":
                            break  # 流结束标记

                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            yield {
                                "type": "error",
                                "content": f"解析流式数据失败：{data}",
                                "session_id": session_id
                            }

    async def invoke(self, session_id: str, query: str) -> Dict:
        """非流式调用Agent（保持不变）"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/agent/invoke",
                json={"session_id": session_id, "query": query, "stream": False}
            ) as resp:
                if resp.status != 200:
                    return {
                        "error": f"请求失败，状态码：{resp.status}",
                        "session_id": session_id
                    }
                return await resp.json()

    async def get_history(self, session_id: str) -> Dict:
        """获取会话历史（保持不变）"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.server_url}/agent/history/{session_id}"
            ) as resp:
                if resp.status != 200:
                    return {
                        "error": f"获取历史失败，状态码：{resp.status}",
                        "session_id": session_id
                    }
                return await resp.json()


# 示例使用（保持不变）
async def main():
    client = AgentClient()
    session_id = "test_session_123"

    print("===== 流式调用结果 =====")
    async for chunk in client.invoke_stream(session_id, "今天天气怎么样？", True):
        if chunk["type"] == "model":
            print(f"🤖 模型推理：{chunk['content']}", flush=True)
        elif chunk["type"] == "tool":
            print(f"🔧 {chunk['content']}")
        elif chunk["type"] == "result":
            print(f"✅ 最终回答：{chunk['content']}", flush=True)
        else:
            print(f"❌ {chunk['content']}", flush=True)

    print("\n===== 会话历史 =====")
    history = await client.get_history(session_id)
    if "error" in history:
        print(history["error"])
    else:
        for idx, msg in enumerate(history["history"], 1):
            role = "用户" if msg["role"] == "user" else "AI" if msg["role"] == "ai" else "工具"
            print(f"{idx}. {role}：{msg['content']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise