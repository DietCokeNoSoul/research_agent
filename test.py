import os
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

async def setup_mcp_client():
    """异步设置MCP客户端和工具"""
    mcp_client = MultiServerMCPClient(
        {
            "zotero": {
                "command": "C:\\Users\\71949\\.local\\bin\\zotero-mcp.EXE",
                "transport": "stdio",
                "args": ["serve", "--transport", "stdio"],
                "env": {
                    "ZOTERO_LOCAL": "true"
                }
            }
        }
    )
    
    try:
        logger.info("正在连接MCP客户端...")
        tools = await mcp_client.get_tools()
        logger.info(f"成功连接，获取到 {len(tools)} 个工具")
        
        # 过滤掉有问题的工具名称
        filtered_tools = []
        problematic_names = {"search", "fetch"}  # 这些名称可能与API冲突
        
        for tool in tools:
            if tool.name in problematic_names:
                logger.warning(f"跳过可能冲突的工具: {tool.name}")
                continue
            filtered_tools.append(tool)
            logger.info(f"Loaded tool: {tool.name} - {tool.description}")

        logger.info(f"使用 {len(filtered_tools)} 个工具创建agent...")
        
        agent_with_tools = create_react_agent(
            model=ChatOpenAI(
                model="qwen3-next-80b-a3b-instruct",
                openai_api_key=os.getenv("QWEN_API_KEY"),
                openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            tools=filtered_tools,
        )
        
        return agent_with_tools, mcp_client
        
    except Exception as e:
        logger.error(f"MCP客户端连接失败: {e}")
        # 如果MCP连接失败，创建一个没有工具的agent
        logger.info("创建无工具的备用agent...")
        agent_with_tools = create_react_agent(
            model=ChatOpenAI(
                model="qwen3-next-80b-a3b-instruct",
                openai_api_key=os.getenv("QWEN_API_KEY"),
                openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            tools=[],
        )
        return agent_with_tools, None

logger.info("Starting agent with tools...")

async def main():
    print("开始搜索论文...")
    print("=" * 50)
    
    # 设置MCP客户端和agent
    agent_with_tools, mcp_client = await setup_mcp_client()
    
    try:
        async for chunk in agent_with_tools.astream(
            {"messages": [
                SystemMessage("你是一个论文搜索助手，帮助用户在Zotero论文库中查找相关的学术文章。"),
                HumanMessage("我想找一篇文章，我记得标题是带有multi-scale neighbor的")]
            },
            stream_mode="messages"
        ):
            print(chunk[0].content, end='', flush=True)
    except Exception as e:
        logger.error(f"查询过程中出现错误: {e}")
        print(f"\n查询失败: {e}")
    finally:
        # 清理资源
        if mcp_client:
            try:
                await mcp_client.close()
                logger.info("MCP客户端连接已关闭")
            except Exception as e:
                logger.warning(f"关闭MCP客户端时出现警告: {e}")

if __name__ == "__main__":
    asyncio.run(main())
