import anthropic

from app.config import settings


class ClaudeService:
    """Wraps the Anthropic Claude API for SAP support conversations."""

    SYSTEM_PROMPT = (
        "You are an expert SAP support assistant. "
        "You help developers and administrators with SAP configuration, "
        "ABAP development, troubleshooting, and best practices. "
        "Provide clear, actionable answers with references to relevant "
        "SAP transactions, tables, or OSS notes when applicable."
    )

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = settings.max_tokens

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a conversation to Claude and return the assistant's reply.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts.

        Returns:
            The text content of Claude's response.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.SYSTEM_PROMPT,
            messages=messages,
        )
        return response.content[0].text


claude_service = ClaudeService()
