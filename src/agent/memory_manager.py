from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger
import time

class Memory_Manager:
    def __init__(self, llm=None):
        self.memory_llm = ChatOpenAI(
            openai_api_base="http://localhost:11434/v1",
            openai_api_key="ollama",
            model="qwen3_lora_sft_memory_q8_0"
        )
        self.llm = llm
        
    def get_long_memory(self, question: str) -> str:
        """从问题中提取长记忆信息"""
        response = self.memory_llm.invoke([SystemMessage(content="判断下面用户问题是否存在可以作为长记忆的重要信息，如果有则提取关键信息（短句或关键词），否则返回<None>。"), HumanMessage(content=question)])
        response = response.content.split("\n")[-1]
        if response == "<None>":
            return ""
        else:
            return response
        
    def _async_get_long_memory(self, question: str):
        """异步执行get_long_memory，不阻塞主流程"""
        logger.info("Starting async long memory extraction...")
        try:
            memory_info = self.get_long_memory(question)
            if memory_info:
                # 写入一个jsonl文件,每条数据的格式为{"time": "当前时间", "memory": "内容"}
                with open("C:\\Users\\71949\\Desktop\\research_agent\\resource\\long_memory\\long_memory.jsonl", "a", encoding="utf-8") as f:
                    f.write(f'{{"time": "{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}", "memory": "{memory_info}"}}\n')
                logger.info(f"Long memory extracted and saved")
        except Exception as e:
            logger.error(f"Error in get_long_memory: {e}")
            

    def summarize_search_result(self, search_result: str) -> str:
        logger.info("Summarizing search result...")
        """总结搜索结果，精简上下文"""
        
        summary_prompt = """
        请将以下论文搜索结果总结为简洁的要点，保留关键信息：
        - 搜索过程的描述
        - 论文标题和作者
        - 关键发现或方法
        - 相关性评分
        - 限制在200字以内
        
        搜索结果
        {search_result}
        """
        
        summary = self.llm.invoke([HumanMessage(content=summary_prompt.format(search_result=search_result))])
        return summary.content