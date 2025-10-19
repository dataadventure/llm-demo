# run_client.py
import asyncio
import argparse
from agent_core import build_agent


async def run_stream(agent):
    print("=== 🔹 Stream 输出 ===")
    async for chunk in agent.astream({"messages": []}):
        print("Chunk:", chunk)


async def run_event(agent):
    print("=== 🔹 Event 输出 ===")
    async for event in agent.astream_events({"messages": []}):
        print("Event:", event["event"], "| name:", event.get("name"), "| data:", event.get("data"))


async def main(mode: str):
    agent = build_agent()

    if mode == "stream":
        await run_stream(agent)
    elif mode == "event":
        await run_event(agent)
    else:
        print("❌ 请选择 mode 为 'stream' 或 'event'。")


if __name__ == "__main__":
    asyncio.run(main("event"))
