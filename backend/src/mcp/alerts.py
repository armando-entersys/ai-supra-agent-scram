"""Proactive alerts system for marketing anomaly detection.

Monitors campaign performance and generates alerts when thresholds are exceeded.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional
from enum import Enum
import structlog
from google.cloud import bigquery

from src.config import get_settings
from src.mcp.benchmarks import (
    get_benchmarks_for_campaign,
    ALERT_THRESHOLDS,
)
from src.mcp.memory import get_agent_memory

logger = structlog.get_logger()
settings = get_settings()


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    SPEND_SPIKE = "spend_spike"
    CTR_DROP = "ctr_drop"
    CPC_SPIKE = "cpc_spike"
    ZERO_CONVERSIONS = "zero_conversions"
    BUDGET_DEPLETED = "budget_depleted"
    PERFORMANCE_ANOMALY = "performance_anomaly"
    OPPORTUNITY = "opportunity"


class CampaignAlerts:
    """Generates and manages campaign alerts."""

    def __init__(self) -> None:
        """Initialize alerts system."""
        self.project_id = settings.gcp_project_id
        self.client = bigquery.Client(project=self.project_id)
        self.memory = get_agent_memory()
        logger.info("CampaignAlerts initialized")

    async def check_all_alerts(self) -> list[dict[str, Any]]:
        """Run all alert checks and return findings.

        Returns:
            List of alert objects
        """
        alerts = []

        try:
            # Get recent campaign data
            campaigns = await self._get_recent_campaign_data()

            for campaign in campaigns:
                campaign_alerts = await self._check_campaign_alerts(campaign)
                alerts.extend(campaign_alerts)

            # Sort by severity
            severity_order = {"critical": 0, "warning": 1, "info": 2}
            alerts.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 3))

            # Store alerts in memory for tracking
            if self.memory and alerts:
                for alert in alerts[:10]:  # Store top 10
                    await self.memory.store_insight(
                        campaign_id=alert.get("campaign_id", ""),
                        insight_type="anomaly" if alert.get("severity") != "info" else "opportunity",
                        title=alert.get("title", ""),
                        description=alert.get("description", ""),
                        data=alert.get("data", {}),
                        severity=alert.get("severity", "info")
                    )

            logger.info("Alert check completed", total_alerts=len(alerts))
            return alerts

        except Exception as e:
            logger.error("Alert check failed", error=str(e))
            return []

    async def _get_recent_campaign_data(self) -> list[dict[str, Any]]:
        """Get campaign performance data for the last 7 days."""
        try:
            query = """
                SELECT
                    campaign_name,
                    campaign_id,
                    SUM(impressions) as impressions,
                    SUM(clicks) as clicks,
                    SUM(cost) as cost,
                    SUM(conversions) as conversions,
                    SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100 as ctr,
                    SAFE_DIVIDE(SUM(cost), SUM(clicks)) as cpc,
                    SAFE_DIVIDE(SUM(cost), SUM(conversions)) as cpa,
                    MAX(date) as last_date,
                    COUNT(DISTINCT date) as days_with_data
                FROM `mi-infraestructura-web.google_ads_data.campaign_performance`
                WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
                GROUP BY campaign_name, campaign_id
            """

            results = []
            for row in self.client.query(query).result():
                results.append({
                    "campaign_name": row.campaign_name,
                    "campaign_id": row.campaign_id,
                    "impressions": row.impressions or 0,
                    "clicks": row.clicks or 0,
                    "cost": float(row.cost or 0),
                    "conversions": float(row.conversions or 0),
                    "ctr": float(row.ctr or 0),
                    "cpc": float(row.cpc or 0),
                    "cpa": float(row.cpa or 0) if row.conversions and row.conversions > 0 else 0,
                    "last_date": str(row.last_date) if row.last_date else None,
                    "days_with_data": row.days_with_data or 0,
                })

            return results

        except Exception as e:
            logger.error("Failed to get campaign data", error=str(e))
            return []

    async def _check_campaign_alerts(self, campaign: dict[str, Any]) -> list[dict[str, Any]]:
        """Check alerts for a single campaign.

        Args:
            campaign: Campaign data dict

        Returns:
            List of alerts for this campaign
        """
        alerts = []
        campaign_name = campaign.get("campaign_name", "Unknown")
        benchmarks = get_benchmarks_for_campaign(campaign_name)

        # 1. Check for zero conversions with significant spend
        if campaign.get("cost", 0) > 100 and campaign.get("conversions", 0) == 0:
            alerts.append({
                "type": AlertType.ZERO_CONVERSIONS.value,
                "severity": AlertSeverity.CRITICAL.value,
                "campaign_id": campaign.get("campaign_id", ""),
                "campaign_name": campaign_name,
                "title": f"Sin conversiones: {campaign_name}",
                "description": f"La campaña ha gastado ${campaign.get('cost', 0):.2f} en los últimos 7 días sin generar conversiones.",
                "data": {
                    "cost": campaign.get("cost", 0),
                    "clicks": campaign.get("clicks", 0),
                    "impressions": campaign.get("impressions", 0),
                },
                "recommendation": "Revisar landing page, tracking de conversiones, y calidad del tráfico."
            })

        # 2. Check CTR vs benchmark
        actual_ctr = campaign.get("ctr", 0)
        benchmark_ctr = benchmarks.get("avg_ctr", 3.0)

        if actual_ctr > 0 and actual_ctr < benchmark_ctr * ALERT_THRESHOLDS["ctr_critical_low"]:
            alerts.append({
                "type": AlertType.CTR_DROP.value,
                "severity": AlertSeverity.CRITICAL.value,
                "campaign_id": campaign.get("campaign_id", ""),
                "campaign_name": campaign_name,
                "title": f"CTR crítico: {campaign_name}",
                "description": f"CTR actual ({actual_ctr:.2f}%) está muy por debajo del benchmark ({benchmark_ctr:.2f}%).",
                "data": {
                    "actual_ctr": actual_ctr,
                    "benchmark_ctr": benchmark_ctr,
                    "diff_pct": round((actual_ctr - benchmark_ctr) / benchmark_ctr * 100, 1),
                },
                "recommendation": "Revisar relevancia de anuncios, palabras clave negativas, y segmentación."
            })
        elif actual_ctr > 0 and actual_ctr < benchmark_ctr * ALERT_THRESHOLDS["ctr_warning_low"]:
            alerts.append({
                "type": AlertType.CTR_DROP.value,
                "severity": AlertSeverity.WARNING.value,
                "campaign_id": campaign.get("campaign_id", ""),
                "campaign_name": campaign_name,
                "title": f"CTR bajo: {campaign_name}",
                "description": f"CTR actual ({actual_ctr:.2f}%) está por debajo del benchmark ({benchmark_ctr:.2f}%).",
                "data": {
                    "actual_ctr": actual_ctr,
                    "benchmark_ctr": benchmark_ctr,
                },
                "recommendation": "Considerar A/B testing de anuncios y revisión de keywords."
            })

        # 3. Check CPC vs benchmark
        actual_cpc = campaign.get("cpc", 0)
        benchmark_cpc = benchmarks.get("avg_cpc", 2.0)

        if actual_cpc > benchmark_cpc * ALERT_THRESHOLDS["cpc_critical_high"]:
            alerts.append({
                "type": AlertType.CPC_SPIKE.value,
                "severity": AlertSeverity.WARNING.value,
                "campaign_id": campaign.get("campaign_id", ""),
                "campaign_name": campaign_name,
                "title": f"CPC elevado: {campaign_name}",
                "description": f"CPC actual (${actual_cpc:.2f}) es el doble del benchmark (${benchmark_cpc:.2f}).",
                "data": {
                    "actual_cpc": actual_cpc,
                    "benchmark_cpc": benchmark_cpc,
                },
                "recommendation": "Revisar pujas, quality score, y competencia en subastas."
            })

        # 4. Check for opportunities (high CTR campaigns)
        if actual_ctr > benchmark_ctr * 1.5 and campaign.get("clicks", 0) > 50:
            alerts.append({
                "type": AlertType.OPPORTUNITY.value,
                "severity": AlertSeverity.INFO.value,
                "campaign_id": campaign.get("campaign_id", ""),
                "campaign_name": campaign_name,
                "title": f"Oportunidad de escalar: {campaign_name}",
                "description": f"CTR excepcional ({actual_ctr:.2f}%) - 50% arriba del benchmark. Considerar aumentar presupuesto.",
                "data": {
                    "actual_ctr": actual_ctr,
                    "benchmark_ctr": benchmark_ctr,
                    "clicks": campaign.get("clicks", 0),
                },
                "recommendation": "Aumentar presupuesto gradualmente y monitorear conversiones."
            })

        return alerts

    async def get_daily_digest(self) -> str:
        """Generate a daily digest of alerts and insights.

        Returns:
            Formatted digest text
        """
        alerts = await self.check_all_alerts()

        if not alerts:
            return "✅ **Sin alertas activas** - Todas las campañas operan dentro de parámetros normales."

        # Group by severity
        critical = [a for a in alerts if a.get("severity") == "critical"]
        warnings = [a for a in alerts if a.get("severity") == "warning"]
        info = [a for a in alerts if a.get("severity") == "info"]

        lines = ["# 📊 Resumen Diario de Alertas\n"]

        if critical:
            lines.append("## 🚨 Alertas Críticas\n")
            for alert in critical:
                lines.append(f"### {alert['title']}")
                lines.append(f"{alert['description']}\n")
                lines.append(f"**Recomendación:** {alert.get('recommendation', 'Revisar campaña.')}\n")

        if warnings:
            lines.append("## ⚠️ Advertencias\n")
            for alert in warnings:
                lines.append(f"- **{alert['title']}**: {alert['description']}")

        if info:
            lines.append("\n## 💡 Oportunidades\n")
            for alert in info:
                lines.append(f"- **{alert['title']}**: {alert['description']}")

        # Summary stats
        lines.append(f"\n---\n**Total alertas:** {len(alerts)} ({len(critical)} críticas, {len(warnings)} advertencias, {len(info)} oportunidades)")

        return "\n".join(lines)


def format_alerts_for_display(alerts: list[dict[str, Any]]) -> str:
    """Format alerts list for chat display.

    Args:
        alerts: List of alert dicts

    Returns:
        Formatted markdown string
    """
    if not alerts:
        return "✅ No hay alertas activas en este momento."

    severity_emoji = {
        "critical": "🚨",
        "warning": "⚠️",
        "info": "💡",
    }

    lines = [f"**📋 {len(alerts)} Alertas Detectadas**\n"]

    for alert in alerts[:10]:
        emoji = severity_emoji.get(alert.get("severity", "info"), "ℹ️")
        lines.append(f"{emoji} **{alert.get('title', 'Alerta')}**")
        lines.append(f"   {alert.get('description', '')}")
        if alert.get("recommendation"):
            lines.append(f"   → *{alert['recommendation']}*")
        lines.append("")

    return "\n".join(lines)


# Singleton instance
_alerts_instance: Optional[CampaignAlerts] = None


def get_campaign_alerts() -> Optional[CampaignAlerts]:
    """Get or create campaign alerts instance."""
    global _alerts_instance
    if _alerts_instance is None:
        try:
            _alerts_instance = CampaignAlerts()
        except Exception as e:
            logger.error("Failed to initialize CampaignAlerts", error=str(e))
            return None
    return _alerts_instance
