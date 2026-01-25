"""Industry benchmarks for marketing analytics.

Provides reference data to compare campaign performance against industry standards.
"""

from typing import Any
import structlog

logger = structlog.get_logger()

# Industry benchmarks by vertical (updated 2025)
INDUSTRY_BENCHMARKS: dict[str, dict[str, float]] = {
    "security_systems": {
        "avg_ctr": 3.20,          # Click-through rate %
        "avg_cpc": 1.85,          # Cost per click USD
        "avg_conversion_rate": 2.80,  # Conversion rate %
        "avg_cpa": 65.00,         # Cost per acquisition USD
        "avg_impression_share": 45.0,  # Impression share %
        "mobile_traffic_pct": 75.0,    # Mobile traffic %
    },
    "connectivity_solutions": {
        "avg_ctr": 2.80,
        "avg_cpc": 2.10,
        "avg_conversion_rate": 3.10,
        "avg_cpa": 72.00,
        "avg_impression_share": 50.0,
        "mobile_traffic_pct": 68.0,
    },
    "b2b_technology": {
        "avg_ctr": 2.50,
        "avg_cpc": 3.50,
        "avg_conversion_rate": 2.50,
        "avg_cpa": 120.00,
        "avg_impression_share": 40.0,
        "mobile_traffic_pct": 45.0,
    },
    "ecommerce_general": {
        "avg_ctr": 2.69,
        "avg_cpc": 1.16,
        "avg_conversion_rate": 2.81,
        "avg_cpa": 45.27,
        "avg_impression_share": 55.0,
        "mobile_traffic_pct": 72.0,
    },
    "professional_services": {
        "avg_ctr": 2.41,
        "avg_cpc": 2.93,
        "avg_conversion_rate": 3.04,
        "avg_cpa": 87.36,
        "avg_impression_share": 42.0,
        "mobile_traffic_pct": 55.0,
    },
}

# Campaign name to industry mapping
CAMPAIGN_INDUSTRY_MAP: dict[str, str] = {
    "seguridad": "security_systems",
    "cámaras": "security_systems",
    "alarmas": "security_systems",
    "cctv": "security_systems",
    "vigilancia": "security_systems",
    "conectividad": "connectivity_solutions",
    "internet": "connectivity_solutions",
    "red": "connectivity_solutions",
    "wifi": "connectivity_solutions",
    "networking": "connectivity_solutions",
}


def get_industry_for_campaign(campaign_name: str) -> str:
    """Determine industry vertical from campaign name.

    Args:
        campaign_name: Name of the campaign

    Returns:
        Industry key or 'b2b_technology' as default
    """
    campaign_lower = campaign_name.lower()

    for keyword, industry in CAMPAIGN_INDUSTRY_MAP.items():
        if keyword in campaign_lower:
            return industry

    return "b2b_technology"  # Default


def get_benchmarks_for_campaign(campaign_name: str) -> dict[str, float]:
    """Get industry benchmarks for a specific campaign.

    Args:
        campaign_name: Name of the campaign

    Returns:
        Dictionary of benchmark metrics
    """
    industry = get_industry_for_campaign(campaign_name)
    return INDUSTRY_BENCHMARKS.get(industry, INDUSTRY_BENCHMARKS["b2b_technology"])


def compare_to_benchmark(
    campaign_name: str,
    metrics: dict[str, float]
) -> dict[str, Any]:
    """Compare campaign metrics to industry benchmarks.

    Args:
        campaign_name: Name of the campaign
        metrics: Actual campaign metrics (ctr, cpc, conversion_rate, cpa)

    Returns:
        Comparison results with performance indicators
    """
    benchmarks = get_benchmarks_for_campaign(campaign_name)
    industry = get_industry_for_campaign(campaign_name)

    comparisons = {
        "industry": industry,
        "benchmarks": benchmarks,
        "comparisons": {}
    }

    # Metrics where higher is better
    higher_is_better = ["ctr", "conversion_rate", "impression_share"]
    # Metrics where lower is better
    lower_is_better = ["cpc", "cpa"]

    metric_map = {
        "ctr": "avg_ctr",
        "cpc": "avg_cpc",
        "conversion_rate": "avg_conversion_rate",
        "cpa": "avg_cpa",
    }

    for metric_key, benchmark_key in metric_map.items():
        if metric_key in metrics and benchmark_key in benchmarks:
            actual = metrics[metric_key]
            benchmark = benchmarks[benchmark_key]

            if benchmark > 0:
                diff_pct = ((actual - benchmark) / benchmark) * 100
            else:
                diff_pct = 0

            # Determine if performance is good
            if metric_key in higher_is_better:
                is_good = actual >= benchmark
                indicator = "above" if is_good else "below"
            else:
                is_good = actual <= benchmark
                indicator = "below" if is_good else "above"

            comparisons["comparisons"][metric_key] = {
                "actual": actual,
                "benchmark": benchmark,
                "diff_pct": round(diff_pct, 1),
                "indicator": indicator,
                "is_good": is_good,
                "emoji": "✅" if is_good else "⚠️"
            }

    return comparisons


def format_benchmark_comparison(comparison: dict[str, Any]) -> str:
    """Format benchmark comparison for display.

    Args:
        comparison: Result from compare_to_benchmark

    Returns:
        Formatted string for display
    """
    lines = [
        f"**📊 Comparación con Industria: {comparison['industry'].replace('_', ' ').title()}**\n",
        "| Métrica | Actual | Benchmark | vs. Industria |",
        "|---------|--------|-----------|---------------|",
    ]

    metric_names = {
        "ctr": "CTR",
        "cpc": "CPC",
        "conversion_rate": "Conv. Rate",
        "cpa": "CPA",
    }

    for metric_key, data in comparison["comparisons"].items():
        name = metric_names.get(metric_key, metric_key)

        # Format values based on metric type
        if metric_key in ["cpc", "cpa"]:
            actual_fmt = f"${data['actual']:.2f}"
            bench_fmt = f"${data['benchmark']:.2f}"
        else:
            actual_fmt = f"{data['actual']:.2f}%"
            bench_fmt = f"{data['benchmark']:.2f}%"

        diff_sign = "+" if data['diff_pct'] > 0 else ""
        indicator = f"{data['emoji']} {diff_sign}{data['diff_pct']}%"

        lines.append(f"| {name} | {actual_fmt} | {bench_fmt} | {indicator} |")

    return "\n".join(lines)


# Alert thresholds based on benchmarks
ALERT_THRESHOLDS = {
    "ctr_critical_low": 0.5,      # CTR below 50% of benchmark
    "ctr_warning_low": 0.75,      # CTR below 75% of benchmark
    "cpc_critical_high": 2.0,     # CPC above 200% of benchmark
    "cpc_warning_high": 1.5,      # CPC above 150% of benchmark
    "conversion_critical_low": 0.25,  # Conv rate below 25% of benchmark
    "zero_conversions_hours": 48,     # Alert if 0 conversions in X hours
    "spend_spike_pct": 150,           # Alert if daily spend >150% of average
}
