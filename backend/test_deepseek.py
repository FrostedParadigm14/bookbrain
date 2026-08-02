import os
import sys
sys.path.append(os.getcwd())

from app.core.llm_factory import LLMFactory

def test_provider(provider_name):
    print(f"Testing LLM provider: {provider_name}...")
    try:
        llm = LLMFactory.get_llm(provider=provider_name)
        res = llm.invoke("Hi! Reply with 'DeepSeek OK'.")
        print(f"Success for {provider_name}! Response:\n{res.content.strip()}")
        return True
    except Exception as e:
        print(f"Failed for {provider_name}: {e}")
        return False

if __name__ == "__main__":
    print("--- Testing OpenCode Provider ---")
    test_provider("opencode")
