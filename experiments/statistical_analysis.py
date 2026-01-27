"""
Statistical significance testing for experiment results.
"""
import math
from typing import List, Dict, Any, Tuple
from scipy import stats
import numpy as np


def mcnemar_test(hybrid_results: List[bool], baseline_results: List[bool]) -> Dict[str, Any]:
    """
    McNemar's test for paired binary data (determinism: True/False).
    
    Tests if there's a significant difference in determinism rates between
    hybrid and baseline systems on the same documents.
    
    Returns:
        Dict with: statistic, p_value, significant (bool), interpretation
    """
    if len(hybrid_results) != len(baseline_results):
        return {
            "error": "Hybrid and baseline results must have same length",
            "statistic": None,
            "p_value": None,
            "significant": None,
        }
    
    # Build contingency table
    # a = both deterministic, b = hybrid deterministic but baseline not
    # c = baseline deterministic but hybrid not, d = neither deterministic
    a = b = c = d = 0
    
    for h, bl in zip(hybrid_results, baseline_results):
        if h and bl:
            a += 1
        elif h and not bl:
            b += 1  # hybrid deterministic, baseline not
        elif not h and bl:
            c += 1  # baseline deterministic, hybrid not
        else:
            d += 1  # neither deterministic
    
    # McNemar's test: chi-square = (|b - c| - 1)^2 / (b + c)
    # Continuity correction: subtract 1
    if (b + c) == 0:
        # Perfect agreement - no test needed
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "significant": False,
            "interpretation": "Perfect agreement - no difference to test",
            "contingency_table": {"a": a, "b": b, "c": c, "d": d},
        }
    
    statistic = ((abs(b - c) - 1) ** 2) / (b + c)
    # Chi-square with 1 degree of freedom
    p_value = 1 - stats.chi2.cdf(statistic, df=1)
    significant = p_value < 0.05
    
    interpretation = (
        f"McNemar's test: {'Significant' if significant else 'Not significant'} "
        f"difference in determinism (p={p_value:.4f})"
    )
    
    return {
        "statistic": statistic,
        "p_value": p_value,
        "significant": significant,
        "interpretation": interpretation,
        "contingency_table": {"a": a, "b": b, "c": c, "d": d},
    }


def chi_square_fp_fn_by_type(
    fp_counts: Dict[str, int],
    fn_counts: Dict[str, int],
    contract_types: List[str]
) -> Dict[str, Any]:
    """
    Chi-square test for independence: Are FP/FN rates independent of contract type?
    
    Args:
        fp_counts: Dict mapping contract_type -> FP count
        fn_counts: Dict mapping contract_type -> FN count
        contract_types: List of contract types to test
    
    Returns:
        Dict with: statistic, p_value, significant, interpretation
    """
    # Build contingency table: contract_type x error_type (FP/FN)
    observed = []
    for ct in contract_types:
        observed.append([fp_counts.get(ct, 0), fn_counts.get(ct, 0)])
    
    if len(observed) < 2:
        return {
            "error": "Need at least 2 contract types for chi-square test",
            "statistic": None,
            "p_value": None,
            "significant": None,
        }
    
    # Perform chi-square test
    try:
        chi2, p_value, dof, expected = stats.chi2_contingency(observed)
        significant = p_value < 0.05
        
        interpretation = (
            f"Chi-square test: FP/FN rates are {'dependent on' if significant else 'independent of'} "
            f"contract type (p={p_value:.4f})"
        )
        
        return {
            "statistic": chi2,
            "p_value": p_value,
            "significant": significant,
            "interpretation": interpretation,
            "degrees_of_freedom": dof,
            "expected_frequencies": expected.tolist(),
        }
    except Exception as e:
        return {
            "error": f"Chi-square test failed: {e}",
            "statistic": None,
            "p_value": None,
            "significant": None,
        }


def confidence_interval(data: List[float], confidence: float = 0.95) -> Dict[str, float]:
    """
    Calculate confidence interval for a list of values.
    
    Returns:
        Dict with: mean, lower_bound, upper_bound, std_dev, n
    """
    if not data:
        return {
            "mean": None,
            "lower_bound": None,
            "upper_bound": None,
            "std_dev": None,
            "n": 0,
        }
    
    n = len(data)
    mean = np.mean(data)
    std_dev = np.std(data, ddof=1) if n > 1 else 0.0
    
    # t-distribution for confidence interval
    if n > 1:
        t_critical = stats.t.ppf((1 + confidence) / 2, df=n-1)
        margin = t_critical * (std_dev / math.sqrt(n))
        lower = mean - margin
        upper = mean + margin
    else:
        lower = upper = mean
    
    return {
        "mean": float(mean),
        "lower_bound": float(lower),
        "upper_bound": float(upper),
        "std_dev": float(std_dev),
        "n": n,
        "confidence_level": confidence,
    }


