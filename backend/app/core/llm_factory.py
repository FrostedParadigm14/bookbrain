import os
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_aws import ChatBedrock
from langchain_openai import ChatOpenAI
from app.core.config import settings

class LLMFactory:
    @staticmethod
    def get_llm(provider: str = None) -> BaseChatModel:
        """Returns a configured LangChain Chat Model"""
        target_provider = provider or settings.ACTIVE_PROVIDER
        
        if target_provider.lower() == "gemini":
            # Will automatically use GOOGLE_API_KEY from environment or settings
            api_key = settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("Gemini API key is missing. Set GEMINI_API_KEY or GOOGLE_API_KEY.")
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=api_key,
                temperature=0,
                convert_system_message_to_human=True
            )

        elif target_provider.lower() == "opencode":
            api_key = settings.OPENCODE_API_KEY or os.getenv("OPENCODE_API_KEY")
            if not api_key:
                raise ValueError("OpenCode API key is missing. Please set OPENCODE_API_KEY in backend/.env")
            
            base_url = settings.OPENCODE_BASE_URL or os.getenv("OPENCODE_BASE_URL")
            model_name = settings.OPENCODE_MODEL or os.getenv("OPENCODE_MODEL", "deepseek-v4-flash")
            
            kwargs = {
                "model": model_name,
                "api_key": api_key,
                "temperature": 0
            }
            if base_url and base_url.strip():
                kwargs["base_url"] = base_url.strip()
                
            return ChatOpenAI(**kwargs)

        else:
            raise ValueError(f"Unsupported LLM provider: {target_provider}")

# Usage: llm = LLMFactory.get_llm()
