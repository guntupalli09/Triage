"""
Baseline pure-LLM detection runner.
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

from experiments.config import OPENAI_API_KEY, BASELINE_MODEL, BASELINE_TEMPERATURE, BASELINE_MAX_TOKENS
from experiments.utils_io import read_text, save_json


BASELINE_PROMPT = """You are analyzing a Non-Disclosure Agreement (NDA) or Master Service Agreement (MSA) for potential risk indicators.

Analyze the following contract text and identify risk indicators. For each risk you identify, provide:
- A clear risk title
- Severity (HIGH, MEDIUM, or LOW)
- A brief rationale explaining why this may be a risk
- A verbatim excerpt from the contract (maximum 40 words) that supports your finding

Output ONLY valid JSON in this exact format:
{{
  "findings": [
    {{
      "risk_title": "Brief title of the risk",
      "severity": "HIGH",
      "rationale": "Why this may indicate risk",
      "evidence_quote": "Exact quote from contract, max 40 words"
    }}
  ]
}}

Contract text:
{text}

Remember: Output ONLY the JSON object, no other text."""


def run_baseline_llm(text: str) -> Dict[str, Any]:
    """
    Run baseline LLM detection on text.
    
    Returns:
        Dict with findings list, or error dict if API unavailable
    """
    if not OPENAI_API_KEY:
        return {
            "error": "OPENAI_API_KEY not set",
            "findings": [],
            "executed": False
        }
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = BASELINE_PROMPT.format(text=text[:8000])  # Limit to avoid token limits
        
        response = client.chat.completions.create(
            model=BASELINE_MODEL,
            messages=[
                {"role": "system", "content": "You are a contract risk analysis assistant. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=BASELINE_TEMPERATURE,
            max_tokens=BASELINE_MAX_TOKENS,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON from response
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Try to find JSON object in the content
        # Sometimes LLM adds extra text before/after JSON
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            # Try to extract JSON object from text using regex
            import re
            # Match balanced braces for JSON object
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    # Last resort: try to fix common JSON issues
                    json_str = json_match.group(0)
                    # Remove trailing commas before closing braces/brackets
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    try:
                        result = json.loads(json_str)
                    except json.JSONDecodeError:
                        return {
                            "error": f"JSON parse error: {str(e)}. Response preview: {content[:300]}",
                            "findings": [],
                            "executed": False,
                            "raw_response": content[:500]  # Include for debugging
                        }
            else:
                return {
                    "error": f"JSON parse error: {str(e)}. No JSON object found. Response: {content[:300]}",
                    "findings": [],
                    "executed": False,
                    "raw_response": content[:500]
                }
        
        # Ensure result has findings list
        if "findings" not in result:
            result["findings"] = []
        
        result["executed"] = True
        return result
        
    except Exception as e:
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}"
        return {
            "error": error_details,
            "findings": [],
            "executed": False,
            "traceback": traceback.format_exc()[:500]  # First 500 chars of traceback
        }


def run_baseline_on_file(input_path: Path, output_path: Path) -> None:
    """Run baseline LLM on a text file and save output."""
    text = read_text(input_path)
    result = run_baseline_llm(text)
    save_json(result, output_path)


if __name__ == "__main__":
    # CLI usage: python run_baseline_llm.py <input.txt> <output.json>
    if len(sys.argv) < 3:
        print("Usage: python run_baseline_llm.py <input.txt> <output.json>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    run_baseline_on_file(input_path, output_path)
