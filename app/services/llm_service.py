import json
import time
import httpx
import logging
from typing import List, Dict, Any, Generator, Optional, Tuple
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

RECOMMENDED_LOCAL_MODELS = [
    {
        "id": "llama3.2:1b",
        "name": "Llama 3.2 1B",
        "approx_size": "~1.3 GB",
        "min_ram_gb": 4,
        "description": "Ultra-fast general-purpose model. Great for older laptops and quick chats."
    },
    {
        "id": "llama3.2:3b",
        "name": "Llama 3.2 3B",
        "approx_size": "~2.0 GB",
        "min_ram_gb": 8,
        "description": "Balanced quality and speed for everyday chat, writing, and light coding."
    },
    {
        "id": "llama3.1:8b",
        "name": "Llama 3.1 8B",
        "approx_size": "~4.7 GB",
        "min_ram_gb": 16,
        "description": "Strong general reasoning and instruction following when you have enough RAM."
    },
    {
        "id": "qwen2.5:3b-instruct",
        "name": "Qwen 2.5 3B Instruct",
        "approx_size": "~1.9 GB",
        "min_ram_gb": 8,
        "description": "Efficient multilingual assistant with good instruction following."
    },
    {
        "id": "qwen2.5-coder:7b",
        "name": "Qwen 2.5 Coder 7B",
        "approx_size": "~4.7 GB",
        "min_ram_gb": 16,
        "description": "Specialized coding model for code generation, review, and debugging."
    },
    {
        "id": "deepseek-r1:1.5b",
        "name": "DeepSeek R1 1.5B",
        "approx_size": "~1.1 GB",
        "min_ram_gb": 4,
        "description": "Small reasoning model that shows its chain of thought."
    },
    {
        "id": "phi3",
        "name": "Phi-3 Mini",
        "approx_size": "~2.2 GB",
        "min_ram_gb": 8,
        "description": "Compact Microsoft model with strong reasoning for its size."
    },
    {
        "id": "mistral",
        "name": "Mistral 7B",
        "approx_size": "~4.1 GB",
        "min_ram_gb": 16,
        "description": "Reliable all-round open model for chat and writing."
    },
    {
        "id": "dolphin-mistral",
        "name": "Dolphin Mistral",
        "approx_size": "~4.1 GB",
        "min_ram_gb": 16,
        "description": "Uncensored Mistral fine-tune for unrestricted local conversations."
    },
    {
        "id": "gemma3",
        "name": "Gemma 3",
        "approx_size": "~3.3 GB",
        "min_ram_gb": 8,
        "description": "Google's capable lightweight open model."
    },
    {
        "id": "gemma4:e2b",
        "name": "Gemma 4 E2B",
        "approx_size": "~5.0 GB",
        "min_ram_gb": 8,
        "description": "Newer efficient Gemma model (availability depends on the Ollama registry)."
    },
    {
        "id": "moondream",
        "name": "Moondream (Vision)",
        "approx_size": "~1.7 GB",
        "min_ram_gb": 4,
        "description": "Tiny vision model for image description, OCR, and screenshot analysis."
    },
]

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

    def check_agent_readiness(self, provider: str, model: str) -> Tuple[bool, str]:
        """
        Fast preflight check before starting Agent Mode.

        Returns (ready, error_message). For local Ollama models this verifies
        that the model is installed and advertises tool-calling support. For
        cloud providers it verifies that an API key is configured. When a
        capability endpoint is unavailable, we allow the run to proceed and
        let the real request surface any error.
        """
        provider = (provider or "ollama").strip().lower()
        model = (model or "").strip()

        if provider == "ollama":
            ollama_url = config_manager.get("ollama_url", "http://localhost:11434").rstrip("/")
            try:
                with httpx.Client(timeout=8.0) as client:
                    res = client.post(f"{ollama_url}/api/show", json={"model": model})
                    if res.status_code == 404:
                        return (
                            False,
                            f"Local model '{model}' is not installed. Open the Model Library to download it, "
                            "or select an installed model.",
                        )
                    if res.status_code != 200:
                        return True, ""
                    data = res.json() or {}
                    capabilities = data.get("capabilities")
                    if isinstance(capabilities, list) and "tools" not in capabilities:
                        return (
                            False,
                            f"Local model '{model}' does not support tool calling, which Agent Mode requires. "
                            "Choose a tool-capable model such as qwen2.5:1.5b, qwen2.5:3b, or mistral, "
                            "or turn off Agent Mode.",
                        )
            except Exception:
                return (
                    False,
                    f"Cannot reach Ollama at {ollama_url}. Make sure Ollama is running, then try again.",
                )
            return True, ""

        if provider in ("openai", "groq", "openrouter", "gemini", "anthropic"):
            api_keys = config_manager.get("api_keys", {})
            if not (api_keys.get(provider) or "").strip():
                display = {
                    "openai": "OpenAI",
                    "groq": "Groq",
                    "openrouter": "OpenRouter",
                    "gemini": "Google Gemini",
                    "anthropic": "Anthropic",
                }.get(provider, provider.capitalize())
                return (
                    False,
                    f"Agent Mode needs an API key for {display}. Add one in Settings, "
                    "or switch to a local Ollama model.",
                )

        return True, ""

    def get_recommended_models(self) -> Dict[str, Any]:
        """Return curated download suggestions annotated with hardware compatibility."""
        specs = self.get_device_specs()
        ram_gb = specs.get("total_ram_gb", 8.0)
        installed_ids = {m.get("id", "") for m in self.get_ollama_models()}
        # Treat an untagged model and its ':latest' tag as the same model.
        installed_roots = {mid.split(":")[0] for mid in installed_ids if mid}

        models = []
        for model in RECOMMENDED_LOCAL_MODELS:
            model_id = model["id"]
            is_installed = model_id in installed_ids or (
                ":" not in model_id and model_id in installed_roots
            )
            is_compatible = ram_gb >= model.get("min_ram_gb", 0)
            models.append({
                **model,
                "is_installed": is_installed,
                "is_compatible": is_compatible,
                "recommendation_reason": (
                    f"Fits comfortably in {ram_gb} GB RAM"
                    if is_compatible
                    else f"Needs about {model.get('min_ram_gb', 0)} GB RAM (you have {ram_gb} GB)"
                ),
            })

        return {
            "models": models,
            "device_specs": specs,
        }

    def pull_ollama_model(self, model_name: str, cancel_event=None) -> Generator[Dict[str, Any], None, None]:
        """Stream download progress for an Ollama model via the /api/pull endpoint."""
        model_name = (model_name or "").strip()
        if not model_name:
            yield {"type": "error", "error": "Please provide a model name, for example 'llama3.2:3b'."}
            return

        ollama_url = config_manager.get("ollama_url", "http://localhost:11434")
        timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=10.0)
        done_sent = False

        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream(
                    "POST",
                    f"{ollama_url}/api/pull",
                    json={"model": model_name, "stream": True}
                ) as response:
                    if response.status_code != 200:
                        body = response.read().decode("utf-8", errors="replace")
                        yield {
                            "type": "error",
                            "model": model_name,
                            "error": f"Ollama rejected the download ({response.status_code}): {body}"
                        }
                        return

                    for line in response.iter_lines():
                        # Check for cancellation on each chunk
                        if cancel_event is not None and cancel_event.is_set():
                            yield {"type": "cancelled", "model": model_name}
                            return

                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except Exception:
                            continue

                        if chunk.get("error"):
                            yield {"type": "error", "model": model_name, "error": str(chunk["error"])}
                            return

                        status = chunk.get("status", "")
                        completed = int(chunk.get("completed") or 0)
                        total = int(chunk.get("total") or 0)
                        percent = round((completed / total) * 100, 1) if total > 0 else None

                        yield {
                            "type": "progress",
                            "model": model_name,
                            "status": status,
                            "completed": completed,
                            "total": total,
                            "percent": percent,
                        }

                        if status == "success":
                            done_sent = True
                            yield {"type": "done", "model": model_name, "status": status}
                            break

            if not done_sent and (cancel_event is None or not cancel_event.is_set()):
                yield {"type": "done", "model": model_name, "status": "complete"}
        except Exception as e:
            yield {
                "type": "error",
                "model": model_name,
                "error": f"Could not download the model. Is Ollama running? ({str(e)})"
            }


    def delete_ollama_model(self, model_name: str) -> Dict[str, Any]:
        """Delete an installed local Ollama model."""
        model_name = (model_name or "").strip()
        if not model_name:
            return {"success": False, "error": "No model name provided."}

        ollama_url = config_manager.get("ollama_url", "http://localhost:11434")
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(
                    "DELETE",
                    f"{ollama_url}/api/delete",
                    json={"model": model_name}
                )
                if response.status_code in (200, 204):
                    return {"success": True, "model": model_name}
                body = response.text
                return {
                    "success": False,
                    "model": model_name,
                    "error": f"Ollama could not delete the model ({response.status_code}): {body}"
                }
        except Exception as e:
            return {
                "success": False,
                "model": model_name,
                "error": f"Could not connect to Ollama: {str(e)}"
            }

    def get_device_specs(self) -> Dict[str, Any]:
        """Detect system CPU count, total RAM in GB, and compute tier."""
        import os
        import platform

        cpu_count = os.cpu_count() or 4
        ram_gb = 8.0
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal:" in line:
                        ram_gb = round(int(line.split()[1]) / (1024**2), 1)
                        break
        except Exception:
            pass

        return {
            "cpu_cores": cpu_count,
            "cpu_count": cpu_count,
            "ram_total_gb": ram_gb,
            "total_ram_gb": ram_gb,
            "ram_total_bytes": int(ram_gb * (1024**3)),
            "os": platform.system()
        }

    def get_all_available_models(self) -> Dict[str, Any]:
        """Aggregate local Ollama models and configured online models with hardware-aware recommendations (⭐)."""
        specs = self.get_device_specs()
        ram_gb = specs.get("total_ram_gb", 8.0)
        cpu_count = specs.get("cpu_count", 4)

        # Local RAM threshold for smooth local inference
        # On <= 8GB RAM, recommend models <= 3.5GB; on 16GB, recommend <= 8GB
        max_rec_local_size_gb = 3.8 if ram_gb <= 8.5 else (8.5 if ram_gb <= 16.5 else 20.0)

        raw_ollama_models = self.get_ollama_models()
        is_ollama_online = len(raw_ollama_models) > 0

        annotated_ollama = []
        for m in raw_ollama_models:
            details = m.get("details", {})
            param_size = details.get("parameter_size", "")
            # Check model name or size
            is_rec = False
            # Check if size fits in RAM comfortably
            size_str = m.get("name", "")
            # e.g. "qwen2.5:1.5b (0.92 GB)"
            import re
            match = re.search(r"\(([0-9.]+)\s*GB\)", size_str)
            size_gb = float(match.group(1)) if match else 2.0

            if size_gb <= max_rec_local_size_gb:
                is_rec = True

            star_prefix = "⭐ " if is_rec else ""
            rec_note = " (Recommended for your hardware)" if is_rec else ""
            annotated_ollama.append({
                "id": m["id"],
                "name": f"{star_prefix}{m['name']}{rec_note}",
                "raw_name": m["name"],
                "provider": "ollama",
                "is_recommended": is_rec,
                "recommendation_reason": f"Fits comfortably in {ram_gb} GB RAM without swapping" if is_rec else None,
                "details": details
            })

        providers = {
            "ollama": {
                "name": "Local Ollama",
                "is_online": is_ollama_online,
                "models": annotated_ollama
            }
        }

        # Online models that are recommended for fast agentic responsiveness
        recommended_online_ids = {
            "gemini-2.0-flash",
            "gpt-4o-mini",
            "llama-3.3-70b-versatile",
            "claude-3-5-haiku-20241022"
        }

        provider_display_names = {
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "gemini": "Google Gemini",
            "groq": "Groq",
            "openrouter": "OpenRouter",
        }

        api_keys = config_manager.get("api_keys", {})
        for provider_id, model_list in ONLINE_MODELS.items():
            has_key = bool(api_keys.get(provider_id, "").strip())
            online_annotated = []
            for m in model_list:
                is_rec = m["id"] in recommended_online_ids
                star_prefix = "⭐ " if is_rec else ""
                online_annotated.append({
                    "id": m["id"],
                    "name": f"{star_prefix}{m['name']}",
                    "raw_name": m["name"],
                    "provider": provider_id,
                    "is_recommended": is_rec,
                    "recommendation_reason": "Ultra-fast low-latency cloud model (recommended)" if is_rec else None
                })

            providers[provider_id] = {
                "name": provider_display_names.get(provider_id, provider_id.capitalize()),
                "is_configured": has_key,
                "models": online_annotated
            }

        providers["system_specs"] = specs
        providers["device_specs"] = specs
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

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        provider: str,
        model: str,
        keep_alive: str = "30m"
    ) -> Dict[str, Any]:
        """
        Unified tool-calling method across local Ollama, OpenAI-compatible APIs, and Anthropic.
        Returns a dict:
        {
            "content": str,
            "tool_calls": List[{"id": str, "name": str, "arguments": dict}],
            "prompt_tokens": int,
            "completion_tokens": int,
            "raw_message": dict
        }
        """
        import uuid

        if provider == "ollama":
            ollama_url = config_manager.get("ollama_url", "http://localhost:11434")
            # Format messages for Ollama tool calling
            ollama_msgs = []
            for m in messages:
                role = m.get("role")
                if role == "tool":
                    ollama_msgs.append({
                        "role": "tool",
                        "content": str(m.get("content", ""))
                    })
                elif role == "assistant" and m.get("tool_calls"):
                    # Assistant message containing tool calls
                    ollama_calls = []
                    for tc in m["tool_calls"]:
                        fn = tc.get("function", {})
                        ollama_calls.append({
                            "function": {
                                "name": fn.get("name", tc.get("name", "")),
                                "arguments": fn.get("arguments", tc.get("arguments", {}))
                            }
                        })
                    ollama_msgs.append({
                        "role": "assistant",
                        "content": m.get("content", ""),
                        "tool_calls": ollama_calls
                    })
                else:
                    ollama_msgs.append({
                        "role": role,
                        "content": m.get("content", "")
                    })

            payload = {
                "model": model,
                "messages": ollama_msgs,
                "tools": tools,
                "stream": False,
                "keep_alive": keep_alive
            }

            try:
                with httpx.Client(timeout=120.0) as client:
                    res = client.post(f"{ollama_url}/api/chat", json=payload)
                    if res.status_code != 200:
                        error_text = res.text or ""
                        if "does not support tools" in error_text.lower():
                            raise RuntimeError(
                                f"The selected model '{model}' does not support tool calling, which Agent Mode requires. "
                                "Choose a tool-capable model (for example qwen2.5:1.5b, qwen2.5:3b, or mistral), "
                                "or turn off Agent Mode."
                            )
                        raise RuntimeError(f"Ollama tool-call error ({res.status_code}): {error_text}")
                    data = res.json()
                    msg = data.get("message", {}) or {}
                    content = msg.get("content", "") or ""
                    raw_calls = msg.get("tool_calls") or []

                    parsed_calls = []
                    for idx, call in enumerate(raw_calls):
                        fn = call.get("function", {})
                        fn_name = fn.get("name", "")
                        fn_args = fn.get("arguments", {})
                        if isinstance(fn_args, str):
                            try:
                                fn_args = json.loads(fn_args)
                            except Exception:
                                pass
                        call_id = call.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                        parsed_calls.append({
                            "id": call_id,
                            "name": fn_name,
                            "arguments": fn_args
                        })

                    prompt_tokens = data.get("prompt_eval_count", 0)
                    completion_tokens = data.get("eval_count", 0)

                    return {
                        "content": content,
                        "tool_calls": parsed_calls,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "raw_message": msg
                    }
            except httpx.TimeoutException:
                raise RuntimeError(
                    f"Ollama did not respond within 120 seconds while planning a tool call. "
                    f"Model '{model}' may be too slow or stuck. Try a smaller/faster model or a shorter task."
                )
            except RuntimeError:
                raise
            except Exception as e:
                raise RuntimeError(f"Failed Ollama tool call request: {str(e)}")

        elif provider in ("openai", "groq", "openrouter", "gemini"):
            api_keys = config_manager.get("api_keys", {})
            api_key = api_keys.get(provider, "").strip()
            endpoints = config_manager.get("custom_endpoints", {})
            base_url = endpoints.get(provider, "https://api.openai.com/v1")
            if provider == "gemini":
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai"

            if not api_key:
                raise RuntimeError(f"API key for {provider.capitalize()} is missing. Configure it in Settings.")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            if provider == "openrouter":
                headers["HTTP-Referer"] = "https://github.com/Ali-Sher12/Ollama-Offline-Chatbot"
                headers["X-Title"] = "Ollama Desktop Chatbot"

            # Format messages
            openai_msgs = []
            for m in messages:
                role = m.get("role")
                if role == "tool":
                    openai_msgs.append({
                        "role": "tool",
                        "tool_call_id": m.get("tool_call_id", f"call_{uuid.uuid4().hex[:8]}"),
                        "content": str(m.get("content", ""))
                    })
                elif role == "assistant" and m.get("tool_calls"):
                    openai_calls = []
                    for tc in m["tool_calls"]:
                        fn = tc.get("function", {})
                        name = fn.get("name", tc.get("name", ""))
                        args = fn.get("arguments", tc.get("arguments", {}))
                        arg_str = json.dumps(args) if isinstance(args, dict) else str(args)
                        openai_calls.append({
                            "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {"name": name, "arguments": arg_str}
                        })
                    openai_msgs.append({
                        "role": "assistant",
                        "content": m.get("content", ""),
                        "tool_calls": openai_calls
                    })
                else:
                    openai_msgs.append({
                        "role": role,
                        "content": m.get("content", "")
                    })

            payload = {
                "model": model,
                "messages": openai_msgs,
                "tools": tools,
                "stream": False
            }

            try:
                with httpx.Client(timeout=120.0) as client:
                    res = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    if res.status_code != 200:
                        raise RuntimeError(f"{provider.capitalize()} API error ({res.status_code}): {res.text}")
                    data = res.json()
                    choices = data.get("choices", [])
                    if not choices:
                        return {"content": "", "tool_calls": [], "prompt_tokens": 0, "completion_tokens": 0}

                    msg = choices[0].get("message", {})
                    content = msg.get("content", "") or ""
                    raw_calls = msg.get("tool_calls", []) or []

                    parsed_calls = []
                    for tc in raw_calls:
                        fn = tc.get("function", {})
                        fn_name = fn.get("name", "")
                        raw_args = fn.get("arguments", "{}")
                        if isinstance(raw_args, str):
                            try:
                                args_dict = json.loads(raw_args)
                            except Exception:
                                args_dict = {"raw": raw_args}
                        else:
                            args_dict = raw_args or {}

                        parsed_calls.append({
                            "id": tc.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                            "name": fn_name,
                            "arguments": args_dict
                        })

                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)

                    return {
                        "content": content,
                        "tool_calls": parsed_calls,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "raw_message": msg
                    }
            except Exception as e:
                raise RuntimeError(f"Request to {provider.capitalize()} failed: {str(e)}")

        elif provider == "anthropic":
            api_keys = config_manager.get("api_keys", {})
            api_key = api_keys.get("anthropic", "").strip()
            if not api_key:
                raise RuntimeError("Anthropic API key is missing. Configure it in Settings.")

            # Convert tools to Anthropic format
            anthropic_tools = []
            for t in tools:
                fn = t.get("function", {})
                anthropic_tools.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}})
                })

            system_prompt = ""
            anthropic_messages = []
            for m in messages:
                if m.get("role") == "system":
                    system_prompt += m.get("content", "") + "\n"
                elif m.get("role") == "tool":
                    anthropic_messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": m.get("tool_call_id", ""),
                            "content": str(m.get("content", ""))
                        }]
                    })
                elif m.get("role") == "assistant" and m.get("tool_calls"):
                    blocks = []
                    if m.get("content"):
                        blocks.append({"type": "text", "text": m["content"]})
                    for tc in m["tool_calls"]:
                        fn = tc.get("function", {})
                        blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", f"toolu_{uuid.uuid4().hex[:8]}"),
                            "name": fn.get("name", tc.get("name", "")),
                            "input": fn.get("arguments", tc.get("arguments", {}))
                        })
                    anthropic_messages.append({"role": "assistant", "content": blocks})
                else:
                    anthropic_messages.append({
                        "role": m.get("role"),
                        "content": m.get("content", "")
                    })

            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "max_tokens": 4096,
                "messages": anthropic_messages,
                "tools": anthropic_tools
            }
            if system_prompt.strip():
                payload["system"] = system_prompt.strip()

            try:
                with httpx.Client(timeout=120.0) as client:
                    res = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                    if res.status_code != 200:
                        raise RuntimeError(f"Anthropic API error ({res.status_code}): {res.text}")
                    data = res.json()

                    content_text = ""
                    parsed_calls = []
                    for block in data.get("content", []):
                        if block.get("type") == "text":
                            content_text += block.get("text", "")
                        elif block.get("type") == "tool_use":
                            parsed_calls.append({
                                "id": block.get("id"),
                                "name": block.get("name"),
                                "arguments": block.get("input", {})
                            })

                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("input_tokens", 0)
                    completion_tokens = usage.get("output_tokens", 0)

                    return {
                        "content": content_text,
                        "tool_calls": parsed_calls,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "raw_message": data
                    }
            except Exception as e:
                raise RuntimeError(f"Request to Anthropic failed: {str(e)}")

        else:
            raise RuntimeError(f"Tool calling is unsupported for provider '{provider}'")

    def resolve_vision_model(
        self,
        current_provider: str,
        current_model: str
    ) -> Tuple[str, str]:
        """
        Resolves the appropriate provider and model for multimodal visual analysis.
        Uses configured vision_provider/vision_model if available, or tests current model,
        or falls back to available vision-capable providers.
        """
        cfg_provider = config_manager.get("vision_provider", "auto")
        cfg_model = config_manager.get("vision_model", "")

        if cfg_provider and cfg_provider != "auto" and cfg_model:
            return cfg_provider, cfg_model

        # Check if current provider/model is known vision-capable
        vision_known_models = {
            "openai": ["gpt-4o", "gpt-4o-mini"],
            "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
            "gemini": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        }

        if current_provider in vision_known_models:
            return current_provider, current_model

        # If current is local ollama, check if a vision model is installed
        if current_provider == "ollama":
            ollama_models = [m["id"] for m in self.get_ollama_models()]
            for vm in ["llama3.2-vision", "llava", "moondream", "minicpm-v", "bakllava"]:
                for om in ollama_models:
                    if vm in om.lower():
                        return "ollama", om

        # Check if user has Gemini, OpenAI, or Anthropic API key configured
        api_keys = config_manager.get("api_keys", {})
        if api_keys.get("gemini", "").strip():
            return "gemini", "gemini-2.0-flash"
        if api_keys.get("openai", "").strip():
            return "openai", "gpt-4o-mini"
        if api_keys.get("anthropic", "").strip():
            return "anthropic", "claude-3-5-sonnet-20241022"

        # Fall back to current provider and model
        return current_provider, current_model

    def analyze_image_with_model(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an image to a multimodal vision model (Ollama, OpenAI, Gemini, or Claude).
        Returns {'analysis': str, 'provider': str, 'model': str}.
        """
        import base64

        current_prov = provider or config_manager.get("selected_provider", "ollama")
        current_mod = model or config_manager.get("selected_model", "llama3.2:1b")
        resolved_prov, resolved_mod = self.resolve_vision_model(current_prov, current_mod)

        b64_str = base64.b64encode(image_bytes).decode("utf-8")

        if resolved_prov == "ollama":
            ollama_url = config_manager.get("ollama_url", "http://localhost:11434")
            payload = {
                "model": resolved_mod,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [b64_str]
                    }
                ],
                "stream": False
            }
            try:
                with httpx.Client(timeout=120.0) as client:
                    res = client.post(f"{ollama_url}/api/chat", json=payload)
                    if res.status_code != 200:
                        raise RuntimeError(f"Ollama vision error ({res.status_code}): {res.text}")
                    data = res.json()
                    analysis = data.get("message", {}).get("content", "")
                    return {
                        "success": True,
                        "analysis": analysis,
                        "provider": "ollama",
                        "model": resolved_mod
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Ollama vision request failed: {str(e)}",
                    "provider": "ollama",
                    "model": resolved_mod
                }

        elif resolved_prov in ("openai", "gemini", "groq", "openrouter"):
            api_keys = config_manager.get("api_keys", {})
            api_key = api_keys.get(resolved_prov, "").strip()
            endpoints = config_manager.get("custom_endpoints", {})
            base_url = endpoints.get(resolved_prov, "https://api.openai.com/v1")
            if resolved_prov == "gemini":
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai"

            if not api_key:
                return {
                    "success": False,
                    "error": f"API key for {resolved_prov.capitalize()} is missing for vision analysis.",
                    "provider": resolved_prov,
                    "model": resolved_mod
                }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": resolved_mod,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64_str}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2048
            }

            try:
                with httpx.Client(timeout=120.0) as client:
                    res = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    if res.status_code != 200:
                        return {
                            "success": False,
                            "error": f"{resolved_prov.capitalize()} API error ({res.status_code}): {res.text}",
                            "provider": resolved_prov,
                            "model": resolved_mod
                        }
                    data = res.json()
                    choices = data.get("choices", [])
                    analysis = choices[0].get("message", {}).get("content", "") if choices else ""
                    return {
                        "success": True,
                        "analysis": analysis,
                        "provider": resolved_prov,
                        "model": resolved_mod
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Vision request failed: {str(e)}",
                    "provider": resolved_prov,
                    "model": resolved_mod
                }

        elif resolved_prov == "anthropic":
            api_keys = config_manager.get("api_keys", {})
            api_key = api_keys.get("anthropic", "").strip()
            if not api_key:
                return {
                    "success": False,
                    "error": "Anthropic API key is missing for vision analysis.",
                    "provider": "anthropic",
                    "model": resolved_mod
                }

            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            payload = {
                "model": resolved_mod,
                "max_tokens": 2048,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": b64_str
                                }
                            },
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]
            }

            try:
                with httpx.Client(timeout=120.0) as client:
                    res = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                    if res.status_code != 200:
                        return {
                            "success": False,
                            "error": f"Anthropic API error ({res.status_code}): {res.text}",
                            "provider": "anthropic",
                            "model": resolved_mod
                        }
                    data = res.json()
                    analysis = ""
                    for block in data.get("content", []):
                        if block.get("type") == "text":
                            analysis += block.get("text", "")
                    return {
                        "success": True,
                        "analysis": analysis,
                        "provider": "anthropic",
                        "model": resolved_mod
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Anthropic vision request failed: {str(e)}",
                    "provider": "anthropic",
                    "model": resolved_mod
                }

        return {
            "success": False,
            "error": f"Unsupported vision provider '{resolved_prov}'",
            "provider": resolved_prov,
            "model": resolved_mod
        }

llm_service = LLMService()
