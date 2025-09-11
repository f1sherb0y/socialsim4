import google.generativeai as genai
from openai import OpenAI

from socialsimv4.api.schemas import LLMConfig


class LLMClient:
    def __init__(self, provider: LLMConfig):
        self.provider = provider
        if self.provider.dialect == "openai":
            self.client = OpenAI(
                api_key=self.provider.api_key,
                base_url=self.provider.base_url,
            )
        elif self.provider.dialect == "gemini":
            genai.configure(api_key=self.provider.api_key)
            self.client = genai.GenerativeModel(self.provider.model)
        else:
            raise ValueError(f"Unknown LLM provider dialect: {self.provider.dialect}")

    def chat(self, messages):
        if self.provider.dialect == "openai":
            openai_messages = []
            for msg in messages:
                role = msg.get("role")
                if role not in ["system", "user", "assistant"]:
                    continue

                # Handle system messages that might have 'content' instead of 'parts'
                if role == "system" and "content" in msg:
                    openai_messages.append(
                        {"role": "system", "content": msg["content"]}
                    )
                    continue

                content_parts = []
                for part in msg.get("parts", []):
                    if isinstance(part, str):
                        content_parts.append({"type": "text", "text": part})
                    elif isinstance(part, dict) and "inline_data" in part:
                        inline_data = part["inline_data"]
                        mime_type = inline_data.get("mime_type")
                        data = inline_data.get("data")
                        if mime_type and data:
                            content_parts.append(
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{data}"
                                    },
                                }
                            )

                if content_parts:
                    openai_messages.append({"role": role, "content": content_parts})

            response = self.client.chat.completions.create(
                model=self.provider.model,
                messages=openai_messages,
                temperature=self.provider.temperature,
            )
            return response.choices[0].message.content.strip()
        elif self.provider.dialect == "gemini":
            response = self.client.generate_content(messages)
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
