import time
import asyncio
from typing import Iterator, AsyncIterator, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class MockLLM(BaseChatModel):
    """
    一个模拟的 LLM：
    - 返回 ChatResult（符合标准格式）
    - 支持同步 stream() 和异步 astream()
    - 每隔 0.1 秒输出一个字符
    """

    def _build_message(self, text: str) -> AIMessage:
        """构造一条 AIMessage，可以扩展 tool_calls 字段"""
        return AIMessage(content=text)

    # ------------------------
    # 1. 同步流式输出
    # ------------------------
    def stream(self, prompt: str) -> Iterator[ChatResult]:
        message = "你好，我是Mock LLM，我会帮助你。"
        content = ""
        for ch in message:
            time.sleep(0.1)
            content += ch
            yield ChatResult(
                generations=[ChatGeneration(message=self._build_message(content))]
            )

    # ------------------------
    # 2. 异步流式输出
    # ------------------------
    async def astream(self, prompt: str) -> AsyncIterator[ChatResult]:
        message = "你好，我是Mock LLM，我会帮助你。"
        content = ""
        for ch in message:
            await asyncio.sleep(0.1)
            content += ch
            yield ChatResult(
                generations=[ChatGeneration(message=self._build_message(content))]
            )

    # ------------------------
    # 3. 标准生成接口（非流式）
    # ------------------------
    def _generate(
        self, messages: List[BaseMessage], stop: Optional[List[str]] = None
    ) -> ChatResult:
        text = "你好，我是Mock LLM，我会帮助你。"
        return ChatResult(
            generations=[ChatGeneration(message=self._build_message(text))]
        )

    async def _agenerate(
        self, messages: List[BaseMessage], stop: Optional[List[str]] = None
    ) -> ChatResult:
        text = "你好，我是Mock LLM，我会帮助你。"
        return ChatResult(
            generations=[ChatGeneration(message=self._build_message(text))]
        )

    @property
    def _llm_type(self) -> str:
        return "mock-minimal-stream-llm"