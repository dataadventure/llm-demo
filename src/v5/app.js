// DOM 元素获取
const keywordsInput = document.getElementById('keywords');
const promptInput = document.getElementById('prompt');
const submitBtn = document.getElementById('submitBtn');
const resultBox = document.getElementById('resultBox');

// 会话 ID（生成唯一会话ID）
const SESSION_ID = 'frontend_session_' + new Date().getTime();
// Agent 服务地址（需与后端一致）
const AGENT_SERVER_URL = 'http://localhost:8001/agent/invoke';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    // 绑定事件监听
    submitBtn.addEventListener('click', handleSubmit);

    // 快捷键支持（Ctrl+Enter 提交）
    [keywordsInput, promptInput].forEach(input => {
        input.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                handleSubmit();
            }
        });
    });
});

/**
 * 处理提交事件
 */
async function handleSubmit() {
    const keywords = keywordsInput.value.trim();
    const prompt = promptInput.value.trim();

    // 输入验证
    if (!keywords && !prompt) {
        alert('请至少输入关键词或 Prompt');
        return;
    }

    // 构建查询内容（组合关键词和 Prompt）
    const query = `${keywords ? `关键词：${keywords}\n` : ''}${prompt ? `详细指令：${prompt}` : ''}`;

    // 重置结果框
    resultBox.innerHTML = '<div class="text-blue-600">正在请求 Agent 服务...<span class="loading-dot">.</span><span class="loading-dot">.</span><span class="loading-dot">.</span></div>';
    submitBtn.disabled = true;
    submitBtn.textContent = '查询中...';

    try {
        // 调用 Agent 流式 API
        await streamAgentResponse(query);
    } catch (error) {
        resultBox.innerHTML += `<div class="text-red-600 mt-2">❌ 交互出错：${error.message}</div>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '提交查询';
    }
}

/**
 * 流式获取 Agent 响应并显示
 * @param {string} query - 组合后的查询内容
 */
async function streamAgentResponse(query) {
    try {
        const response = await fetch(AGENT_SERVER_URL, {
            method: 'POST',
            mode: 'cors',  // 明确启用 CORS
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify({
                session_id: SESSION_ID,
                query: query,
                stream: true
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP 错误: ${response.status} ${response.statusText}`);
        }

        if (!response.body) {
            throw new Error('响应不包含流式数据');
        }

        // 处理流式响应
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            processBuffer(buffer);
        }

        // 处理剩余的缓冲区内容
        processBuffer(buffer);
    } catch (error) {
        // 更详细的错误分类
        if (error.message.includes('CORS')) {
            throw new Error('跨域访问被拒绝，请检查后端CORS配置');
        } else if (error.message.includes('405')) {
            throw new Error('请求方法不允许，请确认后端接口是否支持POST方法');
        } else {
            throw error;
        }
    }
}

/**
 * 处理缓冲区中的 SSE 事件
 * @param {string} buffer - 数据缓冲区
 */
function processBuffer(buffer) {
    const lines = buffer.split('\n');
    buffer = '';  // 重置缓冲区

    for (const line of lines) {
        if (line.startsWith('data:')) {
            const data = line.slice(5).trim();

            if (data === '[DONE]') {
                resultBox.innerHTML += '<div class="text-green-600 mt-2">✅ 交互完成</div>';
                resultBox.scrollTop = resultBox.scrollHeight;
                continue;
            }

            try {
                const chunk = JSON.parse(data);
                let displayContent = '';

                switch (chunk.type) {
                    case 'model':
                        displayContent = `<div class="mt-1"><span class="font-semibold text-blue-600">🤖 模型：</span>${chunk.content}</div>`;
                        break;
                    case 'tool':
                        displayContent = `<div class="mt-1"><span class="font-semibold text-orange-600">🔧 工具：</span>${chunk.content}</div>`;
                        break;
                    case 'result':
                        displayContent = `<div class="mt-2"><span class="font-semibold text-green-600">✅ 最终结果：</span>${chunk.content}</div>`;
                        break;
                    case 'error':
                        displayContent = `<div class="mt-1"><span class="font-semibold text-red-600">❌ 错误：</span>${chunk.content}</div>`;
                        break;
                }

                resultBox.innerHTML += displayContent;
                resultBox.scrollTop = resultBox.scrollHeight;

            } catch (parseError) {
                resultBox.innerHTML += `<div class="mt-1 text-red-600">❌ 数据解析错误：${parseError.message}</div>`;
            }
        } else if (line) {
            // 保留未处理的内容到缓冲区
            buffer += line + '\n';
        }
    }
}