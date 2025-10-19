# agent_core.py
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from mock_llm import MockLLM


class AgentState(TypedDict):
    messages: Annotated[list, "add_messages"]


llm = MockLLM()


async def call_model_1(state: AgentState):
    print(f"before call_model_1, state={state}")
    """节点1：流式调用模型"""

    collected_chunks = []

    async for chunk in llm.astream([HumanMessage(content="1")]):
        yield {"messages": [chunk]}
        print(f"in call_model_1, state={state}")
        collected_chunks.append(chunk)

    s = ""
    for chk in collected_chunks:
        s += chk.content

    """
        1. Agent中的某个node和LLM交互，如果model输出是by token的Chunk，那么node结束时会只会将最后一个Chunk写到State的messages中，这是一个问题
        因为下游的node接收到的当前node的信息不完整了。
        2. 为了解决这个问题，需要在最后将所有的content信息拼接进行yield，这样下游node收到的信息是完整的
        3. 整个过程中，分块的chunk输出了，最后完整的content也输出了一次，那么Agent的客户端会收到冗余的信息，为了让客户端区分分块的和完整的，
        可以在完整的AIMessage中设置一些属性，便于客户端进行过滤
    """
    yield {"messages": [AIMessage(content=s, additional_kwargs={'whole':True})]}

    print(f"after call_model_1, state={state}")


async def call_model_2(state: AgentState):
    if state["messages"][-1].content!='ABC':
        raise ValueError("Content not complete.")
    print(f"before call_model_2, state={state}")
    """节点2：流式调用模型"""
    async for chunk in llm.astream([HumanMessage(content="2")]):
        yield {"messages": [chunk]}
    print(f"after call_model_2, state={state}")


def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("call_model_1", call_model_1)
    graph.add_node("call_model_2", call_model_2)
    graph.add_edge("call_model_1", "call_model_2")
    graph.add_edge("call_model_2", END)
    graph.set_entry_point("call_model_1")
    return graph.compile()
