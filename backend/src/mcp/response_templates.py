"""Response templates for consistent, high-quality AI outputs.

Provides structured templates for different types of analyses and reports.
"""

from typing import Any, Optional
from datetime import datetime


class ResponseTemplates:
    """Templates for structured AI responses."""

    @staticmethod
    def campaign_analysis(
        campaign_name: str,
        metrics: dict[str, Any],
        benchmark_comparison: Optional[dict[str, Any]] = None,
        insights: Optional[list[str]] = None,
        recommendations: Optional[list[str]] = None
    ) -> str:
        """Template for campaign analysis response.

        Args:
            campaign_name: Name of the campaign
            metrics: Campaign metrics dict
            benchmark_comparison: Optional benchmark comparison
            insights: List of insights
            recommendations: List of recommendations

        Returns:
            Formatted response string
        """
        lines = [
            f"# 📊 Análisis: {campaign_name}\n",
            "## Resumen Ejecutivo\n",
        ]

        # Key metrics summary
        impressions = metrics.get("impressions", 0)
        clicks = metrics.get("clicks", 0)
        cost = metrics.get("cost", 0)
        conversions = metrics.get("conversions", 0)
        ctr = metrics.get("ctr", 0)
        cpc = metrics.get("cpc", 0)

        if conversions > 0:
            cpa = cost / conversions if conversions > 0 else 0
            summary = f"La campaña generó **{conversions:.0f} conversiones** con una inversión de **${cost:,.2f}**, resultando en un CPA de **${cpa:.2f}**."
        elif clicks > 0:
            summary = f"La campaña obtuvo **{clicks:,} clics** de **{impressions:,} impresiones** (CTR: {ctr:.2f}%), pero **no generó conversiones**."
        else:
            summary = f"La campaña tuvo **{impressions:,} impresiones** con actividad limitada."

        lines.append(summary + "\n")

        # Metrics table
        lines.extend([
            "## 🔢 Métricas Clave\n",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Impresiones | {impressions:,} |",
            f"| Clics | {clicks:,} |",
            f"| CTR | {ctr:.2f}% |",
            f"| CPC Promedio | ${cpc:.2f} |",
            f"| Costo Total | ${cost:,.2f} |",
            f"| Conversiones | {conversions:.0f} |",
        ])

        if conversions > 0:
            cpa = cost / conversions
            lines.append(f"| CPA | ${cpa:.2f} |")

        lines.append("")

        # Benchmark comparison if available
        if benchmark_comparison:
            lines.append("## 📈 vs. Benchmark de Industria\n")
            for metric, data in benchmark_comparison.get("comparisons", {}).items():
                emoji = data.get("emoji", "")
                actual = data.get("actual", 0)
                benchmark = data.get("benchmark", 0)
                diff = data.get("diff_pct", 0)
                sign = "+" if diff > 0 else ""
                lines.append(f"- **{metric.upper()}**: {actual:.2f} vs {benchmark:.2f} ({emoji} {sign}{diff}%)")
            lines.append("")

        # Insights
        if insights:
            lines.append("## 💡 Insights Clave\n")
            for i, insight in enumerate(insights, 1):
                lines.append(f"{i}. {insight}")
            lines.append("")

        # Recommendations
        if recommendations:
            lines.append("## ✅ Recomendaciones\n")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"**{i}.** {rec}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def diagnostic_response(
        question: str,
        diagnosis: str,
        analysis: str,
        recommendations: list[str],
        data_summary: Optional[str] = None
    ) -> str:
        """Template for diagnostic/problem-solving response.

        Args:
            question: Original question
            diagnosis: What's happening
            analysis: Why it's happening
            recommendations: What to do
            data_summary: Optional data context

        Returns:
            Formatted response
        """
        lines = [
            "## 📊 Resumen Ejecutivo\n",
            f"{diagnosis}\n",
        ]

        if data_summary:
            lines.extend([
                "## 🔍 Datos Analizados\n",
                data_summary,
                "",
            ])

        lines.extend([
            "## 💡 Análisis\n",
            analysis,
            "",
            "## ✅ Recomendaciones\n",
        ])

        for i, rec in enumerate(recommendations, 1):
            lines.append(f"**{i}.** {rec}")

        return "\n".join(lines)

    @staticmethod
    def multi_campaign_comparison(
        campaigns: list[dict[str, Any]],
        winner: Optional[str] = None,
        insights: Optional[list[str]] = None
    ) -> str:
        """Template for comparing multiple campaigns.

        Args:
            campaigns: List of campaign data dicts
            winner: Name of best performing campaign
            insights: Comparison insights

        Returns:
            Formatted comparison
        """
        if not campaigns:
            return "No hay campañas disponibles para comparar."

        lines = [
            "# 📊 Comparación de Campañas\n",
        ]

        # Summary table
        lines.extend([
            "| Campaña | Impresiones | Clics | Costo | Conv. | CTR | CPC |",
            "|---------|-------------|-------|-------|-------|-----|-----|",
        ])

        for c in campaigns:
            name = c.get("name", c.get("campaign_name", ""))[:25]
            lines.append(
                f"| {name} | {c.get('impressions', 0):,} | "
                f"{c.get('clicks', 0):,} | ${c.get('cost', 0):,.2f} | "
                f"{c.get('conversions', 0):.0f} | {c.get('ctr', 0):.2f}% | "
                f"${c.get('cpc', 0):.2f} |"
            )

        lines.append("")

        if winner:
            lines.append(f"**🏆 Mejor rendimiento:** {winner}\n")

        if insights:
            lines.append("## 💡 Insights\n")
            for insight in insights:
                lines.append(f"- {insight}")

        return "\n".join(lines)

    @staticmethod
    def search_terms_analysis(
        terms: list[dict[str, Any]],
        top_performers: Optional[list[str]] = None,
        negatives_suggested: Optional[list[str]] = None
    ) -> str:
        """Template for search terms analysis.

        Args:
            terms: List of search term data
            top_performers: Best performing terms
            negatives_suggested: Suggested negative keywords

        Returns:
            Formatted analysis
        """
        lines = [
            "# 🔍 Análisis de Términos de Búsqueda\n",
        ]

        if terms:
            lines.extend([
                "## Top Términos por Clics\n",
                "| Término | Clics | Costo | Conv. |",
                "|---------|-------|-------|-------|",
            ])

            for t in terms[:15]:
                term = t.get("search_term", t.get("term", ""))[:40]
                lines.append(
                    f"| {term} | {t.get('clicks', 0)} | "
                    f"${t.get('cost', 0):.2f} | {t.get('conversions', 0):.0f} |"
                )

            lines.append("")

        if top_performers:
            lines.append("## ✅ Términos de Alto Rendimiento\n")
            for term in top_performers:
                lines.append(f"- **{term}** - Considerar como keyword exacto")
            lines.append("")

        if negatives_suggested:
            lines.append("## ⛔ Sugerencias de Negativos\n")
            for term in negatives_suggested:
                lines.append(f"- `{term}` - Agregar como negativo")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def daily_report(
        date: str,
        metrics_summary: dict[str, Any],
        alerts: list[dict[str, Any]],
        top_campaign: Optional[str] = None,
        recommendations: Optional[list[str]] = None
    ) -> str:
        """Template for daily performance report.

        Args:
            date: Report date
            metrics_summary: Overall metrics
            alerts: Active alerts
            top_campaign: Best performing campaign
            recommendations: Daily recommendations

        Returns:
            Formatted report
        """
        lines = [
            f"# 📅 Reporte Diario - {date}\n",
            "## 📊 Resumen del Día\n",
        ]

        # Metrics
        total_spend = metrics_summary.get("total_spend", 0)
        total_clicks = metrics_summary.get("total_clicks", 0)
        total_conv = metrics_summary.get("total_conversions", 0)

        lines.extend([
            f"- **Inversión total:** ${total_spend:,.2f}",
            f"- **Clics totales:** {total_clicks:,}",
            f"- **Conversiones:** {total_conv:.0f}",
        ])

        if total_conv > 0:
            cpa = total_spend / total_conv
            lines.append(f"- **CPA promedio:** ${cpa:.2f}")

        lines.append("")

        if top_campaign:
            lines.append(f"**🏆 Mejor campaña del día:** {top_campaign}\n")

        # Alerts section
        if alerts:
            critical = [a for a in alerts if a.get("severity") == "critical"]
            warnings = [a for a in alerts if a.get("severity") == "warning"]

            if critical:
                lines.append("## 🚨 Alertas Críticas\n")
                for alert in critical:
                    lines.append(f"- **{alert.get('title', '')}**: {alert.get('description', '')}")
                lines.append("")

            if warnings:
                lines.append("## ⚠️ Advertencias\n")
                for alert in warnings:
                    lines.append(f"- {alert.get('title', '')}")
                lines.append("")
        else:
            lines.append("✅ **Sin alertas activas**\n")

        # Recommendations
        if recommendations:
            lines.append("## ✅ Acciones Recomendadas\n")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")

        return "\n".join(lines)

    @staticmethod
    def error_response(
        tool_name: str,
        error_message: str,
        suggestion: Optional[str] = None
    ) -> str:
        """Template for error responses.

        Args:
            tool_name: Tool that failed
            error_message: Error description
            suggestion: What to try instead

        Returns:
            User-friendly error message
        """
        lines = [
            f"⚠️ **No pude completar la consulta**\n",
            f"El acceso a {tool_name} no está disponible en este momento.",
        ]

        if suggestion:
            lines.append(f"\n**Alternativa:** {suggestion}")

        lines.append("\n¿Hay algo más en lo que pueda ayudarte?")

        return "\n".join(lines)

    @staticmethod
    def action_proposal(
        action_type: str,
        target: str,
        changes: list[dict[str, Any]],
        expected_impact: Optional[str] = None
    ) -> str:
        """Template for proposing actions (human-in-the-loop).

        Args:
            action_type: Type of action
            target: Campaign/keyword being modified
            changes: List of proposed changes
            expected_impact: Expected result

        Returns:
            Formatted proposal
        """
        lines = [
            "# 📋 Propuesta de Optimización\n",
            f"**Tipo:** {action_type}",
            f"**Objetivo:** {target}\n",
            "## Cambios Propuestos\n",
        ]

        for change in changes:
            action = change.get("action", "")
            detail = change.get("detail", "")
            lines.append(f"- ✏️ **{action}**: {detail}")

        lines.append("")

        if expected_impact:
            lines.extend([
                "## 📈 Impacto Esperado\n",
                expected_impact,
                "",
            ])

        lines.extend([
            "---",
            "**¿Deseas aprobar estos cambios?**",
            "Responde 'aprobar' para ejecutar o 'modificar' para ajustar.",
        ])

        return "\n".join(lines)


# Convenience functions
def get_campaign_template() -> str:
    """Get empty campaign analysis template."""
    return """## 📊 Resumen Ejecutivo
[Hallazgo principal en 1-2 oraciones]

## 🔢 Métricas Clave
| Métrica | Valor | vs. Benchmark |
|---------|-------|---------------|

## 💡 Insights
1. [Insight con el "por qué" detrás]
2. [Segundo insight]

## ✅ Recomendaciones
1. **[Acción prioritaria]** - [Impacto esperado]
2. **[Segunda acción]** - [Impacto esperado]
"""


def get_diagnostic_template() -> str:
    """Get empty diagnostic template."""
    return """## 📊 Diagnóstico
[¿Qué está pasando?]

## 🔍 Análisis
[¿Por qué está pasando?]

## ✅ Solución Recomendada
1. [Paso 1]
2. [Paso 2]
"""
