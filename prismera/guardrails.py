"""Output Guardrails for PrismEra agents.

Implements the Anti-AI lexicon interceptor and automated rewriting engine
to ensure all generated admissions essays and drafts adhere strictly to
PrismEra's authentic, high-SNR brand voice guidelines.
"""

from __future__ import annotations
import re
from typing import List, Tuple, Optional, Any, Dict

from prismera.prompts.brand_voice import (
    ANTI_AI_BANNED_WORDS,
    ANTI_AI_REPLACEMENTS,
)


class AntiAIGuardrail:
    """Post-generation guardrail scanning for banned AI clichés and triggering rewrites."""

    def __init__(
        self,
        banned_words: Optional[List[str]] = None,
        replacements: Optional[Dict[str, str]] = None,
    ):
        self.banned_words = sorted(
            banned_words or ANTI_AI_BANNED_WORDS,
            key=lambda w: len(w),
            reverse=True,  # Match longer phrases first (e.g. "rich tapestry" before "tapestry")
        )
        self.replacements = replacements or ANTI_AI_REPLACEMENTS

    def scan(self, text: str) -> List[str]:
        """Scan text for Anti-AI banned words/phrases.

        Returns a list of unique banned phrases found in the text.
        """
        if not text:
            return []

        hits: List[str] = []
        for phrase in self.banned_words:
            # Match word boundaries, allowing multi-word whitespace variations
            pattern_str = r"\b" + r"\s+".join(re.escape(w) for w in phrase.split()) + r"\b"
            if re.search(pattern_str, text, re.IGNORECASE):
                hits.append(phrase)

        return hits

    def rewrite_deterministic(self, text: str, violations: List[str]) -> str:
        """Deterministically substitute AI clichés with sharp academic action verbs."""
        rewritten = text
        for phrase in sorted(violations, key=lambda w: len(w), reverse=True):
            replacement = self.replacements.get(phrase.lower(), "examine")
            pattern_str = r"\b" + r"\s+".join(re.escape(w) for w in phrase.split()) + r"\b"

            def _repl(match: re.Match) -> str:
                matched_text = match.group(0)
                if matched_text.isupper():
                    return replacement.upper()
                if matched_text[0].isupper():
                    return replacement.capitalize()
                return replacement

            rewritten = re.sub(pattern_str, _repl, rewritten, flags=re.IGNORECASE)

        return rewritten

    def rewrite_with_llm(self, text: str, violations: List[str], llm: Any) -> str:
        """Instruct the LLM to rewrite text eliminating all banned AI clichés."""
        banned_list_str = ", ".join(f"'{v}'" for v in violations)
        system_prompt = (
            "You are PrismEra's Chief Narrative Editor (The Disperser Guardrail). "
            "A draft has violated our Anti-AI Brand Voice guidelines by including plastic, cliché expressions.\n"
            "Your task: Rewrite the text to eliminate ALL banned words while strictly preserving "
            "all factual details, course codes, technical metrics, and narrative flow.\n"
            f"BANNED WORDS TO REMOVE: [{banned_list_str}]\n"
            "Replace them with precise, action-oriented engineering and academic prose. "
            "Return ONLY the rewritten text without conversational preamble."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please rewrite this draft removing all banned words:\n\n{text}"},
        ]

        try:
            rewritten = llm.generate(messages, temperature=0.1).strip()
            # If the markdown code block was wrapped, extract content if needed
            if rewritten.startswith("```") and rewritten.endswith("```"):
                lines = rewritten.splitlines()
                if len(lines) >= 3:
                    rewritten = "\n".join(lines[1:-1]).strip()

            # Post-check: If LLM still slipped in any banned word, clean deterministically
            remaining_hits = self.scan(rewritten)
            if remaining_hits:
                rewritten = self.rewrite_deterministic(rewritten, remaining_hits)
            return rewritten
        except Exception:
            # Fallback to deterministic rewrite on any error
            return self.rewrite_deterministic(text, violations)

    def apply(
        self, text: str, llm: Optional[Any] = None
    ) -> Tuple[str, bool, List[str]]:
        """Execute post-generation guardrail check and rewrite if violations are found.

        Returns:
            (cleansed_text, was_rewritten, list_of_violations_found)
        """
        violations = self.scan(text)
        if not violations:
            return text, False, []

        is_mock = getattr(llm, "is_mock", True) if llm else True

        if llm and not is_mock:
            rewritten = self.rewrite_with_llm(text, violations, llm)
        else:
            rewritten = self.rewrite_deterministic(text, violations)

        return rewritten, True, violations
