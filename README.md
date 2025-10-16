演示stream或astream使用不同的消息类型的效果
v0: AsyncIterator[BaseMessage]
v00: AsyncIterator[ChatResult]
v000: AsyncIterator[ChatGenerationChunk]

v3_1: 从agent--->client的stream未调通，Tool也无法识别state中的消息