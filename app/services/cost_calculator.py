"""Lightweight cost calculation service for LLM API usage."""

from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)

# Pricing per 1M tokens (as of 2024)
# Format: {model_name: {"input": price_per_1M, "output": price_per_1M}}
PRICING_MODELS: Dict[str, Dict[str, float]] = {
    # OpenAI models
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Embeddings
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
    # Hugging Face models (if using API, typically free or very low cost)
    "HuggingFaceH4/zephyr-7b-beta": {"input": 0.0, "output": 0.0},  # Local/self-hosted
    "meta-llama/Llama-3.2-3B-Instruct": {"input": 0.0, "output": 0.0},  # Local/self-hosted
    "google/gemma-2b-it": {"input": 0.0, "output": 0.0},  # Local/self-hosted
    # TGI models (local, no cost)
    "tgi": {"input": 0.0, "output": 0.0},
}


def calculate_cost(
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    provider: Optional[str] = None,
) -> float:
    """
    Calculate cost in USD for LLM API usage.

    Args:
        model: Model name (e.g., 'gpt-4o-mini', 'text-embedding-3-small')
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        provider: Optional provider name (for fallback pricing)

    Returns:
        Cost in USD (rounded to 6 decimal places)
    """
    if input_tokens == 0 and output_tokens == 0:
        return 0.0

    # Normalize model name (remove provider prefix if present)
    model_normalized = model.lower()
    if "/" in model_normalized:
        # For Hugging Face models, use the full path
        pass
    else:
        # Remove common prefixes
        model_normalized = model_normalized.replace("openai/", "").replace("openai:", "")

    # Try to find pricing for this model
    pricing = PRICING_MODELS.get(model_normalized)

    # If not found, try to match by partial name
    if not pricing:
        for model_key, model_pricing in PRICING_MODELS.items():
            if model_key in model_normalized or model_normalized in model_key:
                pricing = model_pricing
                break

    # If still not found, use default based on provider
    if not pricing:
        if provider and provider.lower() == "openai":
            # Default to GPT-3.5-turbo pricing for unknown OpenAI models
            pricing = PRICING_MODELS.get("gpt-3.5-turbo", {"input": 0.50, "output": 1.50})
        else:
            # Default to free for unknown models (likely local/self-hosted)
            pricing = {"input": 0.0, "output": 0.0}
            logger.debug(
                "unknown_model_pricing",
                model=model,
                provider=provider,
                using_default="free",
            )

    # Calculate cost
    input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0.0)
    output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0.0)
    total_cost = input_cost + output_cost

    return round(total_cost, 6)


def calculate_total_cost_from_operations(
    llm_operations: list[Dict[str, Any]],
) -> tuple[float, Optional[str]]:
    """
    Calculate total cost from a list of LLM operations and determine primary model.

    Args:
        llm_operations: List of LLM operation dicts with model, input_tokens, output_tokens

    Returns:
        Tuple of (total_cost_usd, primary_model_name)
    """
    if not llm_operations:
        return 0.0, None

    total_cost = 0.0
    primary_model = None
    max_tokens = 0

    for op in llm_operations:
        model = op.get("model", "unknown")
        input_tokens = op.get("input_tokens", 0) or 0
        output_tokens = op.get("output_tokens", 0) or 0

        # Determine primary model (the one with most tokens)
        op_tokens = input_tokens + output_tokens
        if op_tokens > max_tokens:
            max_tokens = op_tokens
            primary_model = model

        # Calculate cost for this operation
        cost = calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        total_cost += cost

    return round(total_cost, 6), primary_model

