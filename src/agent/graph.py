"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations

import os
import uuid
from loguru import logger

from langgraph.runtime import Runtime
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
# 用LangGraph studio不需要自定义内存存储
from langgraph.checkpoint.memory import InMemorySaver

from agent.langsmith_client import LangsmithClient
import agent.state as state

class Agent:
    def __init__(self):
        self.nodes = ["supervisor","search", "rag", "chat", "other"]
        self.llm = ChatOpenAI(
            model="qwen3-next-80b-a3b-instruct",
            openai_api_key=os.getenv("QWEN_API_KEY"),
            openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.supervisor_llm = llm = ChatOpenAI(
            openai_api_base="http://localhost:11434/v1",
            openai_api_key="ollama",
            model="qwen3_lora_sft_q8_0"
        )
        self.langsmith_client = LangsmithClient.langsmith_client()

    def supervisor_node(self, state: state.State) -> str:
        print(">>> Supervisor Node")
        
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


    def search_node(self, state: state.State) -> str:
        print(">>> Search Node")
        return {"message": [HumanMessage(content="搜索响应")], "type": "search"}


    def rag_node(self, state: state.State) -> str:
        print(">>> RAG Node")
        return {"message": [HumanMessage(content="RAG响应")], "type": "rag"}


    def chat_node(self, state: state.State) -> str:
        print(">>> Chat Node")
        
        response = self.llm.invoke(state["message"][-1].content)

        return {"message": response, "type": "chat"}


    def other_node(self, state: state.State) -> str:
        print(">>> Other Node")
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