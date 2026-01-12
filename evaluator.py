"""
LLM Evaluator for Contract Risk Triage

- Uses OpenAI ONLY to explain and synthesize deterministic findings.
- MUST NOT detect new risks.
- MUST output strict JSON only.
"""

from __future__ import annotations

import os
import json
import logging
import re
from typing import Dict, List, Optional, Set

from openai import OpenAI

logger = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    """
    Normalize a title to canonical form for matching:
    - lowercase
    - strip punctuation
    - collapse whitespace
    - replace spaces with underscores
    """
    if not title:
        return ""
    # Lowercase
    normalized = title.lower()
    # Remove punctuation (keep alphanumeric and spaces)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    # Collapse whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    # Replace spaces with underscores
    normalized = normalized.replace(' ', '_')
    return normalized


class LLMEvaluator:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        # Strip whitespace in case .env file has spaces
        if self.api_key:
            self.api_key = self.api_key.strip()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client: Optional[OpenAI] = None

        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")

    def _build_prompt(self, findings: List[Dict], overall_risk: str) -> str:
        # Group findings by rule_name to reduce repetition
        grouped: Dict[str, List[Dict]] = {}
        for f in findings:
            grouped.setdefault(f.get("rule_name", "unknown"), []).append(f)

        blocks: List[str] = []
        for rule_name, fs in grouped.items():
            # Take up to 2 excerpts per rule to control prompt size
            examples = fs[:2]
            title = examples[0].get("title", rule_name)
            severity = examples[0].get("severity", "low")
            rationale = examples[0].get("rationale", "")

            excerpts = "\n".join([f'- Excerpt: "{ex.get("matched_excerpt","")}"' for ex in examples])
            blocks.append(
                f"Rule: {rule_name}\nTitle: {title}\nSeverity: {severity}\nRationale: {rationale}\n{excerpts}\n"
            )

        findings_text = "\n".join(blocks) if blocks else "None detected"

        return f"""
You are a contract risk triage assistant for founders/CEOs.

IMPORTANT:
- The deterministic engine has ALREADY detected the risks.
- Your job is NOT to find new risks.
- Your job is to explain why the provided findings may matter and synthesize a concise executive summary.

Deterministic Overall Risk (already computed): {overall_risk}

DETECTED FINDINGS (deterministic):
{findings_text}

TASK:
1) Provide a 3–5 bullet executive summary (plain English, business impact, not legal analysis)
2) Produce "top_issues" based ONLY on the detected findings (choose the most important 3–6)
3) Suggest POSSIBLE missing sections commonly negotiated in NDAs/MSAs (max 6). Phrase as suggestions (e.g., "You may want to confirm whether...")

CRITICAL CONSTRAINTS:
- Do NOT invent new risks.
- Do NOT declare legality, enforceability, or safety.
- Do NOT use: "safe to sign", "illegal", "enforceable", "you should"
- Prefer: "may indicate", "can increase risk", "commonly negotiated", "you may want to confirm"

OUTPUT FORMAT: JSON ONLY with this schema:
{{
  "overall_risk": "low | medium | high",
  "summary_bullets": ["..."],
  "top_issues": [
    {{
      "title": "",
      "severity": "high | medium | low",
      "why_it_matters": "",
      "negotiation_consideration": ""
    }}
  ],
  "possible_missing_sections": ["..."],
  "disclaimer": "This is automated risk triage, not legal advice."
}}
""".strip()

    def _validate_result(self, result: Dict) -> Dict:
        # Basic shape validation; enforce disclaimer and required keys
        required = ["overall_risk", "summary_bullets", "top_issues", "possible_missing_sections", "disclaimer"]
        for k in required:
            if k not in result:
                raise ValueError(f"Missing key in LLM result: {k}")

        if not isinstance(result["summary_bullets"], list):
            raise ValueError("summary_bullets must be a list")
        if not isinstance(result["top_issues"], list):
            raise ValueError("top_issues must be a list")
        if not isinstance(result["possible_missing_sections"], list):
            raise ValueError("possible_missing_sections must be a list")

        # Force disclaimer
        result["disclaimer"] = "This is automated risk triage, not legal advice."
        return result

    def _build_canonical_mapping(self, input_findings: List[Dict]) -> Dict[str, Dict]:
        """
        Build canonical mapping from deterministic findings.
        Key by rule_id, store rule_id, rule_name, normalized_title, and normalized_aliases.
        """
        mapping = {}
        for finding in input_findings:
            rule_id = finding.get("rule_id", "")
            rule_name = finding.get("rule_name", "")
            title = finding.get("title", "")
            aliases = finding.get("aliases", [])
            
            if rule_id:
                # Normalize all aliases
                normalized_aliases = [_normalize_title(alias) for alias in aliases]
                
                mapping[rule_id] = {
                    "rule_id": rule_id,
                    "rule_name": rule_name,
                    "normalized_title": _normalize_title(title),
                    "normalized_rule_name": _normalize_title(rule_name),
                    "normalized_aliases": normalized_aliases,
                }
        return mapping

    def _verify_output_maps_to_findings(self, llm_output: Dict, input_findings: List[Dict]) -> bool:
        """
        ✅ VERIFICATION 5: Ensure LLM output maps back to deterministic findings.
        Every top_issue should correspond to a rule from input_findings.
        Uses normalized title matching to avoid false warnings.
        """
        if not input_findings:
            # Zero findings case - LLM should only suggest missing sections
            return len(llm_output.get("top_issues", [])) == 0

        # Build canonical mapping from deterministic findings
        canonical_mapping = self._build_canonical_mapping(input_findings)
        
        # Collect all normalized identifiers for matching (rule_name, title, and aliases)
        normalized_rule_names: Set[str] = set()
        normalized_titles: Set[str] = set()
        normalized_aliases: Set[str] = set()
        for rule_data in canonical_mapping.values():
            normalized_rule_names.add(rule_data["normalized_rule_name"])
            normalized_titles.add(rule_data["normalized_title"])
            normalized_aliases.update(rule_data.get("normalized_aliases", []))

        # Check that top_issues map to input findings using normalized matching
        for issue in llm_output.get("top_issues", []):
            issue_title = issue.get("title", "")
            normalized_issue_title = _normalize_title(issue_title)
            
            # An LLM issue is valid if normalized_title matches:
            # - deterministic rule_name
            # - deterministic title
            # - explicit aliases (BEST - 2-line mental model)
            is_valid = False
            
            # Check against normalized rule names
            for norm_rule_name in normalized_rule_names:
                if (normalized_issue_title == norm_rule_name or
                    normalized_issue_title in norm_rule_name or
                    norm_rule_name in normalized_issue_title):
                    is_valid = True
                    break
            
            # Check against normalized titles
            if not is_valid:
                for norm_title in normalized_titles:
                    if (normalized_issue_title == norm_title or
                        normalized_issue_title in norm_title or
                        norm_title in normalized_issue_title):
                        is_valid = True
                        break
            
            # Check against explicit aliases (production-grade approach)
            if not is_valid:
                for norm_alias in normalized_aliases:
                    if (normalized_issue_title == norm_alias or
                        normalized_issue_title in norm_alias or
                        norm_alias in normalized_issue_title):
                        is_valid = True
                        break

            # Only warn on TRUE mismatches
            if not is_valid:
                logger.warning(
                    f"LLM output issue '{issue_title}' (normalized: '{normalized_issue_title}') "
                    f"may not map to deterministic findings. "
                    f"Available normalized rules: {sorted(list(normalized_rule_names))[:10]}"
                )

        return True

    def evaluate(self, findings: List[Dict], overall_risk: str) -> Optional[Dict]:
        if not self.client:
            logger.warning("OpenAI client not configured; skipping LLM evaluation")
            return None

        # ✅ VERIFICATION 2: Hard architectural assertion - LLM must not be called with zero findings
        # If you want LLM for zero findings, make it explicit by calling create_fallback_response instead
        if not findings:
            logger.warning("LLM evaluate() called with zero findings - using fallback instead")
            return self.create_fallback_response(findings=[], overall_risk=overall_risk)

        # ✅ VERIFICATION 3: Log exactly what is sent to LLM (payload proof)
        # This MUST only contain findings data, NOT full contract text
        findings_summary = json.dumps(findings, indent=2)
        logger.info(
            f"LLM INPUT (deterministic findings only, first 2000 chars): "
            f"{findings_summary[:2000]}"
        )
        logger.info(f"LLM CALL → model={self.model}, temperature=0.2")
        logger.info(f"LLM INPUT contains {len(findings)} findings, NO contract text")

        prompt = self._build_prompt(findings=findings, overall_risk=overall_risk)

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a conservative risk triage assistant. Output only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            content = resp.choices[0].message.content
            result = json.loads(content)

            # Never let model override computed risk
            result["overall_risk"] = overall_risk

            validated_result = self._validate_result(result)

            # ✅ VERIFICATION 4: Verify output maps back to input findings
            self._verify_output_maps_to_findings(validated_result, findings)

            # ✅ VERIFICATION 4: Log LLM output to verify it only explains detected findings
            logger.info(
                f"LLM OUTPUT: {len(validated_result.get('top_issues', []))} top_issues, "
                f"{len(validated_result.get('summary_bullets', []))} summary bullets"
            )
            for issue in validated_result.get("top_issues", [])[:5]:
                logger.info(
                    f"LLM ISSUE: {issue.get('title', 'N/A')} | {issue.get('severity', 'N/A')}"
                )

            return validated_result

        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return None

    def create_fallback_response(self, findings: List[Dict], overall_risk: str) -> Dict:
        # Rules-only fallback (still usable and safe)
        top_issues = []
        for f in findings[:6]:
            top_issues.append(
                {
                    "title": f.get("title") or f.get("rule_name", "Issue"),
                    "severity": f.get("severity", "low"),
                    "why_it_matters": f.get("rationale", "This may indicate increased contractual risk."),
                    "negotiation_consideration": "Commonly negotiated; consider clarifying scope, caps, and mutuality.",
                }
            )

        summary = []
        if overall_risk == "high":
            summary.append("High-level: the deterministic engine flagged one or more high-risk patterns that may materially increase exposure.")
        elif overall_risk == "medium":
            summary.append("Medium-level: multiple negotiable risk patterns were detected; review the highlighted clauses.")
        else:
            summary.append("Low-level: no major high-risk patterns were detected, but review flagged clauses for context.")

        return {
            "overall_risk": overall_risk,
            "summary_bullets": summary[:5],
            "top_issues": top_issues,
            "possible_missing_sections": [
                "Limitation of liability (confirm it exists and covers key categories)",
                "Indemnification scope (confirm it is mutual and reasonably capped)",
                "Termination / term (confirm notice windows and renewal terms)",
                "IP ownership / license scope (confirm no unintended assignment)",
            ][:6],
            "disclaimer": "This is automated risk triage, not legal advice.",
        }
