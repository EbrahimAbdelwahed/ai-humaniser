from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from academic_engine.config import EngineConfig
from academic_engine.schemas import AcademicProfile, CandidateRevision, SemanticRepresentation, Strategy
from academic_engine.utils import extract_citations, extract_numbers, sentence_split, word_tokens


class LLMProvider(ABC):
    @abstractmethod
    def complete_json(self, *, system: str, user: str, schema_name: str) -> dict[str, Any]:
        raise NotImplementedError


class DeepSeekProvider(LLMProvider):
    def __init__(self, config: EngineConfig) -> None:
        if not config.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeekProvider")
        self.config = config

    def complete_json(self, *, system: str, user: str, schema_name: str) -> dict[str, Any]:
        url = f"{self.config.deepseek_base_url.rstrip('/')}/v1/chat/completions"
        payload = {
            "model": self.config.deepseek_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.35,
        }
        headers = {"Authorization": f"Bearer {self.config.deepseek_api_key}"}
        with httpx.Client(timeout=60) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{schema_name} response was not valid JSON") from exc


class DeterministicMockProvider(LLMProvider):
    def complete_json(self, *, system: str, user: str, schema_name: str) -> dict[str, Any]:
        text = self.extract_text(user)
        if schema_name == "SemanticRepresentation":
            return self.semantic(text).model_dump()
        if schema_name == "AcademicProfile":
            return self.profile(text).model_dump()
        if schema_name == "CandidateRevisions":
            return {"candidates": [candidate.model_dump(mode="json") for candidate in self.candidates(text)]}
        if schema_name == "CandidateRevision":
            strategy = self.extract_strategy(user) or Strategy.conservative_academic
            candidate_id = self.extract_candidate_id(user) or "candidate-1"
            return self.rewrite(text, strategy, candidate_id).model_dump(mode="json")
        if schema_name == "RefinedCandidate":
            strategy = Strategy.natural_scholarly
            return self.rewrite(text, strategy, "refined-cycle").model_dump(mode="json")
        raise ValueError(f"Unsupported mock schema: {schema_name}")

    def extract_text(self, user: str) -> str:
        text = user.split("TEXT:", 1)[-1].strip() if "TEXT:" in user else user.strip()
        if "\n\nReturn JSON only." in text:
            text = text.split("\n\nReturn JSON only.", 1)[0].strip()
        return text

    def extract_strategy(self, user: str) -> Strategy | None:
        for line in user.splitlines():
            if line.startswith("STRATEGY:"):
                raw = line.split(":", 1)[1].strip()
                try:
                    return Strategy(raw)
                except ValueError:
                    return None
        return None

    def extract_candidate_id(self, user: str) -> str | None:
        for line in user.splitlines():
            if line.startswith("CANDIDATE_ID:"):
                return line.split(":", 1)[1].strip() or None
        return None

    def semantic(self, text: str) -> SemanticRepresentation:
        citations = extract_citations(text)
        numbers = extract_numbers(text)
        sentences = sentence_split(text)
        terms = [
            word
            for word in sorted(set(word_tokens(text)), key=str.lower)
            if len(word) > 8 and word[0].isalpha()
        ][:10]
        return SemanticRepresentation(
            claims=sentences[:5],
            entities=[word for word in word_tokens(text) if word[:1].isupper()][:10],
            relations=[],
            disciplinary_terms=terms,
            citations_or_references=citations,
            exact_citation_spans=citations,
            numeric_values=numbers,
            argument_structure=[f"Paragraph {index + 1}: {paragraph[:90]}" for index, paragraph in enumerate(text.split("\n\n"))],
            uncertainty_markers=[marker for marker in ["may", "might", "could", "suggests"] if marker in text.lower()],
            non_negotiable_preservation_items=citations + numbers + terms[:5],
        )

    def profile(self, text: str) -> AcademicProfile:
        lower = text.lower()
        discipline = "general academic"
        for needle, value in {
            "policy": "political science",
            "patient": "medicine/health sciences",
            "media": "communication/media studies",
            "enzyme": "biology/life sciences",
            "market": "economics/business",
            "classroom": "education",
            "algorithm": "computer science",
        }.items():
            if needle in lower:
                discipline = value
                break
        return AcademicProfile(
            discipline=discipline,
            document_type="essay",
            author_needs=["clarity", "scholarly voice", "cohesion"],
            style_constraints=["preserve citations exactly", "do not add references"],
            inferred_fields=["discipline", "document_type", "audience", "writing_level"],
        )

    def candidates(self, text: str) -> list[CandidateRevision]:
        strategies = [
            Strategy.conservative_academic,
            Strategy.natural_scholarly,
            Strategy.enhanced_clarity,
            Strategy.structural_optimization,
            Strategy.stylistic_maturation,
            Strategy.non_native_refinement,
            Strategy.precision_oriented,
        ]
        return [self.rewrite(text, strategy, f"candidate-{index + 1}") for index, strategy in enumerate(strategies)]

    def rewrite(self, text: str, strategy: Strategy, candidate_id: str) -> CandidateRevision:
        stripped = " ".join(text.split())
        prefix = {
            Strategy.conservative_academic: "This passage can be stated more carefully:",
            Strategy.natural_scholarly: "The argument can be expressed in a measured scholarly voice:",
            Strategy.enhanced_clarity: "The central point can be clarified as follows:",
            Strategy.structural_optimization: "Organized around its main claim, the passage argues that",
            Strategy.stylistic_maturation: "In a more mature academic register, the passage indicates that",
            Strategy.non_native_refinement: "With smoother academic phrasing, the passage explains that",
            Strategy.precision_oriented: "More precisely, the passage maintains that",
        }[strategy]
        rewritten = f"{prefix} {stripped}"
        return CandidateRevision(
            candidate_id=candidate_id,
            rewritten_text=rewritten,
            strategy=strategy,
            intended_improvements=["improve academic tone", "increase clarity", "retain original claims"],
            preservation_notes=["citation spans and numeric values are copied from the source text"],
            risk_flags=[],
        )


def provider_from_config(config: EngineConfig) -> LLMProvider:
    if config.use_mock_provider:
        return DeterministicMockProvider()
    return DeepSeekProvider(config)
