import os
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_aws import ChatBedrock
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
            
        elif target_provider.lower() == "claude":
            # Standard AWS environment variables or from settings
            aws_access_key = settings.AWS_ACCESS_KEY_ID or os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = settings.AWS_SECRET_ACCESS_KEY or os.getenv("AWS_SECRET_ACCESS_KEY")
            region = settings.AWS_REGION or os.getenv("AWS_REGION", "us-east-1")
            
            if not aws_access_key or not aws_secret_key:
                raise ValueError("AWS credentials missing for Bedrock.")
                
            return ChatBedrock(
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region,
                model_kwargs={"temperature": 0}
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {target_provider}")

# Usage: llm = LLMFactory.get_llm()
