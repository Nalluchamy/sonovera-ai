import os
import sys
import io
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

class ChatbotEngine:
    """
    Engine for interacting with the NVIDIA API (OpenAI-compatible) 
    using the meta/llama-3.1-8b-instruct model.
    """
    def __init__(self) -> None:
        """
        Initializes the OpenAI client with NVIDIA API configuration.
        """
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model = os.getenv("LLM_MODEL", "meta/llama-3.1-8b-instruct")
        self.system_prompt = "You are a helpful assistant. IMPORTANT: Keep your responses concise and relatively short (ideally under 400 characters) to ensure fast voice synthesis, as your output is narrated in real-time."
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def set_system_prompt(self, prompt: str) -> None:
        """Updates the system prompt for the chatbot."""
        self.system_prompt = prompt


    def respond_stream(self, user_message: str, history: List[Dict[str, str]], provider: str = "NVIDIA", image_base64: str = None, translation_enabled: bool = False, knowledge_context: str = "", web_search_enabled: bool = False):
        """
        Generates a streaming response using the selected provider, 
        supporting Vision (images), Tools (Actions), Multilingual Translation, and Knowledge Base (RAG).
        """
        system_prompt = self.system_prompt
        if translation_enabled:
            system_prompt += "\n\nCRITICAL: Translation Mode is ACTIVE. If the user speaks in a foreign language, translate their message to English and respond normally."
        
        if knowledge_context:
            system_prompt += f"\n\nKNOWLEDGE BASE CONTEXT:\n{knowledge_context}\n\nINSTRUCTION: Use the above context to answer user questions if relevant. Cite information from the context if possible."
        
        messages = [{"role": "system", "content": system_prompt}]


        for msg in history:
            role = msg["role"]
            if role == "ai":
                role = "assistant"
            messages.append({"role": role, "content": msg["content"]})
        
        # Build user message (supports text or text+image)
        user_content = [{"type": "text", "text": user_message}]
        if image_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            })
        
        messages.append({"role": "user", "content": user_content}) # type: ignore

        try:
            if provider == "NVIDIA":
                client = self.client
                # If image exists, switch to a vision-capable model if needed
                model = "meta/llama-3.2-11b-vision-instruct" if image_base64 else self.model
            elif provider == "Ollama (Local)":
                from openai import OpenAI as OpenAIClient
                # Ollama runs on 11434 by default
                client = OpenAIClient(api_key="ollama", base_url="http://localhost:11434/v1")
                model = os.getenv("OLLAMA_MODEL", "llama3")
            else:
                from openai import OpenAI as OpenAIClient
                client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))
                model = "gpt-4o" if image_base64 else "gpt-4o-mini"

            
            # Tools integration (only for non-image messages for simplicity initially)
            # Suppress torchcodec warnings that can pollute output
            _old_stderr = sys.stderr
            sys.stderr = io.StringIO()
            try:
                from actions import TOOLS, execute_tool
            finally:
                sys.stderr = _old_stderr
            
            # Filter tools if web search is disabled
            available_tools = TOOLS if web_search_enabled else [t for t in TOOLS if t["function"]["name"] != "search_web"]
            # If no tools remain, use None
            active_tools = available_tools if available_tools else None

            response = client.chat.completions.create(
                model=model,
                messages=messages, # type: ignore
                temperature=0.7,
                max_tokens=1024,
                stream=True,
                tools=active_tools if not image_base64 else None # Tool calling is often restricted with vision
            )
            
            # Streaming + Tool handling logic
            full_reply = ""
            tool_calls = {} # Use dict keyed by index for easier merging
            
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_reply += delta.content
                    yield delta.content
                
                # Check for tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        index = tc.index
                        if index not in tool_calls:
                            tool_calls[index] = tc
                        else:
                            # Merge function arguments
                            if tc.function.arguments:
                                if not tool_calls[index].function.arguments:
                                    tool_calls[index].function.arguments = tc.function.arguments
                                else:
                                    tool_calls[index].function.arguments += tc.function.arguments
            
            # If tools were called
            if tool_calls:
                # Convert back to list for the API
                tool_calls_list = [tool_calls[i] for i in sorted(tool_calls.keys())]
                
                yield "\n\n*(Searching for information...)*\n\n"
                
                # Add assistant message with tool calls to history
                # content MUST be None when tool_calls are present for some providers
                messages.append({"role": "assistant", "content": full_reply or None, "tool_calls": tool_calls_list}) # type: ignore
                
                import json
                for tc in tool_calls_list:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                        output = execute_tool(tc.function.name, args)
                        messages.append({
                            "tool_call_id": tc.id,
                            "role": "tool",
                            "name": tc.function.name,
                            "content": str(output)
                        })
                    except Exception as tool_err:
                        messages.append({
                            "tool_call_id": tc.id,
                            "role": "tool",
                            "name": tc.function.name,
                            "content": f"Error executing tool: {tool_err}"
                        })
                
                # Second call to get final response with tool outputs
                final_response = client.chat.completions.create(
                    model=model,
                    messages=messages, # type: ignore
                    stream=True
                )
                for chunk in final_response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        except Exception as e:
            error_msg = str(e)
            # Filter out noisy library errors from the user-facing response
            if 'torchcodec' in error_msg or 'libtorchcodec' in error_msg:
                print(f"[ChatEngine] Suppressed torchcodec error: {error_msg[:100]}")
                yield "I encountered a temporary issue. Please try again."
            else:
                print(f"[ChatEngine] Error: {error_msg}")
                yield f"Sorry, I encountered an error. Please try again."



    def respond(self, user_message: str, history: List[Dict[str, str]]) -> str:
        """
        Generates a full response (legacy/sync) using the NVIDIA chat completion API.
        """
        # We can just join the steam for backward compatibility if needed
        return "".join(list(self.respond_stream(user_message, history)))

