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

    # 创建记录结构，用于保存函数调用信息
    function_calls = {
        "get_tools": {
            "input": {
                "function": "client.get_tools()",
                "timestamp": datetime.now().isoformat()
            },
            "output": None
        },
        "tool_calls": {},
        "agent_invoke": {
            "input": {
                "function": "agent.ainvoke()",
                "user_query": "我感觉屋里面有点热啊？",
                "messages": [{"role": "user", "content": "我感觉屋里面有点热啊？"}],
                "timestamp": datetime.now().isoformat()
            },
            "output": None
        }
    }

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

    # 获取工具并记录输出
    tools = await client.get_tools()
    function_calls["get_tools"]["output"] = {
        "tools_count": len(tools),
        "tools_list": [{
            "name": tool.name,
            "description": tool.description
        } for tool in tools],
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"✓ 成功连接！获取到 {len(tools)} 个工具:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description} (args_schema: {tool.args_schema})")
        if tool.name == "GetLiveContext":
            # 记录工具调用
            function_calls["tool_calls"][tool.name] = {
                "input": {
                    "function": "tool.arun(tool_input={})",
                    "tool_input": {},
                    "timestamp": datetime.now().isoformat()
                },
                "output": None
            }
            
            # 调用该工具
            print(f"调用工具 {tool.name} ...")
            result = await tool.arun(tool_input={})
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    pass
            
            # 记录工具调用输出
            function_calls["tool_calls"][tool.name]["output"] = {
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 创建agent并调用
    agent = create_agent(llm_model, tools)
    response = await agent.ainvoke({"messages": [{"role": "user", "content": "我感觉屋里面有点热啊？"}]})
    
    # 记录agent调用输出
    function_calls["agent_invoke"]["output"] = {
        "response": response,
        "timestamp": datetime.now().isoformat()
    }
    
    print(response)

    # 保存完整数据到JSON文件
    output_dir_name = os.getenv("OUTPUT_DIR", "output")
    output_dir = os.path.join(os.getcwd(), output_dir_name)
    os.makedirs(output_dir, exist_ok=True)
    filename = f"mcp_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = os.path.join(output_dir, filename)

    
    # 保存到文件
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(function_calls, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"响应和函数调用记录已保存到: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())