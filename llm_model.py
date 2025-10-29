# llm_model.py
import os
from dotenv import load_dotenv
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

load_dotenv()

class BaseModel(ABC):
    """
    LLM 模型的抽象基类。
    所有具体模型实现必须继承此类并实现 `get_model()`。
    """

    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """
        返回一个 LangChain 兼容的 ChatModel 实例。
        """
        pass


class VLLMModel(BaseModel):
    """
    基于 vLLM 的 OpenAI 兼容 API 模型封装。
    适用于本地部署的 Qwen、Llama 等模型。
    """

    def __init__(
        self,
        model_name: str = os.getenv("QWEN_MODEL"), 
        base_url: str = os.getenv("QWEN_API_BASE"),
        api_key: str = os.getenv("QWEN_API_KEY"),
        **kwargs
    ):
        super().__init__(model_name, **kwargs)
        
        self.base_url = base_url
        self.api_key = api_key
        self.logger.info(f"Initialize VLLM Model: {model_name} @ {base_url}")

    def get_model(self) -> ChatOpenAI:
        return ChatOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model_name,
            temperature=0.1,
            request_timeout=120,
            max_retries=3,
            extra_body={"enable_thinking": False}
        )
    
    def get_local_model(self) -> ChatOpenAI:
        return ChatOpenAI(
            base_url= "http://202.120.59.70:1234/v1/",
            api_key= "wcf0326",
            model= "Qwen3-8B",
            temperature=0.1,
            request_timeout=180,
            max_retries=3,
            extra_body={"enable_thinking": False}
        )
        
if __name__ == "__main__":
    model_wrapper = VLLMModel()
    llm = model_wrapper.get_local_model()
    response = llm.invoke("你好，请介绍一下你自己。")
    print(response.content)