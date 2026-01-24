"""BigQuery MCP tool for advanced analytics.

Provides tools to query BigQuery datasets including GA4 exports,
Google Ads data, and custom analytics tables.
"""

from typing import Any
import structlog
from google.cloud import bigquery
from vertexai.generative_models import FunctionDeclaration

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class BigQueryTool:
    """MCP tool for BigQuery data queries."""

    def __init__(self, project_id: str | None = None) -> None:
        """Initialize BigQuery client.

        Args:
            project_id: GCP project ID. Uses settings if not provided.
        """
        self.project_id = project_id or settings.gcp_project_id
        self.client = bigquery.Client(project=self.project_id)
        logger.info("BigQuery tool initialized", project_id=self.project_id)

    def get_function_declarations(self) -> list[FunctionDeclaration]:
        """Get Gemini function declarations for BigQuery tools.

        Returns:
            List of function declarations
        """
        return [
            FunctionDeclaration(
                name="bq_list_datasets",
                description="""Lista todos los datasets disponibles en BigQuery del proyecto.
                Usa esto primero para ver qué datos tienes disponibles (GA4 exports, Google Ads, etc.).""",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            FunctionDeclaration(
                name="bq_list_tables",
                description="""Lista todas las tablas dentro de un dataset de BigQuery.
                Útil para ver las tablas de eventos de GA4 (events_*) o tablas de Google Ads.""",
                parameters={
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "ID del dataset (ej: analytics_123456789, google_ads_data)",
                        },
                    },
                    "required": ["dataset_id"],
                },
            ),
            FunctionDeclaration(
                name="bq_get_table_schema",
                description="""Obtiene el esquema (columnas y tipos) de una tabla de BigQuery.
                Útil para entender la estructura antes de hacer queries.""",
                parameters={
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "ID del dataset",
                        },
                        "table_id": {
                            "type": "string",
                            "description": "ID de la tabla (ej: events_20241201, events_*)",
                        },
                    },
                    "required": ["dataset_id", "table_id"],
                },
            ),
            FunctionDeclaration(
                name="bq_run_query",
                description="""Ejecuta una consulta SQL en BigQuery y retorna los resultados.

                IMPORTANTE: Usa esto para análisis avanzados que combinan GA4 + Google Ads.

                Ejemplos de queries útiles:
                - Eventos de GA4: SELECT * FROM `project.analytics_*.events_*` WHERE event_name = 'purchase'
                - Sesiones por fuente: SELECT traffic_source.source, COUNT(*) FROM `analytics_*.events_*` GROUP BY 1
                - Conversiones con costo: Combinar GA4 events con Google Ads cost data

                SIEMPRE usa LIMIT para evitar resultados muy grandes.""",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Consulta SQL de BigQuery. Siempre incluye LIMIT.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Máximo de filas a retornar (default: 100, max: 1000)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            FunctionDeclaration(
                name="bq_ga4_events_summary",
                description="""Obtiene un resumen de eventos de GA4 desde BigQuery para un rango de fechas.
                Más detallado que la API estándar de GA4. Incluye parámetros de eventos.""",
                parameters={
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "ID del dataset de GA4 (ej: analytics_123456789)",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Fecha inicio YYYYMMDD (ej: 20241201)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Fecha fin YYYYMMDD (ej: 20241231)",
                        },
                        "event_name": {
                            "type": "string",
                            "description": "Filtrar por evento específico (opcional, ej: page_view, purchase, generate_lead)",
                        },
                    },
                    "required": ["dataset_id", "start_date", "end_date"],
                },
            ),
            FunctionDeclaration(
                name="bq_ads_performance",
                description="""Obtiene métricas de rendimiento de Google Ads desde BigQuery.
                Permite análisis más profundos que la API estándar.""",
                parameters={
                    "type": "object",
                    "properties": {
                        "dataset_id": {
                            "type": "string",
                            "description": "ID del dataset de Google Ads en BigQuery",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Fecha inicio YYYY-MM-DD",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Fecha fin YYYY-MM-DD",
                        },
                        "group_by": {
                            "type": "string",
                            "description": "Agrupar por: campaign, ad_group, keyword, date",
                        },
                    },
                    "required": ["dataset_id"],
                },
            ),
            FunctionDeclaration(
                name="bq_export_google_ads",
                description="""Exporta TODOS los datos de Google Ads a BigQuery.
                Sincroniza datos completos incluyendo:
                - campaign_performance: Rendimiento por campaña
                - keyword_performance: Rendimiento por keyword
                - search_terms: Términos de búsqueda reales
                - ad_group_performance: Rendimiento por grupo de anuncios
                - device_performance: Rendimiento por dispositivo (móvil, desktop, tablet)
                - geographic_performance: Rendimiento por ubicación geográfica
                - hourly_performance: Rendimiento por hora del día y día de la semana""",
                parameters={
                    "type": "object",
                    "properties": {
                        "days_back": {
                            "type": "integer",
                            "description": "Días de historial a exportar (default: 30)",
                        },
                    },
                },
            ),
            FunctionDeclaration(
                name="bq_upload_prospects",
                description="""Sube datos de prospectos/clientes desde archivos CSV a BigQuery.
                Crea el dataset prospects_data con tablas optimizadas para análisis de marketing.
                Tipos de archivos soportados:
                - industrial_clients: Prospectos industriales (USA, Canadá, México)
                - contractors: Contratistas y terceros""",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_type": {
                            "type": "string",
                            "description": "Tipo de archivo: 'industrial_clients' o 'contractors'",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Ruta al archivo CSV",
                        },
                    },
                    "required": ["file_type", "file_path"],
                },
            ),
        ]

    async def execute(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        """Execute a BigQuery tool.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool

        Returns:
            Tool execution result as string
        """
        try:
            if tool_name == "bq_list_datasets":
                return await self._list_datasets()
            elif tool_name == "bq_list_tables":
                return await self._list_tables(tool_args.get("dataset_id", ""))
            elif tool_name == "bq_get_table_schema":
                return await self._get_table_schema(
                    tool_args.get("dataset_id", ""),
                    tool_args.get("table_id", ""),
                )
            elif tool_name == "bq_run_query":
                return await self._run_query(
                    tool_args.get("query", ""),
                    tool_args.get("max_results", 100),
                )
            elif tool_name == "bq_ga4_events_summary":
                return await self._ga4_events_summary(
                    tool_args.get("dataset_id", ""),
                    tool_args.get("start_date", ""),
                    tool_args.get("end_date", ""),
                    tool_args.get("event_name"),
                )
            elif tool_name == "bq_ads_performance":
                return await self._ads_performance(
                    tool_args.get("dataset_id", ""),
                    tool_args.get("start_date"),
                    tool_args.get("end_date"),
                    tool_args.get("group_by", "campaign"),
                )
            elif tool_name == "bq_export_google_ads":
                return await self._export_google_ads(
                    tool_args.get("days_back", 30),
                )
            elif tool_name == "bq_upload_prospects":
                return await self._upload_prospects(
                    tool_args.get("file_type", ""),
                    tool_args.get("file_path", ""),
                )
            else:
                return f"Error: Unknown BigQuery tool: {tool_name}"
        except Exception as e:
            logger.error("BigQuery tool error", tool=tool_name, error=str(e))
            return f"Error ejecutando {tool_name}: {str(e)}"

    async def _list_datasets(self) -> str:
        """List all datasets in the project."""
        try:
            datasets = list(self.client.list_datasets())
            if not datasets:
                return "No se encontraron datasets en el proyecto."

            result = ["📊 **Datasets disponibles en BigQuery:**\n"]
            for dataset in datasets:
                dataset_ref = dataset.reference
                result.append(f"- **{dataset_ref.dataset_id}** (proyecto: {dataset_ref.project})")

            return "\n".join(result)
        except Exception as e:
            return f"Error listando datasets: {str(e)}"

    async def _list_tables(self, dataset_id: str) -> str:
        """List all tables in a dataset."""
        try:
            tables = list(self.client.list_tables(dataset_id))
            if not tables:
                return f"No se encontraron tablas en el dataset '{dataset_id}'."

            result = [f"📋 **Tablas en dataset '{dataset_id}':**\n"]
            for table in tables[:50]:  # Limit to 50 tables
                table_type = "🗓️" if "events_" in table.table_id else "📊"
                result.append(f"- {table_type} {table.table_id}")

            if len(tables) > 50:
                result.append(f"\n... y {len(tables) - 50} tablas más")

            return "\n".join(result)
        except Exception as e:
            return f"Error listando tablas: {str(e)}"

    async def _get_table_schema(self, dataset_id: str, table_id: str) -> str:
        """Get schema of a table."""
        try:
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            table = self.client.get_table(table_ref)

            result = [f"📝 **Esquema de '{table_id}':**\n"]
            result.append(f"- Filas: {table.num_rows:,}")
            result.append(f"- Tamaño: {table.num_bytes / (1024*1024):.2f} MB\n")
            result.append("**Columnas:**")

            for field in table.schema[:30]:  # Limit to 30 fields
                field_type = field.field_type
                mode = " (REPEATED)" if field.mode == "REPEATED" else ""
                result.append(f"- `{field.name}`: {field_type}{mode}")

            if len(table.schema) > 30:
                result.append(f"\n... y {len(table.schema) - 30} columnas más")

            return "\n".join(result)
        except Exception as e:
            return f"Error obteniendo esquema: {str(e)}"

    async def _run_query(self, query: str, max_results: int = 100) -> str:
        """Run a SQL query on BigQuery."""
        try:
            # Safety: ensure LIMIT is present
            max_results = min(max_results, 1000)
            if "LIMIT" not in query.upper():
                query = f"{query} LIMIT {max_results}"

            logger.info("Executing BigQuery query", query=query[:200])

            query_job = self.client.query(query)
            results = query_job.result()

            rows = list(results)
            if not rows:
                return "La consulta no retornó resultados."

            # Format results as table
            schema = results.schema
            headers = [field.name for field in schema]

            result = [f"📊 **Resultados ({len(rows)} filas):**\n"]
            result.append("| " + " | ".join(headers) + " |")
            result.append("| " + " | ".join(["---"] * len(headers)) + " |")

            for row in rows[:max_results]:
                values = [str(row[h])[:50] for h in headers]  # Truncate long values
                result.append("| " + " | ".join(values) + " |")

            return "\n".join(result)
        except Exception as e:
            return f"Error ejecutando query: {str(e)}"

    async def _ga4_events_summary(
        self,
        dataset_id: str,
        start_date: str,
        end_date: str,
        event_name: str | None = None,
    ) -> str:
        """Get GA4 events summary from BigQuery."""
        try:
            event_filter = f"AND event_name = '{event_name}'" if event_name else ""

            query = f"""
            SELECT
                event_name,
                COUNT(*) as event_count,
                COUNT(DISTINCT user_pseudo_id) as unique_users,
                COUNTIF(device.category = 'mobile') as mobile_events,
                COUNTIF(device.category = 'desktop') as desktop_events
            FROM `{self.project_id}.{dataset_id}.events_*`
            WHERE _TABLE_SUFFIX BETWEEN '{start_date}' AND '{end_date}'
            {event_filter}
            GROUP BY event_name
            ORDER BY event_count DESC
            LIMIT 20
            """

            return await self._run_query(query, max_results=20)
        except Exception as e:
            return f"Error en resumen de eventos GA4: {str(e)}"

    async def _ads_performance(
        self,
        dataset_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        group_by: str = "campaign",
    ) -> str:
        """Get Google Ads performance from BigQuery."""
        try:
            # This is a generic template - actual table structure may vary
            date_filter = ""
            if start_date and end_date:
                date_filter = f"WHERE date BETWEEN '{start_date}' AND '{end_date}'"

            # Try common Google Ads BigQuery table structures
            query = f"""
            SELECT
                {group_by}_name as {group_by},
                SUM(impressions) as impressions,
                SUM(clicks) as clicks,
                ROUND(SUM(clicks) / NULLIF(SUM(impressions), 0) * 100, 2) as ctr,
                SUM(cost_micros) / 1000000 as cost,
                SUM(conversions) as conversions
            FROM `{self.project_id}.{dataset_id}.p_ads_*`
            {date_filter}
            GROUP BY 1
            ORDER BY cost DESC
            LIMIT 20
            """

            return await self._run_query(query, max_results=20)
        except Exception as e:
            return f"Error en rendimiento de Ads: {str(e)}"

    async def _export_google_ads(self, days_back: int = 30) -> str:
        """Export Google Ads data to BigQuery."""
        try:
            from src.mcp.ads_to_bigquery import get_ads_exporter

            exporter = get_ads_exporter()
            if not exporter:
                return "Error: Google Ads exporter not configured. Verifica las credenciales de Google Ads."

            result = await exporter.export_all(days_back=days_back)

            if result.get("success"):
                details = result.get("details", {})
                output = [
                    f"✅ **Exportación de Google Ads completada**\n",
                    f"📊 **Total de filas exportadas:** {result.get('total_rows_exported', 0)}\n",
                    "\n**Tablas actualizadas:**",
                ]

                for table_name, table_result in details.items():
                    if table_result.get("success"):
                        output.append(f"- `{table_result.get('table')}`: {table_result.get('rows_exported', 0)} filas")
                    else:
                        output.append(f"- `{table_name}`: ❌ Error - {table_result.get('error', 'Unknown')}")

                output.append(f"\n📅 Rango de fechas: {details.get('campaigns', {}).get('date_range', 'N/A')}")
                output.append("\n**Dataset:** `google_ads_data`")

                return "\n".join(output)
            else:
                return f"❌ Error en exportación: {result.get('error', 'Unknown error')}"

        except Exception as e:
            logger.error("Google Ads export error", error=str(e))
            return f"Error exportando datos de Google Ads: {str(e)}"

    async def _upload_prospects(self, file_type: str, file_path: str) -> str:
        """Upload prospect CSV data to BigQuery.

        Args:
            file_type: Type of file ('industrial_clients' or 'contractors')
            file_path: Path to the CSV file

        Returns:
            Upload result summary
        """
        try:
            from src.mcp.csv_to_bigquery import get_csv_uploader

            uploader = get_csv_uploader()
            if not uploader:
                return "Error: CSV uploader not initialized. Verifica la configuración de BigQuery."

            if file_type == "industrial_clients":
                result = await uploader.upload_industrial_clients(file_path)
            elif file_type == "contractors":
                result = await uploader.upload_contractors(file_path)
            else:
                return f"Error: Tipo de archivo no soportado: {file_type}. Usa 'industrial_clients' o 'contractors'."

            if result.get("success"):
                output = [
                    f"✅ **Carga de prospectos completada**\n",
                    f"📊 **Tabla:** `{result.get('table')}`",
                    f"📝 **Filas cargadas:** {result.get('rows_uploaded', 0)}",
                    f"📈 **Total en tabla:** {result.get('total_rows', 0)}\n",
                ]

                # Add segment breakdown if available
                segments = result.get("segments", [])
                if segments:
                    output.append("**Distribución por segmento:**")
                    for seg in segments[:10]:
                        output.append(f"- {seg.get('segment', 'N/A')}: {seg.get('count', 0)}")

                # Add country breakdown if available
                countries = result.get("countries", [])
                if countries:
                    output.append("\n**Distribución por país:**")
                    for country in countries[:10]:
                        output.append(f"- {country.get('country', 'N/A')}: {country.get('count', 0)}")

                return "\n".join(output)
            else:
                return f"❌ Error en carga: {result.get('error', 'Unknown error')}"

        except Exception as e:
            logger.error("CSV upload error", error=str(e))
            return f"Error subiendo datos CSV: {str(e)}"


def get_bigquery_tool() -> BigQueryTool | None:
    """Get BigQuery tool instance if configured.

    Returns:
        BigQueryTool instance or None if not configured
    """
    try:
        if not settings.gcp_project_id:
            logger.warning("BigQuery tool not configured: missing GCP_PROJECT_ID")
            return None

        return BigQueryTool()
    except Exception as e:
        logger.error("Failed to initialize BigQuery tool", error=str(e))
        return None
