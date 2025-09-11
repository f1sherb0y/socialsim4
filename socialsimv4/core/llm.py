import google.generativeai as genai
from openai import OpenAI
from socialsimv4.api.schemas import LLMConfig

class LLMClient:
    def __init__(self, provider: LLMConfig):
        self.provider = provider
        if self.provider.kind == "openai":
            self.client = OpenAI(
                api_key=self.provider.api_key,
                base_url=self.provider.base_url,
            )
        elif self.provider.kind == "gemini":
            genai.configure(api_key=self.provider.api_key)
            self.client = genai.GenerativeModel(self.provider.model)
        else:
            raise ValueError(f"Unknown LLM provider kind: {self.provider.kind}")

    def chat(self, messages):
        if self.provider.dialect == "openai":
            response = self.client.chat.completions.create(
                model=self.provider.model,
                messages=messages,
                temperature=self.provider.temperature,
            )
            return response.choices[0].message.content.strip()
        elif self.provider.dialect == "gemini":
            # Gemini uses a different message format
            gemini_messages = [
                {"role": "user" if msg["role"] == "user" else "model", "parts": [msg["content"]]}
                for msg in messages
            ]
            response = self.client.generate_content(gemini_messages)
            return response.text.strip()
        else:
            raise ValueError(f"Unknown LLM dialect: {self.provider.dialect}")

    def completion(self, prompt):
        if self.provider.dialect == "openai":
            response = self.client.completions.create(
                model=self.provider.model,
                prompt=prompt,
                temperature=self.provider.temperature,
                max_tokens=self.provider.max_tokens,
            )
            return response.choices[0].text.strip()
        elif self.provider.dialect == "gemini":
            response = self.client.generate_content(prompt)
            return response.text.strip()
        else:
            raise ValueError(f"Unknown LLM dialect: {self.provider.dialect}")

    def embedding(self, text):
        if self.provider.dialect == "openai":
            response = self.client.embeddings.create(
                model=self.provider.model,
                input=text,
            )
            return response.data[0].embedding
        elif self.provider.dialect == "gemini":
            return genai.embed_content(
                model=self.provider.model,
                content=text,
            )["embedding"]
        else:
            raise ValueError(f"Unknown LLM dialect: {self.provider.dialect}")

def create_llm_client(provider: LLMConfig):
    return LLMClient(provider)
