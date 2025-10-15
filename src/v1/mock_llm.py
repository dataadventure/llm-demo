from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatResult, ChatGeneration


class MockLLM(BaseChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # 查找最新的用户消息和工具返回结果
        user_message = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

        if not user_message:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="请输入问题"))])

        content = user_message.content
        tool_calls = []

        # 只有当没有工具返回结果时，才生成工具调用（避免循环调用）
        if not tool_messages and ("天气" in content or "weather" in content.lower()):
            city = "上海"
            tool_calls.append({
                "name": "get_weather",
                "args": {"location": city},
                "id": "tool_call_1"
            })
            # 工具调用阶段的回复
            response_content = "正在查询天气信息..."
        else:
            # 工具返回结果已存在，生成最终回答（终止循环）
            response_content = f"根据查询，{tool_messages[-1].content}" if tool_messages else "未找到天气信息"

        message = AIMessage(
            content=response_content,
            tool_calls=tool_calls
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self):
        return "mock-llm"