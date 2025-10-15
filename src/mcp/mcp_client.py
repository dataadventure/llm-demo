# mcp_client_test.py
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool  # 引入Tool类型定义

async def test_mcp_server():
    # 配置MCP服务器连接参数
    server_params = {
        "url": "http://localhost:8000/mcp",  # 对应MCP服务器地址
        "headers": {}  # 如需认证可添加headers
    }

    # 建立与MCP服务器的连接
    async with streamablehttp_client(**server_params) as (read, write, _):
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()
            print("已成功连接到MCP服务器")

            # 1. 列出服务器提供的所有工具
            tools_response = await session.list_tools()
            # 解析工具列表（兼容不同版本的返回格式）
            tools = []
            if hasattr(tools_response, 'tools'):
                tools = [t[0] if isinstance(t, tuple) else t for t in tools_response.tools]
            print("\n服务器提供的工具:")
            for tool in tools:
                if isinstance(tool, Tool):
                    print(f"- 工具名称: {tool.name}, 描述: {tool.description}")
                else:
                    print(f"- 工具信息: {tool} (格式不兼容)")

            # 2. 调用get_weather工具（使用arguments参数传递参数）
            target_tool = next((t for t in tools if isinstance(t, Tool) and t.name == "get_weather"), None)
            if target_tool:
                print("\n开始调用get_weather工具...")
                # 关键修正：将parameters改为arguments
                response = await session.call_tool(
                    name="get_weather",
                    arguments={"location": "上海"}  # MCP协议标准参数名是arguments
                )
                # 解析返回结果
                if hasattr(response, 'content') and response.content:
                    result = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
                    print(f"工具返回结果: {result}")
                else:
                    print(f"工具返回结果: {response}")
            else:
                print("\n错误: 服务器未提供get_weather工具")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())