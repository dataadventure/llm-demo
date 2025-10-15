# mcp_server.py
from mcp.server.fastmcp import FastMCP

# 初始化MCP服务器
mcp = FastMCP("WeatherServer")

# 定义天气工具
@mcp.tool()
async def get_weather(location: str) -> str:
    """获取指定城市的天气信息"""
    # 简单mock返回结果
    return f"Mock天气: {location} 晴朗，25°C"

if __name__ == "__main__":
    # 启动streamable-http服务器，默认端口8000
    mcp.run(transport="streamable-http")