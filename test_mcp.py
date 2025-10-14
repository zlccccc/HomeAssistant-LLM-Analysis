import os
import asyncio
import json
from datetime import datetime
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

    # 保存响应为 JSON 文件到 OUTPUT_DIR
    output_dir_name = os.getenv("OUTPUT_DIR", "output")
    output_dir = os.path.join(os.getcwd(), output_dir_name)
    os.makedirs(output_dir, exist_ok=True)
    filename = f"mcp_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=2, default=str)
    print(f"响应已保存到: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())