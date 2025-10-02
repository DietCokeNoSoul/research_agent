from langsmith import Client
from dotenv import load_dotenv, find_dotenv
import os

class LangsmithClient:

    def langsmith_client() -> Client:
        # 加载环境变量
        found = find_dotenv('.env.example', raise_error_if_not_found=False)
        if found:
            load_dotenv(found, override=False)
        langsmith_api_key = os.getenv('LANGSMITH_API_KEY')
        # 设置环境变量
        os.environ["LANGSMITH_PROJECT"] = "Director_Agent"
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
        return Client(api_key=os.getenv("LANGSMITH_API_KEY"))
