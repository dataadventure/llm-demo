# mock_llm.py
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult, ChatGenerationChunk
import asyncio


class MockLLM(BaseChatModel):
    """一个符合LangChain接口的mock模型，可stream或非stream。"""

    model_name: str = "mock-llm"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        """非流式推理"""
        last = messages[-1]
        if isinstance(last, HumanMessage):
            if "1" in last.content:
                text = "ABC"
            elif "2" in last.content:
                text = "一二三"
            else:
                text = "模型回复：未知输入。"
        else:
            text = "无效输入。"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        """流式推理，分3个chunk输出"""
        last = messages[-1]
        if "1" in last.content:
            parts = ["A", "B", "C"]
        elif "2" in last.content:
            parts = ["一", "二", "三"]
        else:
            parts = ["未知", "输入", "。"]

        for part in parts:
            await asyncio.sleep(0.3)
            chunk = AIMessageChunk(content=part)
            yield ChatGenerationChunk(message=chunk)



    @property
    def _llm_type(self) -> str:
        return "mock"


if __name__ == "__main__":
    import asyncio

    async def test():
        llm = MockLLM()
        print(await llm.agenerate([[HumanMessage(content="1")]]))
        async for c in llm.astream([HumanMessage(content="1")]):
            print(c)

    asyncio.run(test())
