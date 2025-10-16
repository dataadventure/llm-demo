from src.v0.mock_llm import MockLLM

llm = MockLLM()

for chunk in llm.stream("帮我写一句问候语"):
    print(chunk.content, end="", flush=True)
print()

import asyncio

async def main():
    async for chunk in llm.astream("帮我写一句问候语"):
        print(chunk.content, end="", flush=True)

asyncio.run(main())
