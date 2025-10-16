import time
import asyncio
from typing import Iterator, AsyncIterator
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage


class MockLLM(BaseChatModel):
    """一个模拟的 LLM，会逐字流式输出文本。"""

    def _generate_output(self, text: str) -> AIMessage:
        return AIMessage(content=text)

    # 同步流式输出
    def stream(self, prompt: str) -> Iterator[BaseMessage]:
        message = "你好，我是Mock LLM，我会帮助你。"
        for ch in message:
            time.sleep(0.1)
            yield self._generate_output(ch)

    # 异步流式输出
    async def astream(self, prompt: str) -> AsyncIterator[BaseMessage]:
        message = "你好，我是Mock LLM，我会帮助你。"
        for ch in message:
            await asyncio.sleep(0.1)
            yield self._generate_output(ch)



    # 这两个是BaseChatModel要求必须实现的接口
    def _generate(self, messages, stop=None):
        return self._generate_output("你好，我是Mock LLM，我会帮助你。")

    async def _agenerate(self, messages, stop=None):
        return self._generate_output("你好，我是Mock LLM，我会帮助你。")

    @property
    def _llm_type(self) -> str:
        return "mock-minimal-stream-llm"
