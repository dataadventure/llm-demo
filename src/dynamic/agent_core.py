import asyncio
import random
import time

from langgraph.graph import StateGraph, MessagesState


class AgentState(MessagesState):
    result: int


def build_graph(step_count: int):
    builder = StateGraph(AgentState)
    steps = []
    for step_index in range(1, step_count+1):
        def wrapper(step_index: int):
            def run(state: AgentState):
                last_result = state["result"]
                x: int = random.randint(0, 10)
                time.sleep(1)
                return {"messages": [f"step_{step_index} finished with {x}"], "result": x+last_result}
            return run
        run =wrapper(step_index)
        steps.append(run)
    for i in range(step_count):
        builder.add_node(f"step_{i+1}", steps[i])

    builder.set_entry_point("step_1")
    for i in range(step_count-1):
        builder.add_edge(f"step_{i+1}", f"step_{i+2}")

    graph = builder.compile()
    return graph


async def run_agent():
    step_count = 7
    graph = build_graph(step_count)
    async for step in graph.astream({"messages": [{"role": "user", "content": ""}], "result": 0}):
        print(step)


if __name__ == '__main__':
    asyncio.run(run_agent())