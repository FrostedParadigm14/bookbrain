import os
import sys
sys.path.append(os.getcwd())

from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

def test_model(model_name):
    print(f"Testing model: {model_name}...")
    try:
        api_key = settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY")
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0
        )
        res = llm.invoke("Hi! Reply with 'OK'.")
        print(f"Success! Response: {res.content.strip()}")
        return True
    except Exception as e:
        print(f"Failed for {model_name}: {e}")
        return False

if __name__ == "__main__":
    test_model("gemini-1.5-pro")
    test_model("gemini-1.5-flash")
    test_model("gemini-2.5-flash")
    test_model("gemini-2.5-pro")
