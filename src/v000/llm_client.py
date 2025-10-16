from src.v000.mock_llm import MockLLM


def run_sync_client():
    llm = MockLLM()
    print(">>> 开始同步流式输出:")
    buf = ""
    for chunk in llm.stream("你好"):
        # chunk.message 现在是一个 dict（被 Pydantic 转回了 chunk 实例），但通常可以安全访问：
        # 取增量文本：如果是 dict，就用 chunk['message']['content']，如果是对象则用 .message.content
        # 为兼容两种可能，我们做个小判断：
        content_piece = None
        # 尝试属性访问
        if hasattr(chunk, "message") and getattr(chunk.message, "content", None) is not None:
            content_piece = chunk.message.content
        else:
            # 当 chunk.message 是 dict（在某些版本下），使用 dict 方式
            try:
                content_piece = chunk.message.get("content")
            except Exception:
                content_piece = str(chunk)  # 兜底
        buf += content_piece or ""
        print(content_piece or "", end="", flush=True)

    print("\n>>> 最终内容:", buf)


if __name__ == '__main__':
    run_sync_client()