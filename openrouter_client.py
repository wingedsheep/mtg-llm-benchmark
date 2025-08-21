from openai import OpenAI, Stream

from openai.types.chat import ChatCompletion, ChatCompletionChunk


class OpenRouterClient:
    """Client for interacting with OpenRouter API"""

    def __init__(self, api_key: str):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    def create_completion(self, model: str, messages: list, **kwargs) -> ChatCompletion | Stream[ChatCompletionChunk]:
        """Create a chat completion using specified model"""
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        return response
