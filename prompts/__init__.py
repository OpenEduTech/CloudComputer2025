"""Prompt模板库"""

from .discovery_prompts import DiscoveryPrompt
from .verification_prompts import VerificationPrompt
from .graph_prompts import GraphPrompt

__all__ = ["DiscoveryPrompt", "VerificationPrompt", "GraphPrompt"]
