import base64
from io import BytesIO

from openai import AsyncOpenAI


class ModerationEngine:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def check_message(self, message):
        content = []
        if message.content.strip():
            content.append({"type": "text", "text": message.content})

        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                data = await attachment.read()
                encoded = base64.b64encode(data).decode("ascii")
                content.append({"type": "image_url", "image_url": {"url": f"data:{attachment.content_type};base64,{encoded}"}})

        if not content:
            content.append({"type": "text", "text": "[message contains no text or supported image]"})

        return await self.client.moderations.create(model=self.model, input=content)
