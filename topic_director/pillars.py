"""
Channel-scoped content pillars — configurable per channel.

Each pillar has a name, description, and keyword list used for
lightweight topic classification.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentPillar:
    name: str
    description: str
    keywords: tuple[str, ...]


@dataclass
class ChannelStrategy:
    channel_id: str
    display_name: str
    audience: str
    pillars: list[ContentPillar] = field(default_factory=list)
    difficulty_targets: dict[str, float] = field(default_factory=dict)


SRINI_ON_AI = ChannelStrategy(
    channel_id="srini_on_ai",
    display_name="Srini on AI",
    audience="Tech-curious professionals and developers learning AI/ML concepts",
    pillars=[
        ContentPillar(
            name="AI Fundamentals",
            description="Core concepts every AI learner should know",
            keywords=("artificial intelligence", "machine learning", "neural network",
                      "deep learning", "data", "pattern", "learn", "model", "algorithm",
                      "basics", "fundamentals", "introduction"),
        ),
        ContentPillar(
            name="LLM Concepts",
            description="How large language models work under the hood",
            keywords=("llm", "language model", "transformer", "attention", "token",
                      "context window", "prompt", "embedding", "gpt", "claude",
                      "inference", "generation", "decoder", "encoder"),
        ),
        ContentPillar(
            name="AI Agents / Agentic Systems",
            description="Autonomous AI agents, agentic patterns, multi-agent systems",
            keywords=("agent", "agents", "agentic", "autonomous", "multi-agent", "orchestrat",
                      "plan", "reason", "decide", "loop", "react", "reflection", "tool use"),
        ),
        ContentPillar(
            name="RAG / Knowledge Systems",
            description="Retrieval-augmented generation and knowledge management",
            keywords=("rag", "retrieval", "augmented", "knowledge", "vector",
                      "embedding", "search", "document", "chunk", "index",
                      "hallucination", "ground"),
        ),
        ContentPillar(
            name="AI Tools / Function Calling",
            description="How AI interacts with external tools and APIs",
            keywords=("tool", "function calling", "api", "plugin", "action",
                      "integration", "mcp", "protocol", "interface"),
        ),
        ContentPillar(
            name="Model Training / Reasoning",
            description="How models are trained, fine-tuned, and reason",
            keywords=("train", "fine-tune", "rlhf", "reward", "loss", "gradient",
                      "reasoning", "chain of thought", "think", "pretraining",
                      "dataset", "benchmark", "evaluation"),
        ),
        ContentPillar(
            name="AI Infrastructure / Cost / Tokens",
            description="Practical infrastructure: cost, tokens, deployment, scaling",
            keywords=("cost", "token", "pricing", "latency", "throughput", "deploy",
                      "infrastructure", "scale", "gpu", "compute", "batch",
                      "rate limit", "api key", "billing"),
        ),
        ContentPillar(
            name="Practical AI Concepts",
            description="Applied AI patterns people can use today",
            keywords=("prompt engineering", "few-shot", "zero-shot", "template",
                      "workflow", "automat", "use case", "practical", "build",
                      "tutorial", "how to", "step"),
        ),
        ContentPillar(
            name="Emerging AI Concepts",
            description="Cutting-edge research and next-generation AI ideas",
            keywords=("emerging", "frontier", "multimodal", "vision", "audio",
                      "video", "world model", "alignment", "safety", "regulation",
                      "agi", "synthetic", "distillation"),
        ),
    ],
    difficulty_targets={
        "beginner": 0.35,
        "intermediate": 0.45,
        "advanced": 0.20,
    },
)

CHANNEL_STRATEGIES: dict[str, ChannelStrategy] = {
    "srini_on_ai": SRINI_ON_AI,
}


def get_strategy(channel_id: str) -> ChannelStrategy:
    if channel_id not in CHANNEL_STRATEGIES:
        raise KeyError(f"No strategy defined for channel '{channel_id}'")
    return CHANNEL_STRATEGIES[channel_id]
