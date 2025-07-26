import json
from typing import Any

from openai import OpenAI
from openai.types.chat.chat_completion_message_param import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolMessageParam,
)
from openai.types.chat.chat_completion_content_part_param import (
    ChatCompletionContentPartParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionContentPartImageParam,
)
from openai.types.chat.chat_completion_message_tool_call_param import ChatCompletionMessageToolCallParam, Function
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam, FunctionDefinition
from openai.types.chat.chat_completion import ChatCompletion
from anthropic.types.beta import (
    BetaMessage,
    BetaMessageParam,
    BetaTextBlockParam,
    BetaToolParam,
    BetaContentBlock,
    BetaTextBlock,
    BetaToolUseBlock,
    BetaUsage,
)


class NebiusProvider:
    def __init__(self, api_key: str):
        self._client = OpenAI(base_url="https://api.studio.nebius.com/v1/", api_key=api_key)
    
    @staticmethod
    def _format_messages(messages: list[BetaMessageParam], system: BetaTextBlockParam | None = None) -> list[ChatCompletionMessageParam]:
        formatted_messages: list[ChatCompletionMessageParam] = []
        if system is not None:
            formatted_messages.append(ChatCompletionSystemMessageParam(
                content=system["text"],
                role="system",
            ))
        for message in messages:
            if message["role"] == "user" and isinstance(message["content"], str):
                formatted_messages.append(ChatCompletionUserMessageParam(
                    content=message["content"],
                    role="user",
                ))
            
            elif message["role"] == "user" and isinstance(message["content"], list):
                for block in message["content"]:
                    if block["type"] == "text":
                        formatted_messages.append(ChatCompletionUserMessageParam(
                            content=block["text"],
                            role="user",
                        ))
                    elif block["type"] == "tool_result":
                        if isinstance(block["content"], str):
                            formatted_messages.append(ChatCompletionToolMessageParam(
                                content=block["content"],
                                role="tool",
                                tool_call_id=block["tool_use_id"],
                            ))
                        elif isinstance(block["content"], list):
                            openai_content_block: list[ChatCompletionContentPartParam] = []
                            for subblock in block["content"]:
                                if subblock["type"] == "text":
                                    openai_content_block.append(ChatCompletionContentPartTextParam(
                                        text=subblock["text"],
                                        type="text",
                                    ))
                                elif subblock["type"] == "image":
                                    openai_content_block.append(ChatCompletionContentPartImageParam(
                                        image_url=subblock["source"]["data"],
                                        type="image_url",
                                    ))
                            formatted_messages.append(ChatCompletionToolMessageParam(
                                content=openai_content_block,
                                role="tool",
                                tool_call_id=block["tool_use_id"],
                            ))
                    
            elif message["role"] == "assistant" and isinstance(message["content"], str):
                formatted_messages.append(ChatCompletionAssistantMessageParam(
                    content=message["content"],
                    role="assistant",
                ))
            
            elif message["role"] == "assistant" and isinstance(message["content"], list):
                for block in message["content"]:
                    if block["type"] == "text":
                        formatted_messages.append(ChatCompletionAssistantMessageParam(
                            content=block["text"],
                            role="assistant",
                        ))
                    elif block["type"] == "thinking":
                        pass
                    elif block["type"] == "tool_use":
                        formatted_messages.append(ChatCompletionAssistantMessageParam(
                            tool_calls=[ChatCompletionMessageToolCallParam(
                                id=block["id"],
                                function=Function(
                                    arguments=json.dumps(block["input"]),
                                    name=block["name"],
                                ),
                                type="function",
                            )],
                            role="assistant",
                        ))
        
        return formatted_messages
    
    @staticmethod
    def _format_tools(tools: list[BetaToolParam]) -> list[ChatCompletionToolParam]:
        formatted_tools: list[ChatCompletionToolParam] = []
        for tool in tools:
            formatted_tools.append(
                ChatCompletionToolParam(
                    function=FunctionDefinition(
                        name=tool["name"],
                        description=tool["description"],
                        parameters=tool["input_schema"],
                    ),
                    type="function",
                )
            )
        return formatted_tools
    
    @staticmethod
    def _format_response(response: ChatCompletion) -> BetaMessage:
        formatted_contents: list[BetaContentBlock] = []
        for choice in response.choices:
            if choice.message.content is not None:
                formatted_contents.append(BetaTextBlock(
                    text=choice.message.content,
                    type="text",
                ))
            if choice.message.tool_calls is not None:
                for tool_use in choice.message.tool_calls:
                    formatted_contents.append(BetaToolUseBlock(
                        id=tool_use.id,
                        input=json.loads(tool_use.function.arguments),
                        name=tool_use.function.name,
                        type="tool_use",
                    ))
        
        return BetaMessage(
            id=response.id,
            content=formatted_contents,
            model=response.model,
            role="assistant",
            type="message",
            usage=BetaUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )
        )
    
    def create(
        self,
        model: str,
        messages: list[BetaMessageParam],
        system: BetaTextBlockParam | None = None,
        tools: list[BetaToolParam] = [],
        extra_body: dict[str, Any] = {},
        max_tokens: int = 4096,
        **kwargs,
    ) -> BetaMessage:
        response = self._client.chat.completions.create(
            model=model,
            messages=self._format_messages(messages, system),
            max_tokens=max_tokens,
            tools=self._format_tools(tools),
            tool_choice="auto",
        )
        return self._format_response(response)
