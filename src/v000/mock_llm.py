import time
import asyncio
from typing import Iterator, AsyncIterator, List, Optional

# 根据你的环境调整导入路径：下面用 langchain_core 做示例
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult, ChatGeneration

class MockLLM(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "mock-minimal-stream-llm"

    # 同步流：每次产出增量 chunk（使用 dict 方式，兼容 Pydantic 校验）
    def stream(self, prompt: str) -> Iterator[ChatGenerationChunk]:
        message = "你好，我是Mock LLM，我会帮助你。"
        for ch in message:
            time.sleep(0.1)
            # 把 AIMessage 转成 dict，Pydantic 会把 dict 转为 BaseMessageChunk
            yield ChatGenerationChunk(message=AIMessage(content=ch).dict())

    # 异步流
    async def astream(self, prompt: str) -> AsyncIterator[ChatGenerationChunk]:
        message = "你好，我是Mock LLM，我会帮助你。"
        for ch in message:
            await asyncio.sleep(0.1)
            yield ChatGenerationChunk(message=AIMessage(content=ch).dict())

    # 非流式最终生成（返回 ChatResult）
    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None) -> ChatResult:
        full_text = "你好，我是Mock LLM，我会帮助你。"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=full_text))])

    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None) -> ChatResult:
        full_text = "你好，我是Mock LLM，我会帮助你。"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=full_text))])
