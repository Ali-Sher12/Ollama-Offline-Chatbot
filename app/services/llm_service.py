import json
import time
import httpx
import logging
from typing import List, Dict, Any, Generator, Optional
from app.config import config_manager
from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

ONLINE_MODELS = {
    "openai": [
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Fast & Cheap)"},
        {"id": "gpt-4o", "name": "GPT-4o (Flagship Omnimodal)"},
        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"}
    ],
    "anthropic": [
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (State-of-the-Art)"},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku (Ultra Fast)"}
    ],
    "gemini": [
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Next-Gen Fast)"},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro (Deep Context)"}
    ],
    "groq": [
        {"id": "llama-3.3-70b-versatile", "name": "Groq Llama 3.3 70B (Extremely Fast)"},
        {"id": "llama-3.1-8b-instant", "name": "Groq Llama 3.1 8B Instant"},
        {"id": "mixtral-8x7b-32768", "name": "Groq Mixtral 8x7B"}
    ],
    "openrouter": [
        {"id": "meta-llama/llama-3.3-70b-instruct", "name": "OpenRouter: Llama 3.3 70B"},
        {"id": "deepseek/deepseek-chat", "name": "OpenRouter: DeepSeek V3"},
        {"id": "google/gemini-2.0-flash-exp:free", "name": "OpenRouter: Gemini 2.0 Flash (Free)"}
    ]
}

