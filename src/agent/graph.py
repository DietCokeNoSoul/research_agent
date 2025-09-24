"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv, find_dotenv

found = find_dotenv('.env.example', raise_error_if_not_found=False)
if found:
    load_dotenv(found, override=False)
langsmith_api_key = os.getenv('LANGSMITH_API_KEY')

os.environ["LANGSMITH_PROJECT"] = "Director_Agent"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_API_KEY"] = langsmith_api_key

from dataclasses import dataclass

from langgraph.runtime import Runtime

from typing_extensions import TypedDict, Annotated, Any, Dict

from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langsmith import Client

# 用LangGraph studio不需要自定义内存存储
from langgraph.checkpoint.memory import InMemorySaver



class Context(TypedDict):
    """Context parameters for the agent.

    Set these when creating assistants OR when invoking the graph.
    See: https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/
    """

    my_configurable_param: str


@dataclass
class State(TypedDict):
    """Input state for the agent.

    Defines the initial structure of incoming data.
    See: https://langchain-ai.github.io/langgraph/concepts/low_level/#state
    """
    message: Annotated[list[AnyMessage], add_messages]
    type: str


def supervisor_node(state: State) -> str:
    print(">>> Supervisor Node")
    # 拉取prompt
    prompts = client.pull_prompt("supervisor", include_model=False)
    prompt_super = prompts.format(question=state["message"][-1].content)
    # 调用模型
    response = llm.invoke([HumanMessage(content=prompt_super)])
    
    # 如果已经有type，结束
    if "type" in state:
        return {"type": END}
    
    return {"message": response, "type": response.content}


def travel_node(state: State) -> str:
    print(">>> Travel Node")
    return {"message": [HumanMessage(content="旅行响应")], "type": "travel"}


def rag_node(state: State) -> str:
    print(">>> RAG Node")
    return {"message": [HumanMessage(content="RAG响应")], "type": "rag"}


def chat_node(state: State) -> str:
    print(">>> Chat Node")
    return {"message": [HumanMessage(content="Chat响应")], "type": "chat"}


def other_node(state: State) -> str:
    print(">>> Other Node")
    return {"message": [HumanMessage(content="无法回答")], "type": "other"}


def routing_func(state: State) -> str:
    if state["type"] == "travel":
        return "travel_node"
    elif state["type"] == "rag":
        return "rag_node"
    elif state["type"] == "chat":
        return "chat_node"
    elif state["type"] == "other":
        return "other_node"
    else:
        return END


graph = (StateGraph(State, context_schema=Context)
    .add_node("supervisor_node", supervisor_node)
    .add_node("travel_node", travel_node)
    .add_node("rag_node", rag_node)
    .add_node("chat_node", chat_node)
    .add_node("other_node", other_node)
    .set_entry_point("supervisor_node")
    .add_conditional_edges("supervisor_node", routing_func)
    .add_edge("travel_node", "supervisor_node")
    .add_edge("rag_node", "supervisor_node")
    .add_edge("chat_node", "supervisor_node")
    .add_edge("other_node", "supervisor_node")
).compile(name="Director_Agent", checkpointer=InMemorySaver())

client = Client(api_key=langsmith_api_key)

llm = ChatOpenAI(
    model="qwen3-next-80b-a3b-instruct",
    openai_api_key=os.getenv("QWEN_API_KEY"),
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


config = {"configurable": {"thread_id":"1"}}

response = graph.invoke(
    {"message": [HumanMessage(content="广州南站的经纬度是多少？")]},
    config=config,
)

# response = graph.invoke(
#     {"message": [HumanMessage(content="我刚刚问什么？")]},
#     config=config,
# )


messages = response["message"]
for message in messages:
    print(message)

type = response["type"]
print("type:", type)