import os
import asyncio
import json
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

# 禁用代理（避免 localhost 连接通过代理）
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('all_proxy', None)
os.environ.pop('ALL_PROXY', None)

# 加载环境变量
load_dotenv()

llm_model = ChatOpenAI(model=os.getenv("QWEN_MODEL"),
                  api_key=os.getenv("QWEN_API_KEY"),
                  base_url=os.getenv("QWEN_API_BASE"))

async def main():
    # 测试不同的端点配置
    ha_url = os.getenv("HA_URL", "http://localhost:8123")
    ha_token = os.getenv("HA_TOKEN")
    ha_mcp_endpoint = os.getenv("HA_MCP_ENDPOINT")

    client = MultiServerMCPClient(
        {
            "homeassistant": {
                "transport": "sse",
                "url": f"{ha_url}{ha_mcp_endpoint}",
                "headers": {
                    "Authorization": f"Bearer {ha_token}",
                    "Content-Type": "application/json"
                },
            }
        }
    )
    tools = await client.get_tools()
    print(f"✓ 成功连接！获取到 {len(tools)} 个工具:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description} (args_schema: {tool.args_schema})")
        if tool.name == "GetLiveContext":
            # 调用该工具并以utf-8编码输出结果
            print(f"调用工具 {tool.name} ...")
            result = await tool.arun(tool_input={})
            if isinstance(result, str):
                result = json.loads(result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    
    agent = create_agent(llm_model, tools)
    response = await agent.ainvoke({"messages": [{"role": "user", "content": "我感觉屋里面有点热啊？"}]})
    print(response)

if __name__ == "__main__":
    asyncio.run(main())