class LLMService:
    def __init__(self):
        pass

    def get_ollama_models(self) -> List[Dict[str, Any]]:
        """Fetch list of models available in local Ollama instance."""
        ollama_url = config_manager.get("ollama_url", "http://localhost:11434")
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.get(f"{ollama_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = []
                    for m in data.get("models", []):
                        size_gb = round(m.get("size", 0) / (1024**3), 2)
                        models.append({
                            "id": m.get("model", m.get("name", "")),
                            "name": f"{m.get('name')} ({size_gb} GB)",
                            "provider": "ollama",
                            "details": m.get("details", {})
                        })
                    return models
        except Exception as e:
            logger.debug(f"Could not connect to Ollama: {e}")
        return []

    def get_all_available_models(self) -> Dict[str, Any]:
        """Aggregate local Ollama models and configured online models."""
        ollama_models = self.get_ollama_models()
        is_ollama_online = len(ollama_models) > 0

        providers = {
            "ollama": {
                "name": "Local Ollama",
                "is_online": is_ollama_online,
                "models": ollama_models
            }
        }

        api_keys = config_manager.get("api_keys", {})
        for provider_id, model_list in ONLINE_MODELS.items():
            has_key = bool(api_keys.get(provider_id, "").strip())
            providers[provider_id] = {
                "name": provider_id.capitalize(),
                "is_configured": has_key,
                "models": [{"id": m["id"], "name": m["name"], "provider": provider_id} for m in model_list]
            }

        return providers

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        provider: str,
        model: str,
        keep_alive: str = "30m"
    ) -> Generator[Dict[str, Any], None, None]:
        """Unified stream generator across Ollama and Online providers."""
        start_time = time.time()
        accumulated_text = ""
        prompt_tokens = 0
        completion_tokens = 0

        # Calculate estimated prompt tokens from message history
        for m in messages:
            prompt_tokens += analytics_service.estimate_tokens(m.get("content", ""))

        if provider == "ollama":
            ollama_url = config_manager.get("ollama_url", "http://localhost:11434")
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "keep_alive": keep_alive
            }

            try:
                with httpx.Client(timeout=120.0) as client:
                    with client.stream("POST", f"{ollama_url}/api/chat", json=payload) as response:
                        if response.status_code != 200:
                            yield {"type": "error", "error": f"Ollama error {response.status_code}: {response.text}"}
                            return

                        for line in response.iter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                                msg = chunk.get("message", {})
                                chunk_content = msg.get("content", "")
                                if chunk_content:
                                    accumulated_text += chunk_content
                                    yield {"type": "chunk", "content": chunk_content}

                                if chunk.get("done", False):
                                    if "prompt_eval_count" in chunk:
                                        prompt_tokens = chunk["prompt_eval_count"]
                                    if "eval_count" in chunk:
                                        completion_tokens = chunk["eval_count"]
                                    break
                            except Exception as parse_err:
                                logger.debug(f"Chunk parse error: {parse_err}")
            except Exception as e:
                yield {"type": "error", "error": f"Failed to connect to local Ollama: {str(e)}"}
                return

        elif provider in ("openai", "groq", "openrouter"):
            api_keys = config_manager.get("api_keys", {})
            api_key = api_keys.get(provider, "").strip()
            endpoints = config_manager.get("custom_endpoints", {})
            base_url = endpoints.get(provider, "https://api.openai.com/v1")

            if not api_key:
                yield {"type": "error", "error": f"API key for {provider.capitalize()} is missing. Please set it in Settings."}
                return

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            if provider == "openrouter":
                headers["HTTP-Referer"] = "https://github.com/Ali-Sher12/Ollama-Offline-Chatbot"
                headers["X-Title"] = "Ollama Desktop Chatbot"

            payload = {
                "model": model,
                "messages": messages,
                "stream": True
            }

            try:
                with httpx.Client(timeout=120.0) as client:
                    with client.stream("POST", f"{base_url}/chat/completions", headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            error_text = response.read().decode("utf-8", errors="replace")
                            yield {"type": "error", "error": f"{provider.capitalize()} API error ({response.status_code}): {error_text}"}
                            return

                        for line in response.iter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    choices = chunk.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            accumulated_text += content
                                            yield {"type": "chunk", "content": content}
                                    if "usage" in chunk and chunk["usage"]:
                                        prompt_tokens = chunk["usage"].get("prompt_tokens", prompt_tokens)
                                        completion_tokens = chunk["usage"].get("completion_tokens", completion_tokens)
                                except Exception:
                                    pass
            except Exception as e:
                yield {"type": "error", "error": f"Request to {provider.capitalize()} failed: {str(e)}"}
                return

        elif provider == "anthropic":
            api_keys = config_manager.get("api_keys", {})
            api_key = api_keys.get("anthropic", "").strip()
            if not api_key:
                yield {"type": "error", "error": "Anthropic API key is missing. Please set it in Settings."}
                return

            # Format messages for Anthropic (system prompt separated)
            system_prompt = ""
            anthropic_messages = []
            for m in messages:
                if m["role"] == "system":
                    system_prompt += m["content"] + "\n"
                else:
                    anthropic_messages.append({"role": m["role"], "content": m["content"]})

            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "max_tokens": 4096,
                "messages": anthropic_messages,
                "stream": True
            }
            if system_prompt:
                payload["system"] = system_prompt.strip()

            try:
                with httpx.Client(timeout=120.0) as client:
                    with client.stream("POST", "https://api.anthropic.com/v1/messages", headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            error_text = response.read().decode("utf-8", errors="replace")
                            yield {"type": "error", "error": f"Anthropic API error ({response.status_code}): {error_text}"}
                            return

                        for line in response.iter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                try:
                                    chunk = json.loads(data_str)
                                    chunk_type = chunk.get("type")
                                    if chunk_type == "content_block_delta":
                                        content = chunk.get("delta", {}).get("text", "")
                                        if content:
                                            accumulated_text += content
                                            yield {"type": "chunk", "content": content}
                                    elif chunk_type == "message_start":
                                        usage = chunk.get("message", {}).get("usage", {})
                                        prompt_tokens = usage.get("input_tokens", prompt_tokens)
                                    elif chunk_type == "message_delta":
                                        usage = chunk.get("usage", {})
                                        completion_tokens = usage.get("output_tokens", completion_tokens)
                                except Exception:
                                    pass
            except Exception as e:
                yield {"type": "error", "error": f"Request to Anthropic failed: {str(e)}"}
                return

        elif provider == "gemini":
            api_keys = config_manager.get("api_keys", {})
            api_key = api_keys.get("gemini", "").strip()
            if not api_key:
                yield {"type": "error", "error": "Google Gemini API key is missing. Please set it in Settings."}
                return

            # Gemini OpenAI-compatible endpoint
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            gemini_base = f"https://generativelanguage.googleapis.com/v1beta/openai"
            payload = {
                "model": model,
                "messages": messages,
                "stream": True
            }

            try:
                with httpx.Client(timeout=120.0) as client:
                    with client.stream("POST", f"{gemini_base}/chat/completions", headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            error_text = response.read().decode("utf-8", errors="replace")
                            yield {"type": "error", "error": f"Gemini API error ({response.status_code}): {error_text}"}
                            return

                        for line in response.iter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    choices = chunk.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            accumulated_text += content
                                            yield {"type": "chunk", "content": content}
                                except Exception:
                                    pass
            except Exception as e:
                yield {"type": "error", "error": f"Request to Gemini failed: {str(e)}"}
                return

        else:
            yield {"type": "error", "error": f"Unsupported provider: {provider}"}
            return

        duration = max(0.01, round(time.time() - start_time, 2))
        if completion_tokens == 0:
            completion_tokens = analytics_service.estimate_tokens(accumulated_text)

        tok_per_sec = round(completion_tokens / duration, 1)
        estimated_cost = analytics_service.calculate_cost(provider, model, prompt_tokens, completion_tokens)

        yield {
            "type": "done",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "duration_sec": duration,
            "tokens_per_sec": tok_per_sec,
            "estimated_cost": estimated_cost
        }

llm_service = LLMService()
