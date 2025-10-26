// DOM 元素获取（不变）
const keywordsInput = document.getElementById('keywords');
const promptInput = document.getElementById('prompt');
const submitBtn = document.getElementById('submitBtn');
const resultBox = document.getElementById('resultBox');

// 会话 ID 和服务地址（不变）
const SESSION_ID = 'frontend_session_' + new Date().getTime();
const AGENT_SERVER_URL = 'http://localhost:8001/agent/invoke';

// 全局状态（不变）
let currentTypingTask = null;
let currentSegmentId = '';

// 页面初始化（不变）
document.addEventListener('DOMContentLoaded', () => {
    submitBtn.addEventListener('click', handleSubmit);
    [keywordsInput, promptInput].forEach(input => {
        input.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                handleSubmit();
            }
        });
    });
});

/**
 * 处理提交事件（不变）
 */
async function handleSubmit() {
    const keywords = keywordsInput.value.trim();
    const prompt = promptInput.value.trim();

    if (!keywords && !prompt) {
        alert('请至少输入关键词或 Prompt');
        return;
    }

    const query = `${keywords ? `关键词：${keywords}\n` : ''}${prompt ? `详细指令：${prompt}` : ''}`;

    clearAllTypingTasks();
    resultBox.innerHTML = '<div class="text-blue-600">正在请求 Agent 服务...<span class="loading-dot">.</span><span class="loading-dot">.</span><span class="loading-dot">.</span></div>';
    submitBtn.disabled = true;
    submitBtn.textContent = '查询中...';

    try {
        await streamAgentResponse(query);
    } catch (error) {
        await createTypingContainer('error', error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '提交查询';
    }
}

/**
 * 流式获取响应（不变）
 */
async function streamAgentResponse(query) {
    try {
        const response = await fetch(AGENT_SERVER_URL, {
            method: 'POST',
            mode: 'cors',
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

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            buffer = await processBuffer(buffer);
        }

        if (buffer.trim()) {
            await processBuffer(buffer);
        }

    } catch (error) {
        let errorMsg = error.message;
        if (errorMsg.includes('CORS')) errorMsg = '跨域访问被拒绝，请检查后端CORS配置';
        else if (errorMsg.includes('405')) errorMsg = '请求方法不允许，请确认后端接口支持POST';
        else if (errorMsg.includes('404')) errorMsg = 'Agent服务地址不存在，请检查后端地址';
        throw new Error(errorMsg);
    }
}

/**
 * 处理缓冲区事件（不变）
 */
async function processBuffer(buffer) {
    const lines = buffer.split('\n');
    let remaining = '';

    for (const line of lines) {
        if (line.startsWith('data:')) {
            const data = line.slice(5).trim();

            if (data === '[DONE]') {
                await waitForCurrentTypingDone();
                resultBox.innerHTML += '<div class="text-green-600 mt-2">✅ 交互完成</div>';
                resultBox.scrollTop = resultBox.scrollHeight;
                continue;
            }

            try {
                const chunk = JSON.parse(data);
                // 修复1：修剪content的前导/尾随空格，避免顶格空格
                const content = (chunk.content || chunk.result || chunk.tool_result || chunk.msg || '（无内容）').trimStart();
                const type = chunk.type || 'unknown';

                await waitForCurrentTypingDone();
                await createTypingContainer(type, content);

            } catch (parseError) {
                await waitForCurrentTypingDone();
                await createTypingContainer('error', `数据解析错误：${parseError.message}`);
            }
        } else if (line) {
            remaining += line + '\n';
        }
    }

    return remaining;
}

/**
 * 创建打字段落（核心修复：清除HTML嵌套空格）
 */
function createTypingContainer(type, content) {
    return new Promise((resolve) => {
        const prefixMap = {
            model: '<span class="font-semibold text-blue-600">🤖 模型：</span>',
            tool: '<span class="font-semibold text-orange-600">🔧 工具：</span>',
            result: '<span class="font-semibold text-green-600">✅ 最终结果：</span>',
            error: '<span class="font-semibold text-red-600">❌ 错误：</span>',
            unknown: '<span class="font-semibold text-gray-600">ℹ️ 信息：</span>'
        };
        const prefix = prefixMap[type] || prefixMap.unknown;

        currentSegmentId = `typing-segment-${Date.now()}`;
        const segmentContainer = document.createElement('div');
        segmentContainer.className = 'mt-1'; // 仅保留段落间距，无额外内边距
        // 修复2：HTML不换行不缩进，避免解析出多余空格
        segmentContainer.innerHTML = `${prefix}<span class="typing-container" id="${currentSegmentId}"></span>`;
        resultBox.appendChild(segmentContainer);
        resultBox.scrollTop = resultBox.scrollHeight;

        const contentElement = document.getElementById(currentSegmentId);
        let charIndex = 0;
        const typeSpeed = 30;

        clearAllTypingTasks();

        function typeNextChar() {
            if (charIndex < content.length) {
                const currentChar = content[charIndex].replace('\n', '<br>');
                contentElement.innerHTML += currentChar;
                charIndex++;
                resultBox.scrollTop = resultBox.scrollHeight;
                currentTypingTask = setTimeout(typeNextChar, typeSpeed);
            } else {
                clearAllTypingTasks();
                resolve();
            }
        }

        typeNextChar();
    });
}

/**
 * 等待打字完成（不变）
 */
function waitForCurrentTypingDone() {
    return new Promise((resolve) => {
        if (!currentTypingTask) {
            resolve();
            return;
        }

        const checkTimer = setInterval(() => {
            if (!currentTypingTask) {
                clearInterval(checkTimer);
                resolve();
            }
        }, 20);
    });
}

/**
 * 清除打字任务（不变）
 */
function clearAllTypingTasks() {
    if (currentTypingTask) {
        clearTimeout(currentTypingTask);
        currentTypingTask = null;
    }
    currentSegmentId = '';
}