def cohens_d(group1: List[float], group2: List[float]) -> Dict[str, Any]:
    """
    Calculate Cohen's d effect size between two groups.
    
    Returns:
        Dict with: cohens_d, interpretation, magnitude
    """
    if not group1 or not group2:
        return {
            "cohens_d": None,
            "interpretation": "Insufficient data",
            "magnitude": None,
        }
    
    mean1 = np.mean(group1)
    mean2 = np.mean(group2)
    std1 = np.std(group1, ddof=1) if len(group1) > 1 else 0.0
    std2 = np.std(group2, ddof=1) if len(group2) > 1 else 0.0
    
    # Pooled standard deviation
    n1, n2 = len(group1), len(group2)
    pooled_std = math.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return {
            "cohens_d": 0.0,
            "interpretation": "No variance - perfect agreement",
            "magnitude": "none",
        }
    
    d = (mean1 - mean2) / pooled_std
    
    # Interpret effect size
    abs_d = abs(d)
    if abs_d < 0.2:
        magnitude = "negligible"
    elif abs_d < 0.5:
        magnitude = "small"
    elif abs_d < 0.8:
        magnitude = "medium"
    else:
        magnitude = "large"
    
    interpretation = f"Cohen's d = {d:.3f} ({magnitude} effect size)"
    
    return {
        "cohens_d": float(d),
        "interpretation": interpretation,
        "magnitude": magnitude,
    }


def compute_all_statistics(
    exp1_results: List[Dict[str, Any]],
    exp3_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compute all statistical tests for the experiment results.
    
    Returns:
        Dict with all statistical test results
    """
    stats_results = {}
    
    # 1. McNemar's test for determinism
    hybrid_deterministic = [r.get("hybrid_deterministic", False) for r in exp1_results]
    baseline_deterministic = [r.get("baseline_deterministic", False) if r.get("baseline_deterministic") is not None else False for r in exp1_results]
    
    if any(baseline_deterministic):  # Only test if baseline was executed
        stats_results["mcnemar_determinism"] = mcnemar_test(hybrid_deterministic, baseline_deterministic)
    
    # 2. Confidence intervals for metrics
    ungrounded_values = [r.get("baseline_avg_ungrounded", 0) for r in exp1_results if r.get("baseline_avg_ungrounded") is not None]
    if ungrounded_values:
        stats_results["ungrounded_ci"] = confidence_interval(ungrounded_values)
    
    # 3. FP/FN by contract type (chi-square)
    fp_by_type = {}
    fn_by_type = {}
    contract_types = set()
    
    for r in exp1_results:
        if r.get("is_synthetic"):
            # Try to determine contract type from doc_id
            doc_id = r.get("doc_id", "")
            if doc_id.startswith("msa_"):
                ct = "MSA"
            elif doc_id.startswith("emp_"):
                ct = "Employment"
            elif doc_id.startswith("lic_"):
                ct = "Licensing"
            else:
                ct = "NDA"
            
            contract_types.add(ct)
            fp_by_type[ct] = fp_by_type.get(ct, 0) + r.get("fp_count", 0)
            fn_by_type[ct] = fn_by_type.get(ct, 0) + r.get("fn_count", 0)
    
    if len(contract_types) >= 2:
        stats_results["chi_square_fp_fn"] = chi_square_fp_fn_by_type(
            fp_by_type, fn_by_type, list(contract_types)
        )
    
    # 4. Effect size for determinism difference
    hybrid_det_rate = sum(hybrid_deterministic) / len(hybrid_deterministic) if hybrid_deterministic else 0
    baseline_det_rate = sum(baseline_deterministic) / len(baseline_deterministic) if baseline_deterministic else 0
    
    # Convert to binary lists for Cohen's d
    hybrid_binary = [1 if d else 0 for d in hybrid_deterministic]
    baseline_binary = [1 if d else 0 for d in baseline_deterministic]
    
    if baseline_binary:
        stats_results["cohens_d_determinism"] = cohens_d(hybrid_binary, baseline_binary)
    
    # 5. Suppression impact (from exp3)
    if exp3_results:
        fp_on = [r.get("fp_on", 0) for r in exp3_results]
        fp_off = [r.get("fp_off", 0) for r in exp3_results if r.get("fp_off") is not None]
        
        if fp_off:
            stats_results["suppression_fp_ci"] = {
                "on": confidence_interval(fp_on),
                "off": confidence_interval(fp_off),
            }
            
            # Paired t-test for suppression impact
            if len(fp_on) == len(fp_off):
                try:
                    t_stat, p_val = stats.ttest_rel(fp_on, fp_off)
                    stats_results["suppression_t_test"] = {
                        "statistic": float(t_stat),
                        "p_value": float(p_val),
                        "significant": p_val < 0.05,
                        "interpretation": f"Paired t-test: Suppression {'significantly' if p_val < 0.05 else 'does not significantly'} reduces FPs (p={p_val:.4f})",
                    }
                except:
                    pass
    
    return stats_results
