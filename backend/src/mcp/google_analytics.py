"""Google Analytics MCP tool for GA4 data queries.

Provides tools to query Google Analytics 4 data via the Data API.
"""

from datetime import datetime, timedelta
from typing import Any

import structlog
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    RunRealtimeReportRequest,
)
from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
from vertexai.generative_models import FunctionDeclaration

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class GoogleAnalyticsTool:
    """MCP tool for Google Analytics 4 data queries."""

    def __init__(self) -> None:
        """Initialize GA4 clients (Data API and Admin API)."""
        self.data_client = BetaAnalyticsDataClient()
        self.admin_client = AnalyticsAdminServiceClient()
        self.default_property_id = settings.ga4_property_id

    def get_function_declarations(self) -> list[FunctionDeclaration]:
        """Get Gemini function declarations for GA4 tools.

        Returns:
            List of function declarations
        """
        return [
            FunctionDeclaration(
                name="ga_list_properties",
                description="Lista todas las propiedades de Google Analytics 4 a las que tienes acceso. Usa esto primero para ver qué propiedades puedes consultar.",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            FunctionDeclaration(
                name="run_report",
                description="Ejecuta un reporte de Google Analytics 4 con métricas y dimensiones específicas. Usa esto para obtener datos históricos como sesiones, usuarios, conversiones, etc.",
                parameters={
                    "type": "object",
                    "properties": {
                        "property_id": {
                            "type": "string",
                            "description": "ID de la propiedad GA4 (ej: 512088907). Si no se especifica, usa la propiedad por defecto.",
                        },
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de métricas GA4 (ej: sessions, activeUsers, conversions, screenPageViews, bounceRate, averageSessionDuration)",
                        },
                        "dimensions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Lista de dimensiones GA4 (ej: date, country, city, deviceCategory, sessionSource, pagePath)",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Fecha de inicio (YYYY-MM-DD) o 'today', 'yesterday', '7daysAgo', '30daysAgo'",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Fecha de fin (YYYY-MM-DD) o 'today', 'yesterday'",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Número máximo de filas a retornar (default: 10)",
                        },
                    },
                    "required": ["metrics"],
                },
            ),
            FunctionDeclaration(
                name="run_realtime_report",
                description="Obtiene datos en tiempo real de Google Analytics 4. Útil para ver usuarios activos ahora mismo.",
                parameters={
                    "type": "object",
                    "properties": {
                        "property_id": {
                            "type": "string",
                            "description": "ID de la propiedad GA4 (ej: 512088907). Si no se especifica, usa la propiedad por defecto.",
                        },
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Métricas de tiempo real (ej: activeUsers, screenPageViews, conversions)",
                        },
                        "dimensions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Dimensiones de tiempo real (ej: country, city, deviceCategory, unifiedScreenName)",
                        },
                    },
                    "required": ["metrics"],
                },
            ),
            FunctionDeclaration(
                name="get_property_details",
                description="Obtiene información sobre la propiedad de Google Analytics configurada.",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a GA4 tool.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name == "ga_list_properties":
            return await self._list_properties()
        elif tool_name == "run_report":
            return await self._run_report(args)
        elif tool_name == "run_realtime_report":
            return await self._run_realtime_report(args)
        elif tool_name == "get_property_details":
            return await self._get_property_details()
        else:
            return {"error": f"Unknown GA4 tool: {tool_name}"}

    async def _run_report(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run a GA4 report.

        Args:
            args: Report parameters

        Returns:
            Report data as dictionary
        """
        try:
            property_id = args.get("property_id", self.default_property_id)
            metrics = args.get("metrics", ["sessions"])
            dimensions = args.get("dimensions", [])
            start_date = args.get("start_date", "7daysAgo")
            end_date = args.get("end_date", "today")
            limit = args.get("limit", 10)

            request = RunReportRequest(
                property=f"properties/{property_id}",
                metrics=[Metric(name=m) for m in metrics],
                dimensions=[Dimension(name=d) for d in dimensions] if dimensions else [],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                limit=limit,
            )

            response = self.data_client.run_report(request)

            # Format response
            result = {
                "property_id": property_id,
                "metrics": metrics,
                "dimensions": dimensions,
                "date_range": {"start": start_date, "end": end_date},
                "row_count": response.row_count,
                "rows": [],
            }

            for row in response.rows:
                row_data: dict[str, Any] = {}

                # Add dimension values
                for i, dim in enumerate(dimensions):
                    row_data[dim] = row.dimension_values[i].value

                # Add metric values
                for i, metric in enumerate(metrics):
                    row_data[metric] = row.metric_values[i].value

                result["rows"].append(row_data)

            logger.info(
                "GA4 report executed",
                metrics=metrics,
                rows=len(result["rows"]),
            )

            return result

        except Exception as e:
            logger.error("GA4 report failed", error=str(e), exc_info=True)
            return {"error": str(e)}

    async def _run_realtime_report(self, args: dict[str, Any]) -> dict[str, Any]:
        """Run a GA4 realtime report.

        Args:
            args: Report parameters

        Returns:
            Realtime report data
        """
        try:
            property_id = args.get("property_id", self.default_property_id)
            metrics = args.get("metrics", ["activeUsers"])
            dimensions = args.get("dimensions", [])

            request = RunRealtimeReportRequest(
                property=f"properties/{property_id}",
                metrics=[Metric(name=m) for m in metrics],
                dimensions=[Dimension(name=d) for d in dimensions] if dimensions else [],
            )

            response = self.data_client.run_realtime_report(request)

            # Format response
            result = {
                "property_id": property_id,
                "metrics": metrics,
                "dimensions": dimensions,
                "timestamp": datetime.utcnow().isoformat(),
                "row_count": response.row_count,
                "rows": [],
            }

            for row in response.rows:
                row_data: dict[str, Any] = {}

                for i, dim in enumerate(dimensions):
                    row_data[dim] = row.dimension_values[i].value

                for i, metric in enumerate(metrics):
                    row_data[metric] = row.metric_values[i].value

                result["rows"].append(row_data)

            logger.info(
                "GA4 realtime report executed",
                metrics=metrics,
                rows=len(result["rows"]),
            )

            return result

        except Exception as e:
            logger.error("GA4 realtime report failed", error=str(e), exc_info=True)
            return {"error": str(e)}

    async def _get_property_details(self) -> dict[str, Any]:
        """Get GA4 property details.

        Returns:
            Property information
        """
        try:
            return {
                "property_id": self.default_property_id,
                "property_name": f"properties/{self.default_property_id}",
                "status": "connected",
            }
        except Exception as e:
            return {"error": str(e)}

    async def _list_properties(self) -> dict[str, Any]:
        """List all accessible GA4 properties using Admin API.

        Returns:
            List of properties with their IDs and names
        """
        try:
            properties = []

            # List all account summaries (includes all properties)
            for account_summary in self.admin_client.list_account_summaries():
                account_name = account_summary.display_name
                account_id = account_summary.account.split("/")[-1]

                for prop_summary in account_summary.property_summaries:
                    prop_id = prop_summary.property.split("/")[-1]
                    properties.append({
                        "property_id": prop_id,
                        "property_name": prop_summary.display_name,
                        "account_id": account_id,
                        "account_name": account_name,
                    })

            logger.info("Listed GA4 properties", count=len(properties))

            return {
                "properties": properties,
                "count": len(properties),
                "default_property_id": self.default_property_id,
            }

        except Exception as e:
            logger.error("Failed to list GA4 properties", error=str(e), exc_info=True)
            return {"error": str(e)}
