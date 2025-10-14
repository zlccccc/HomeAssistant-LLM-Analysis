# 调试修复说明

## 问题描述

代码在集成 MCP 工具后遇到异步调用问题。主要错误是：

1. **异步/同步混用问题**：`process_home_assistant_message` 被改为异步方法并使用 `await self.compiled_graph.ainvoke()`，但节点函数 `_generate_response` 最初是同步的，导致在已有事件循环中无法正确调用异步代码。

2. **消息格式转换问题**：Agent 返回的是 LangChain 消息对象，需要转换为字典格式。

3. **错误处理不完整**：缺少完善的异步错误处理机制。

## 修复内容

### 1. 将 `_generate_response` 改为异步方法

**修改前：**
```python
def _generate_response(self, state: State) -> Dict[str, Any]:
    # 同步方法，内部使用 asyncio.run_until_complete
```

**修改后：**
```python
async def _generate_response(self, state: State) -> Dict[str, Any]:
    # 完全异步的方法
    if state.execution_result:
        return {"response": state.execution_result, ...}
    else:
        result = await self._generate_response_async(state)
        return result
```

### 2. 重构异步逻辑

创建了独立的 `_generate_response_async` 方法处理 MCP 工具调用：

```python
async def _generate_response_async(self, state: State) -> Dict[str, Any]:
    """异步生成回复消息（内部实现）"""
    # 1. 转换消息格式为 LangChain 消息对象
    lc_messages = []
    lc_messages.append(SystemMessage(content=system_prompt))
    for msg in state.messages:
        if msg.get("role") == "user":
            lc_messages.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            lc_messages.append(AIMessage(content=msg.get("content", "")))
    
    # 2. 创建 MCP 客户端并获取工具
    client = MultiServerMCPClient({...})
    tools = await client.get_tools()
    
    # 3. 创建 ReAct Agent 并调用
    agent = self._create_react_agent(tools)
    agent_response = await agent.ainvoke({"messages": lc_messages})
    
    # 4. 转换响应格式
    formatted_msgs = []
    for msg in agent_response["messages"]:
        if isinstance(msg, HumanMessage):
            formatted_msgs.append({"role": "user", "content": msg.content})
        # ... 其他类型
    
    return {"response": response, "messages": formatted_msgs}
```

### 3. 添加错误处理

```python
try:
    result = await self._generate_response_async(state)
except Exception as e:
    logger.error(f"生成回复时出错: {str(e)}")
    import traceback
    traceback.print_exc()
    error_msg = f"抱歉，生成回复时出错: {str(e)}"
    return {"response": error_msg, "messages": state.messages + [{"role": "assistant", "content": error_msg}]}
```

### 4. 更新依赖

在 `requirements.txt` 中添加了 `nest-asyncio`（虽然当前实现中未使用，但保留以备后续需要）。

## 关键改进

1. **统一异步调用链**：
   - `ha_chat_assistant.py` → `await process_home_assistant_message()` 
   - → `await self.compiled_graph.ainvoke()` 
   - → `await _generate_response()` 
   - → `await _generate_response_async()`

2. **消息格式正确转换**：
   - 输入：字典格式 `{"role": "user", "content": "..."}`
   - Agent 内部：LangChain 消息对象 `HumanMessage`, `AIMessage` 等
   - 输出：字典格式

3. **完善的错误处理**：捕获并记录所有异常，返回友好的错误消息

## 测试建议

1. 确保安装所有依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 配置环境变量（`.env` 文件）：
   ```env
   HA_URL=http://localhost:8123
   HA_TOKEN=your_token
   HA_MCP_ENDPOINT=/api/mcp/sse
   QWEN_API_KEY=your_key
   QWEN_MODEL=qwen-plus
   QWEN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
   ```

3. 运行测试：
   ```bash
   python3 ha_chat_assistant.py
   ```

## 注意事项

- LangGraph 支持异步节点函数，只要使用 `ainvoke()` 调用图即可
- 在异步环境中避免使用 `asyncio.run()`，它会创建新的事件循环
- 消息格式转换是关键，确保 Agent 接收和返回的格式正确

