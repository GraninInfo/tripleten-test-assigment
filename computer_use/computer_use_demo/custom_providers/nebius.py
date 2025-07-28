import json
from typing import Any, Literal

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
from openai.types.chat.chat_completion_named_tool_choice_param import ChatCompletionNamedToolChoiceParam
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
                            image_in_tool_result = False
                            openai_content_block: list[ChatCompletionContentPartParam] = []
                            for subblock in block["content"]:
                                if subblock["type"] == "text":
                                    openai_content_block.append(ChatCompletionContentPartTextParam(
                                        text=subblock["text"],
                                        type="text",
                                    ))
                                elif subblock["type"] == "image":
                                    image_in_tool_result = True
                                    openai_content_block.append(ChatCompletionContentPartImageParam(
                                        type="image_url",
                                        image_url={
                                            "url": f"data:{subblock['source']['media_type']};{subblock['source']['type']},{subblock['source']['data']}",
                                        }
                                    ))
                            if image_in_tool_result:
                                formatted_messages.append(ChatCompletionUserMessageParam(
                                    content=openai_content_block,
                                    role="user",
                                ))
                            else:
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
        tool_choice: Literal["none", "auto"] | ChatCompletionNamedToolChoiceParam = "auto",
        tools: list[BetaToolParam] = [],
        extra_body: dict[str, Any] = {},
        max_tokens: int = 4096,
        **kwargs,
    ) -> BetaMessage:
        if not tools:
            tool_choice = "none"
        response = self._client.chat.completions.create(
            model=model,
            messages=self._format_messages(messages, system),
            max_tokens=max_tokens,
            tool_choice=tool_choice,
            tools=self._format_tools(tools),
        )
        return self._format_response(response)
    
    def complex_create(
        self,
        vision_model: str,
        tool_calling_model: str,
        messages: list[BetaMessageParam],
        system: BetaTextBlockParam | None = None,
        tool_choice: Literal["auto"] = "auto",
        tools: list[BetaToolParam] = [],
        extra_body: dict[str, Any] = {},
        max_tokens: int = 4096,
        **kwargs,
    ) -> BetaMessage:
        tools_list_str = "\n".join([f"{idx+1}. {json.dumps(tool, indent=2)}" for idx, tool in enumerate(tools)])
        define_tool_call_prompt = f"""<AWAILABLE_TOOLS>
You have the ability to use the following tools by passing the necessary parameters to them:
{tools_list_str}

If you decide to use some tool, directly indicate the name of this tool and the parameters with which it should be called.
The parameters required for each tool are specified in the input_schema field.
</AWAILABLE_TOOLS>"""
        original_system_message = system["text"] if system is not None else ""
        system_for_vision_model = BetaTextBlockParam(
            text=original_system_message + "\n" + define_tool_call_prompt,
            type="text",
        )
        vision_model_response = self.create(
            model=vision_model,
            messages=messages,
            system=system_for_vision_model,
            max_tokens=max_tokens,
        )
        text_with_specified_tool = vision_model_response.content[0].text

        parse_tool_call_prompt = f"""
You will be given a text response from the LLM model.
This response may describe the tool calls in text format.
Your task is to call the tools if they are precisely specified in the text response along with the parameters required for them.

Text response from the LLM model:
{text_with_specified_tool}
"""
        tool_call_message = BetaMessageParam(
            content=parse_tool_call_prompt,
            role="user",
        )
        tool_call_response = self.create(
            model=tool_calling_model,
            messages=[tool_call_message],
            tool_choice=tool_choice,
            tools=tools,
            max_tokens=max_tokens,
        )
        
        for content_block in tool_call_response.content:
            if content_block.type == "tool_use":
                vision_model_response.content.append(content_block)
        
        return vision_model_response
