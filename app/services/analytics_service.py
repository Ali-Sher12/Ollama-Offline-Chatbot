from typing import Dict, Any, Optional

PRICING_PER_MILLION = {
    # Provider: { prompt_cost_per_m, completion_cost_per_m }
    "ollama": (0.0, 0.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "llama-3.3-70b": (0.59, 0.79),
    "default_online": (1.00, 3.00)
}

class AnalyticsService:
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token count estimation (~4 characters per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    @staticmethod
    def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        if provider == "ollama":
            return 0.0
        
        # Match model against pricing keys
        matched_key = "default_online"
        model_lower = model.lower()
        for key in PRICING_PER_MILLION:
            if key in model_lower:
                matched_key = key
                break
        
        p_rate, c_rate = PRICING_PER_MILLION.get(matched_key, (1.0, 3.0))
        cost = (prompt_tokens / 1_000_000 * p_rate) + (completion_tokens / 1_000_000 * c_rate)
        return round(cost, 6)

    @staticmethod
    def get_budget_status(total_tokens_used: int, budget_limit: int) -> Dict[str, Any]:
        """Evaluate token budget limit status."""
        if budget_limit <= 0:
            return {
                "budget_limit": 0,
                "tokens_used": total_tokens_used,
                "remaining_tokens": None,
                "percentage_used": 0.0,
                "is_approaching_limit": False,
                "is_exceeded": False
            }
        
        remaining = max(0, budget_limit - total_tokens_used)
        pct = min(100.0, round((total_tokens_used / budget_limit) * 100.0, 1))
        
        return {
            "budget_limit": budget_limit,
            "tokens_used": total_tokens_used,
            "remaining_tokens": remaining,
            "percentage_used": pct,
            "is_approaching_limit": pct >= 80.0,
            "is_exceeded": total_tokens_used >= budget_limit
        }

analytics_service = AnalyticsService()
