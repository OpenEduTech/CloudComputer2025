from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Passage:
    domain: str
    title: str
    snippet: str
    url: str | None = None


# A tiny offline corpus to guarantee the system works without network/API keys.
# You can extend it freely for demo quality.
SEED_PASSAGES: dict[str, list[Passage]] = {
    "Computer Science": [
        Passage(
            domain="Computer Science",
            title="Information Entropy (seed)",
            snippet="Information entropy (Shannon entropy) measures uncertainty in a random variable and is used in coding and machine learning.",
            url=None,
        ),
        Passage(
            domain="Computer Science",
            title="Cross-entropy (seed)",
            snippet="Cross-entropy compares two probability distributions and is widely used as a loss function in classification tasks.",
            url=None,
        ),
    ],
    "Physics": [
        Passage(
            domain="Physics",
            title="Thermodynamic Entropy (seed)",
            snippet="Thermodynamic entropy quantifies the number of microscopic configurations corresponding to a macroscopic state; it relates to the second law of thermodynamics.",
            url=None,
        )
    ],
    "Mathematics": [
        Passage(
            domain="Mathematics",
            title="Probability distributions (seed)",
            snippet="A probability distribution assigns probabilities to outcomes; many entropy definitions depend on distributions.",
            url=None,
        )
    ],
    "Biology": [
        Passage(
            domain="Biology",
            title="Biological information (seed)",
            snippet="Entropy-like measures appear in bioinformatics for sequence variability and information content.",
            url=None,
        )
    ],
    "Economics": [
        Passage(
            domain="Economics",
            title="Information and uncertainty (seed)",
            snippet="In economics, uncertainty and information affect decision-making; entropy can be used as a diversity/uncertainty measure in some models.",
            url=None,
        )
    ],
}


DEFAULT_DOMAINS = ["Mathematics", "Physics", "Computer Science", "Biology", "Economics"]

