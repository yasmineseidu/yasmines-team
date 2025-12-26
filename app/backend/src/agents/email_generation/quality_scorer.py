"""
Email Quality Scorer - Evaluates generated emails across multiple dimensions.

Scores emails on:
- Personalization (30% weight)
- Clarity (25% weight)
- Length (15% weight)
- CTA Quality (15% weight)
- Tone (15% weight)
"""

import logging
import re

from src.agents.email_generation.frameworks import (
    AVOID_PATTERNS,
    EXCESSIVE_FLATTERY_PATTERNS,
    SOFT_CTAS,
)
from src.agents.email_generation.schemas import (
    GeneratedEmail,
    LeadContext,
    QualityScore,
)

logger = logging.getLogger(__name__)


class EmailQualityScorer:
    """
    Scores email quality across multiple dimensions.

    Scoring Weights:
    - Personalization: 30%
    - Clarity: 25%
    - Length: 15%
    - CTA Quality: 15%
    - Tone: 15%
    """

    def __init__(self) -> None:
        """Initialize the quality scorer."""
        self.avoid_patterns = [p.lower() for p in AVOID_PATTERNS]
        self.flattery_patterns = [p.lower() for p in EXCESSIVE_FLATTERY_PATTERNS]
        self.soft_cta_patterns = [cta.lower() for cta in SOFT_CTAS]

    def score_email(
        self,
        email: GeneratedEmail,
        lead_context: LeadContext,
    ) -> QualityScore:
        """
        Score an email across all quality dimensions.

        Args:
            email: The generated email to score.
            lead_context: Context about the lead for personalization scoring.

        Returns:
            QualityScore with breakdown and total.
        """
        return QualityScore(
            personalization=self._score_personalization(email, lead_context),
            clarity=self._score_clarity(email),
            length=self._score_length(email),
            cta_quality=self._score_cta(email),
            tone=self._score_tone(email),
        )

    def _score_personalization(
        self,
        email: GeneratedEmail,
        lead_context: LeadContext,
    ) -> float:
        """
        Score personalization level (0-10).

        Criteria:
        - uses_specific_research: 10
        - mentions_company_context: 8
        - references_role: 5
        - generic: 0
        """
        score = 0.0
        full_text = email.full_email.lower()

        # Check for specific research usage (highest value)
        uses_research = False
        if lead_context.lead_research:
            headline = lead_context.lead_research.get("headline", "").lower()
            interests = lead_context.lead_research.get("key_interests", [])
            if headline and len(headline) > 5 and headline[:20] in full_text:
                uses_research = True
            for interest in interests[:3]:
                if interest.lower() in full_text:
                    uses_research = True
                    break

        if lead_context.company_research:
            angle = lead_context.company_research.get("personalization_angle", "").lower()
            if angle and len(angle) > 10 and angle[:30] in full_text:
                uses_research = True

        if uses_research:
            score = 10.0
        # Check for company context mention (medium value)
        elif lead_context.company_name.lower() in full_text:
            score = 8.0
        # Check for role/title reference (lower value)
        elif lead_context.title.lower() in full_text:
            score = 5.0
        # Check for first name usage
        elif lead_context.first_name.lower() in full_text:
            score = 3.0
        # Completely generic
        else:
            score = 0.0

        # Bonus for using multiple personalization elements
        personalization_count = 0
        if lead_context.first_name.lower() in full_text:
            personalization_count += 1
        if lead_context.company_name.lower() in full_text:
            personalization_count += 1
        if lead_context.title.lower() in full_text:
            personalization_count += 1

        if personalization_count >= 2 and score < 10:
            score = min(10.0, score + 1.0)

        return score

    def _score_clarity(self, email: GeneratedEmail) -> float:
        """
        Score clarity of the email (0-10).

        Criteria:
        - clear_value_prop: 10
        - easy_to_understand: 8
        - confusing: 0
        """
        score = 8.0  # Start with assumption of decent clarity
        body = email.body

        # Check sentence length (shorter is clearer)
        sentences = re.split(r"[.!?]+", body)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_sentence_length <= 15:
                score = 10.0
            elif avg_sentence_length <= 20:
                score = 8.0
            elif avg_sentence_length <= 25:
                score = 6.0
            else:
                score = 4.0

        # Check for jargon/complexity
        jargon_words = [
            "synergy",
            "leverage",
            "paradigm",
            "holistic",
            "ecosystem",
            "bandwidth",
            "circle back",
            "deep dive",
            "move the needle",
        ]
        jargon_count = sum(1 for word in jargon_words if word in body.lower())
        score -= jargon_count * 1.5

        # Check for clear structure
        has_clear_opening = len(email.opening_line) > 10
        has_clear_cta = len(email.cta) > 10
        if has_clear_opening and has_clear_cta:
            score += 1.0

        return max(0.0, min(10.0, score))

    def _score_length(self, email: GeneratedEmail) -> float:
        """
        Score email length (0-10).

        Criteria:
        - optimal_50_100_words: 10
        - acceptable_100_150: 7
        - too_short_under_50: 4
        - too_long_over_150: 3
        """
        word_count = len(email.body.split())

        if 50 <= word_count <= 100:
            return 10.0
        elif 100 < word_count <= 150:
            return 7.0
        elif word_count < 50:
            return 4.0
        else:  # > 150
            return 3.0

    def _score_cta(self, email: GeneratedEmail) -> float:
        """
        Score CTA quality (0-10).

        Criteria:
        - soft_low_friction: 10
        - clear_ask: 7
        - pushy_or_vague: 3
        """
        cta = email.cta.lower()

        # Check for soft CTA patterns
        is_soft = any(pattern[:20] in cta for pattern in self.soft_cta_patterns)
        if is_soft:
            return 10.0

        # Check for question mark (soft ask indicator)
        if "?" in cta:
            # Check for pushy patterns
            pushy_patterns = [
                "book a call",
                "schedule a demo",
                "buy now",
                "limited time",
                "act now",
                "don't miss",
            ]
            is_pushy = any(p in cta for p in pushy_patterns)
            if is_pushy:
                return 3.0
            return 7.0

        # No question mark - likely too direct
        if len(cta) > 10:
            return 5.0

        # Very short or missing CTA
        return 3.0

    def _score_tone(self, email: GeneratedEmail) -> float:
        """
        Score email tone (0-10).

        Criteria:
        - conversational_human: 10
        - professional_warm: 8
        - corporate_stiff: 3
        - too_casual: 4
        """
        full_text = email.full_email.lower()
        score = 8.0  # Default to professional

        # Check for avoided patterns (corporate/stiff)
        avoid_count = sum(1 for p in self.avoid_patterns if p in full_text)
        if avoid_count > 0:
            score -= avoid_count * 2.0

        # Check for excessive flattery
        flattery_count = sum(1 for p in self.flattery_patterns if p in full_text)
        if flattery_count > 1:
            score -= flattery_count * 1.5

        # Check for conversational indicators
        conversational_markers = [
            "curious",
            "wondering",
            "thought",
            "noticed",
            "sounds like",
            "seems like",
        ]
        conv_count = sum(1 for m in conversational_markers if m in full_text)
        if conv_count > 0:
            score += min(conv_count, 2)

        # Check for too casual
        casual_patterns = ["hey!", "yo", "sup", "gonna", "wanna", "gotta"]
        casual_count = sum(1 for p in casual_patterns if p in full_text)
        if casual_count > 1:
            score = 4.0

        return max(0.0, min(10.0, score))

    def should_regenerate(self, score: QualityScore, threshold: int) -> bool:
        """
        Determine if email should be regenerated based on score.

        Args:
            score: The quality score.
            threshold: Minimum acceptable score.

        Returns:
            True if email should be regenerated.
        """
        return score.total_score < threshold

    def get_improvement_suggestions(self, score: QualityScore) -> list[str]:
        """
        Get suggestions for improving the email.

        Args:
            score: The quality score breakdown.

        Returns:
            List of improvement suggestions.
        """
        suggestions = []

        if score.personalization < 5:
            suggestions.append(
                "Add more specific personalization - reference their work, company, or role"
            )

        if score.clarity < 5:
            suggestions.append("Simplify sentences and remove jargon for better clarity")

        if score.length < 5:
            suggestions.append("Adjust email length - aim for 50-100 words in the body")

        if score.cta_quality < 5:
            suggestions.append("Use a softer CTA - ask a question instead of demanding action")

        if score.tone < 5:
            suggestions.append("Adjust tone - sound more conversational, less corporate")

        return suggestions


# Singleton instance for reuse
_scorer_instance: EmailQualityScorer | None = None


def get_quality_scorer() -> EmailQualityScorer:
    """Get or create the quality scorer singleton."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = EmailQualityScorer()
    return _scorer_instance
