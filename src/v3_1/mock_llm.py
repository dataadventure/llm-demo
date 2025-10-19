import time
import asyncio
import uuid
from typing import Iterator, AsyncIterator, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, AIMessageChunk
from langchain_core.outputs import (
    ChatResult,
    ChatGeneration,
    ChatGenerationChunk,
)
from langchain_core.tools import BaseTool


class MockLLM(BaseChatModel):
    """支持工具调用 + 流式输出的 Mock LLM"""

    tools: list[BaseTool] = []

    # --------------------------------------
    # 1️⃣ 同步生成（旧逻辑保持）
    # --------------------------------------
    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        user_message = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

        if not user_message:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="请输入问题"))])

        content = user_message.content
        tool_calls = []
        response_content = ""

        if self.tools and not tool_messages:
            first_tool = self.tools[0]
            if "天气" in content or "weather" in content.lower():
                tool_calls.append({
                    "name": first_tool.name,
                    "args": {"location": "上海"},
                    "id": "tool_call_1"
                })
                time.sleep(0.1)
                response_content = f"将要调用{first_tool.name}工具查询信息..."
            else:
                time.sleep(0.1)
                response_content = f"你的问题我无法回答..."
        else:
            response_content = f"查询结果：{tool_messages[-1].content}" if tool_messages else "未找到信息"

        message = AIMessage(content=response_content, tool_calls=tool_calls)
        return ChatResult(generations=[ChatGeneration(message=message)])

    # --------------------------------------
    # 2️⃣ stream：同步流式输出
    # --------------------------------------
    def stream(self, messages, **kwargs) -> Iterator[ChatGenerationChunk]:
        """同步流式输出：逐字返回 ChatGenerationChunk"""
        result = self._generate(messages, **kwargs)
        full_text = result.generations[0].message.content
        for ch in full_text:
            time.sleep(0.1)
            yield ChatGenerationChunk(message=AIMessageChunk(content=ch))

    # --------------------------------------
    # 3️⃣ astream：异步流式输出
    # --------------------------------------
    async def astream(self, messages, **kwargs) -> AsyncIterator[ChatGenerationChunk]:

        for ch in "Thinking ...\n":
            await asyncio.sleep(0.1)
            yield ChatGenerationChunk(message=AIMessageChunk(content=ch))

        """异步流式输出：逐字返回 ChatGenerationChunk"""
        result = self._generate(messages, **kwargs)
        full_text = result.generations[0].message.content
        tmp = None
        for ch in full_text:
            await asyncio.sleep(0.1)
            tool_calls = result.generations[0].message.tool_calls
            # 以Chunk的形式返回消息，Agent的State会自动将一次交互的Chunk merge成一个AIMessage，
            # 默认的merge逻辑是取最后一个，这个merge其实是一个reduce函数，逻辑大致是：(a, b)->b
            # 但是我们可以自定义merge逻辑，例如将content拼接，tool_calls只保留最后一个Chunk的tool_calls
            yield ChatGenerationChunk(message=AIMessageChunk(content=ch))
            if  tool_calls:
                tmp = tool_calls
        if tmp:
            yield ChatGenerationChunk(message=AIMessageChunk(content="", tool_calls=tmp))
    # --------------------------------------
    # 4️⃣ 类型标识 + 工具绑定
    # --------------------------------------
    @property
    def _llm_type(self) -> str:
        return "mock-minimal-stream-llm"

    def bind_tools(self, tools: list[BaseTool]):
        new_instance = MockLLM()
        new_instance.tools = tools
        return new_instance
