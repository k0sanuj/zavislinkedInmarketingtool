"""
Service: AI Role Matching

Uses an LLM (Claude or OpenAI) to evaluate whether an employee's job title
matches the target roles. Also provides role suggestions — e.g. if the user
says "clinic administrator", the AI can suggest related roles like
"Practice Manager", "Operations Director", "Office Manager", etc.
"""

import logging
from typing import List, Optional, Tuple

from app.core.config import settings
from app.core.ontology import MatchConfidence

logger = logging.getLogger(__name__)


ROLE_MATCH_SYSTEM_PROMPT = """You are a job title matching assistant for a healthcare B2B sales tool.
Your job is to determine if an employee's job title matches the target roles that a salesperson is looking for.

Consider:
- Exact matches (e.g. "Clinic Administrator" matches "Clinic Administrator")
- Semantic equivalents (e.g. "Practice Manager" matches "Clinic Administrator")
- Hierarchical matches (e.g. "Director of Operations" is senior to but relevant to "Operations Manager")
- Industry-specific titles (e.g. "Chief Dental Officer" in a dental clinic is a decision-maker)

Respond with JSON only:
{
  "is_match": true/false,
  "confidence": "exact" | "high" | "medium" | "low" | "no_match",
  "reasoning": "brief explanation",
  "matched_role": "which target role this matches (or null)"
}"""


ROLE_SUGGESTION_PROMPT = """You are a healthcare industry job title expert. Given a set of target roles,
suggest additional related job titles that might be relevant for B2B outreach in the healthcare/clinic space.

Think about:
- Equivalent titles across different company sizes
- Regional variations (US, UK, Middle East naming conventions)
- Decision-makers and influencers in healthcare purchasing
- C-suite, management, and operational roles

Respond with JSON only:
{
  "suggested_roles": ["Role 1", "Role 2", ...],
  "reasoning": "brief explanation of why these roles are relevant"
}"""


async def evaluate_role_match(
    employee_title: str,
    target_roles: List[str],
    custom_prompt: Optional[str] = None,
) -> Tuple[bool, MatchConfidence, str, Optional[str]]:
    """
    Use AI to determine if an employee's job title matches target roles.

    Returns:
        Tuple of (is_match, confidence, reasoning, matched_role)
    """
    if not employee_title:
        return False, MatchConfidence.NO_MATCH, "No job title available", None

    # First try rule-based matching for speed
    rule_result = _rule_based_match(employee_title, target_roles)
    if rule_result[0]:  # is_match
        return rule_result

    # Fall back to AI matching
    user_message = f"""Employee job title: "{employee_title}"
Target roles: {target_roles}
{f'Additional context: {custom_prompt}' if custom_prompt else ''}

Is this employee's role a match for the target roles?"""

    try:
        result = await _call_llm(ROLE_MATCH_SYSTEM_PROMPT, user_message)
        import json
        parsed = json.loads(result)
        return (
            parsed.get("is_match", False),
            MatchConfidence(parsed.get("confidence", "no_match")),
            parsed.get("reasoning", ""),
            parsed.get("matched_role"),
        )
    except Exception as e:
        logger.error(f"AI role matching failed: {e}")
        return False, MatchConfidence.NO_MATCH, f"AI evaluation failed: {e}", None


async def suggest_related_roles(
    target_roles: List[str],
    industry: str = "healthcare",
) -> Tuple[List[str], str]:
    """
    Use AI to suggest additional related job titles.

    Returns:
        Tuple of (suggested_roles list, reasoning)
    """
    user_message = f"""Target roles: {target_roles}
Industry: {industry}

Suggest additional related job titles that would be relevant for B2B outreach."""

    try:
        result = await _call_llm(ROLE_SUGGESTION_PROMPT, user_message)
        import json
        parsed = json.loads(result)
        return parsed.get("suggested_roles", []), parsed.get("reasoning", "")
    except Exception as e:
        logger.error(f"AI role suggestion failed: {e}")
        return [], f"AI suggestion failed: {e}"


def _rule_based_match(
    employee_title: str, target_roles: List[str]
) -> Tuple[bool, MatchConfidence, str, Optional[str]]:
    """Fast rule-based matching before falling back to AI."""
    title_lower = employee_title.lower().strip()

    for role in target_roles:
        role_lower = role.lower().strip()

        # Exact match
        if title_lower == role_lower:
            return True, MatchConfidence.EXACT, "Exact title match", role

        # Contains match
        if role_lower in title_lower or title_lower in role_lower:
            return True, MatchConfidence.HIGH, f"Title contains '{role}'", role

        # Word overlap
        role_words = set(role_lower.split())
        title_words = set(title_lower.split())
        overlap = role_words & title_words
        # Remove common filler words
        filler = {"of", "the", "and", "in", "at", "for", "a", "an", "&"}
        meaningful_overlap = overlap - filler
        if len(meaningful_overlap) >= 2:
            return True, MatchConfidence.MEDIUM, f"Significant word overlap: {meaningful_overlap}", role

    return False, MatchConfidence.NO_MATCH, "No rule-based match found", None


async def _call_llm(system_prompt: str, user_message: str) -> str:
    """Call LLM API (tries Anthropic first, then OpenAI)."""
    if settings.ANTHROPIC_API_KEY:
        return await _call_anthropic(system_prompt, user_message)
    elif settings.OPENAI_API_KEY:
        return await _call_openai(system_prompt, user_message)
    else:
        raise RuntimeError("No AI API key configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY)")


async def _call_anthropic(system_prompt: str, user_message: str) -> str:
    """Call Anthropic Claude API."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


async def _call_openai(system_prompt: str, user_message: str) -> str:
    """Call OpenAI API."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=500,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content
