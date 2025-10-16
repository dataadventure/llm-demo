import asyncio

from src.v00.mock_llm import MockLLM

llm = MockLLM()

def run_sync_client():

    for chunk in llm.stream("你好"):
        msg = chunk.generations[0].message
        print("\r" + msg.content, end="", flush=False)

    print(">>> 开始同步流式输出:")
    for chunk in llm.stream("你好"):
        msg = chunk.generations[0].message
        print("\r" + msg.content, end="", flush=False)

    print("\n>>> 同步输出结束。")


async def run_async_client():

    print(">>> 开始异步流式输出:")
    async for chunk in llm.astream("你好"):
        msg = chunk.generations[0].message
        print("\r" + msg.content, end="", flush=True)
    print("\n>>> 异步输出结束。")


if __name__ == '__main__':
    run_sync_client()
    asyncio.run(run_async_client())