"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations

import os
import time
import uuid
import threading
import asyncio
from loguru import logger

from langgraph.runtime import Runtime
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
# 用LangGraph studio不需要自定义内存存储
from langgraph.checkpoint.memory import InMemorySaver


from agent.langsmith_client import LangsmithClient
# from agent.memory_manager import Memory_Manager
from agent.mcp_agent import MCPClient
from agent.celery.tasks import send_memory_message
import agent.state as state

class Agent:
    def __init__(self):
        # 初始化节点和模型
        self.nodes = ["supervisor","search", "rag", "chat", "other"]
        # 初始化大语言模型
        self.llm = ChatOpenAI(
            model="qwen3-next-80b-a3b-thinking",
            openai_api_key=os.getenv("QWEN_API_KEY"),
            openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        # 初始化监督模型
        self.supervisor_llm = ChatOpenAI(
            openai_api_base="http://localhost:11434/v1",
            openai_api_key="ollama",
            model="qwen3_lora_sft_supervisor_dpo",
        )
        # 取带工具的agent
        self.mcp_client = MCPClient(llm=self.llm)
        # 记忆管理器
        # self.memory_manager = Memory_Manager(llm=self.llm)
        # Langsmith客户端
        self.langsmith_client = LangsmithClient.langsmith_client()
        

    def supervisor_node(self, state: state.State) -> str:
        logger.info(">>> Supervisor Node")
        
        # 如果已经有type，结束
        if "type" in state:
            return {"type": END}
        else:
            # # 拉取prompt
            # prompts = self.langsmith_client.pull_prompt("supervisor", include_model=False)
            # prompt_super = prompts.format(question=state["message"][-1].content)
            # # 调用模型
            # response = self.llm.invoke([HumanMessage(content=prompt_super)])
            # # response = HumanMessage(content="other")  # 测试直接返回
            # # 对大模型的回答进行检验兜底，如果不在nodes中，返回other
            response = self.supervisor_llm.invoke([SystemMessage(content="消息分类为 search、rag、chat、other 中的一类，只输出标签。"), HumanMessage(content=state["message"][-1].content)])
            response = response.content.split("\n")[-1]
            if response not in self.nodes:
                raise ValueError(f"Invalid response from LLM: {response}. Must be one of {self.nodes}.")

        return {"type": response}


    def search_node(self, state: state.State) -> dict:
        logger.info(">>> Search Node")

        # 获取搜索结果，传递完整的消息历史以保持上下文
        if len(state["message"]) > 6: # 只保留最近6条消息，避免过长
            search_messages = state["message"][-6:]
        else:
            search_messages = state["message"]
        # 获取搜索结果
        search_result = self.mcp_client.invoke_with_context(search_messages)

        # 如果没有获取到结果，使用默认消息
        if not search_result:
            search_result = "搜索完成，但未找到相关结果。"

        # if len(search_result) > 500:  # 短结果直接返回
        #     send_memory_message.delay({"type": "summarize", "text": search_result, "ts": int(time.time())})

        return {"message": [AIMessage(content=search_result)], "type": "search"}


    def rag_node(self, state: state.State) -> str:
        logger.info(">>> RAG Node")
        return {"message": [HumanMessage(content="RAG响应")], "type": "rag"}


    def chat_node(self, state: state.State) -> str:
        logger.info(">>> Chat Node")
        
        response = self.llm.invoke(state["message"][-1].content)

        return {"message": response, "type": "chat"}


    def other_node(self, state: state.State) -> str:
        logger.info(">>> Other Node")
        return {"message": [HumanMessage(content="无法回答")], "type": "other"}


    def routing_func(self, state: state.State) -> str:
        if state["type"] == "search":
            return "search_node"
        elif state["type"] == "rag":
            return "rag_node"
        elif state["type"] == "chat":
            return "chat_node"
        elif state["type"] == "other":
            return "other_node"
        else:
            return END


    def agent(self, question: str):
        
        # # 启动异步任务处理长记忆，不阻塞graph执行
        # memory_thread = threading.Thread(
        #     target=self.memory_manager._async_get_long_memory,
        #     args=(question,),
        #     daemon=True  # 设置为守护线程，主程序结束时自动结束
        # )
        # memory_thread.start()
        
        # 使用Celery异步处理长记忆
        send_memory_message.delay({"type": "extract", "text": question, "ts": int(time.time())})
        
        graph = (StateGraph(state.State, context_schema=state.Context)
            .add_node("supervisor_node", self.supervisor_node)
            .add_node("search_node", self.search_node)
            .add_node("rag_node", self.rag_node)
            .add_node("chat_node", self.chat_node)
            .add_node("other_node", self.other_node)
            .set_entry_point("supervisor_node")
            .add_conditional_edges("supervisor_node", self.routing_func)
            .add_edge("search_node", "supervisor_node")
            .add_edge("rag_node", "supervisor_node")
            .add_edge("chat_node", "supervisor_node")
            .add_edge("other_node", "supervisor_node")
        ).compile(name="Director_Agent", checkpointer=InMemorySaver())

        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        for chunk in graph.invoke(
            {"message": [HumanMessage(content=question)]},
            config=config,
            stream_mode="updates"
        ):
            print(chunk)

        # response = graph.invoke(
        #     {"message": [HumanMessage(content=question)]},
        #     config=config,
        # )

        # return response["message"][-1].content