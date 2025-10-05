from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger
import asyncio

class MCPClient:
    def __init__(self, llm=None):
        self.llm = llm
        self.mcp_client = None
        self.agent_with_tools = None
        
        """异步初始化MCP客户端和agent"""  
        try:
            self.mcp_client = MultiServerMCPClient(
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
            
            logger.info("正在连接MCP客户端...")
            tools = asyncio.run(self.mcp_client.get_tools())
            logger.info(f"成功获取到 {len(tools)} 个工具")
            
            # 过滤掉有问题的工具名称
            filtered_tools = []
            problematic_names = {"search", "fetch"}  # 这些名称可能与API冲突
            
            for tool in tools:
                if tool.name in problematic_names:
                    logger.warning(f"跳过可能冲突的工具: {tool.name}")
                    continue
                filtered_tools.append(tool)
            
            logger.info(f"使用 {len(filtered_tools)} 个工具创建agent...")
            
            self.agent_with_tools = create_react_agent(
                model=self.llm,
                tools=filtered_tools,
            )
            logger.info("MCP客户端初始化完成")
            
        except Exception as e:
            logger.error(f"MCP客户端初始化失败: {e}")
            # 创建无工具的备用agent
            self.agent_with_tools = create_react_agent(
                model=self.llm,
                tools=[],
            )
            logger.info("使用无工具的备用agent")
        
    async def main_with_context(self, messages: list):
        """执行查询，传入最近的消息历史"""
        logger.info("开始搜索论文...")
        result = ""
        
        # 构建完整的消息列表
        full_messages = [
            SystemMessage(content="你是一个zotero搜索助手。请根据以下消息历史进行搜索，不要做出跟用户需求无关的内容和推荐，并且用中文回复。")
        ] + messages
        
        try:
            async for chunk in self.agent_with_tools.astream(
                {"messages": full_messages},
                stream_mode="messages"
            ):
                result += chunk[0].content
                print(chunk[0].content, end='', flush=True)
        except Exception as e:
            logger.error(f"查询过程中出现错误: {e}")
            result = f"查询失败: {e}"
            
        return result
        
    def invoke_with_context(self, messages: list):
        """带上下文的同步接口"""
        return asyncio.run(self.main_with_context(messages))