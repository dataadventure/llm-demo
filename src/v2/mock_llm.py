from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.tools import BaseTool


class MockLLM(BaseChatModel):
    # 存储通过bind_tools绑定的工具列表
    tools: list[BaseTool] = []

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # 提取最新用户消息和工具返回结果
        user_message = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

        if not user_message:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="请输入问题"))])

        content = user_message.content
        tool_calls = []

        # 关键逻辑：如果有绑定的工具且未收到工具返回结果，则调用第一个工具
        if self.tools and not tool_messages:
            # 不硬编码工具名称，直接取绑定工具列表的第一个
            first_tool = self.tools[0]
            # 模拟提取工具所需参数（这里以location为例，实际可根据工具schema动态处理）
            if "天气" in content or "weather" in content.lower():
                tool_calls.append({
                    "name": first_tool.name,  # 使用工具的名称
                    "args": {"location": "上海"},  # 工具参数（可根据工具schema动态生成）
                    "id": "tool_call_1"
                })
                response_content = f"正在调用{first_tool.name}工具查询信息..."
            else:
                response_content = f"你的问题我无法回答..."
        else:
            # 工具调用完成，返回最终结果
            response_content = f"查询结果：{tool_messages[-1].content}" if tool_messages else "未找到信息"

        message = AIMessage(
            content=response_content,
            tool_calls=tool_calls
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        return "mock-llm"

    # 实现bind_tools方法，用于将工具绑定到模型
    def bind_tools(self, tools: list[BaseTool]):
        new_instance = MockLLM()
        new_instance.tools = tools  # 存储绑定的工具
        return new_instance