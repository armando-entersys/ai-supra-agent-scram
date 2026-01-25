"""Autonomous Agent capabilities for proactive data exploration.

Implements ReAct (Reasoning + Acting) pattern for intelligent,
autonomous decision-making and data discovery.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional
import structlog
from google.cloud import bigquery

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class DataDiscovery:
    """Autonomous data discovery and exploration."""

    def __init__(self) -> None:
        """Initialize data discovery."""
        self.project_id = settings.gcp_project_id
        self.client = bigquery.Client(project=self.project_id)
        self._schema_cache: dict[str, Any] = {}
        self._data_summary_cache: dict[str, Any] = {}
        logger.info("DataDiscovery initialized")

    async def discover_all_data(self) -> dict[str, Any]:
        """Automatically discover and summarize all available data.

        Returns:
            Complete data landscape summary
        """
        discovery = {
            "discovered_at": datetime.now().isoformat(),
            "datasets": {},
            "relationships": [],
            "recommended_analyses": []
        }

        try:
            # Get all datasets
            datasets = list(self.client.list_datasets())

            for dataset in datasets:
                dataset_id = dataset.dataset_id
                discovery["datasets"][dataset_id] = {
                    "tables": {},
                    "total_rows": 0,
                    "total_size_mb": 0
                }

                # Get all tables in dataset
                tables = list(self.client.list_tables(dataset.reference))

                for table in tables:
                    table_ref = self.client.get_table(table.reference)
                    table_info = {
                        "name": table.table_id,
                        "rows": table_ref.num_rows,
                        "size_mb": round(table_ref.num_bytes / (1024 * 1024), 2) if table_ref.num_bytes else 0,
                        "columns": [],
                        "sample_values": {}
                    }

                    # Get schema
                    for field in table_ref.schema:
                        table_info["columns"].append({
                            "name": field.name,
                            "type": field.field_type,
                            "description": field.description
                        })

                    # Get sample values for key columns
                    try:
                        sample_query = f"""
                            SELECT * FROM `{self.project_id}.{dataset_id}.{table.table_id}`
                            LIMIT 3
                        """
                        sample_results = list(self.client.query(sample_query).result())
                        if sample_results:
                            for col in table_info["columns"][:5]:  # First 5 columns
                                col_name = col["name"]
                                values = [str(getattr(row, col_name, ""))[:50] for row in sample_results]
                                table_info["sample_values"][col_name] = values
                    except Exception:
                        pass

                    discovery["datasets"][dataset_id]["tables"][table.table_id] = table_info
                    discovery["datasets"][dataset_id]["total_rows"] += table_info["rows"] or 0
                    discovery["datasets"][dataset_id]["total_size_mb"] += table_info["size_mb"]

            # Detect relationships between tables
            discovery["relationships"] = self._detect_relationships(discovery["datasets"])

            # Generate recommended analyses
            discovery["recommended_analyses"] = self._generate_recommendations(discovery["datasets"])

            logger.info("Data discovery completed", datasets=len(discovery["datasets"]))
            return discovery

        except Exception as e:
            logger.error("Data discovery failed", error=str(e))
            return {"error": str(e)}

    def _detect_relationships(self, datasets: dict) -> list[dict]:
        """Detect potential relationships between tables."""
        relationships = []

        # Common join keys to look for
        join_keys = ["customer_id", "campaign_id", "user_id", "email", "city", "state", "date"]

        all_tables = []
        for dataset_id, dataset_info in datasets.items():
            for table_id, table_info in dataset_info.get("tables", {}).items():
                columns = [c["name"] for c in table_info.get("columns", [])]
                all_tables.append({
                    "dataset": dataset_id,
                    "table": table_id,
                    "columns": columns
                })

        # Find common columns between tables
        for i, table1 in enumerate(all_tables):
            for table2 in all_tables[i+1:]:
                common = set(table1["columns"]) & set(table2["columns"])
                join_candidates = [c for c in common if any(k in c.lower() for k in join_keys)]

                if join_candidates:
                    relationships.append({
                        "table1": f"{table1['dataset']}.{table1['table']}",
                        "table2": f"{table2['dataset']}.{table2['table']}",
                        "join_columns": join_candidates,
                        "relationship_type": "potential_join"
                    })

        return relationships

    def _generate_recommendations(self, datasets: dict) -> list[dict]:
        """Generate recommended analyses based on available data."""
        recommendations = []

        # Check for Google Ads data
        if "google_ads_data" in datasets:
            ads_tables = datasets["google_ads_data"].get("tables", {})

            if "campaign_performance" in ads_tables and "search_terms" in ads_tables:
                recommendations.append({
                    "title": "Análisis de Términos de Búsqueda por Campaña",
                    "description": "Cruzar rendimiento de campañas con términos de búsqueda para identificar keywords de alto/bajo rendimiento",
                    "tables": ["campaign_performance", "search_terms"],
                    "query_template": """
                        SELECT
                            c.campaign_name,
                            s.search_term,
                            SUM(s.clicks) as clicks,
                            SUM(s.cost) as cost,
                            SUM(s.conversions) as conversions
                        FROM google_ads_data.campaign_performance c
                        JOIN google_ads_data.search_terms s
                            ON c.campaign_id = s.campaign_id
                        GROUP BY 1, 2
                        ORDER BY clicks DESC
                    """
                })

            if "device_performance" in ads_tables:
                recommendations.append({
                    "title": "Análisis de Rendimiento por Dispositivo",
                    "description": "Identificar qué dispositivos generan mejor ROI",
                    "tables": ["device_performance"],
                    "priority": "high"
                })

        # Check for prospects data
        if "prospects_data" in datasets:
            prospects_tables = datasets["prospects_data"].get("tables", {})

            if "industrial_clients" in prospects_tables:
                recommendations.append({
                    "title": "Segmentación Geográfica de Clientes",
                    "description": "Analizar distribución de clientes por ciudad/estado para optimizar targeting",
                    "tables": ["industrial_clients"],
                    "priority": "high"
                })

                # Cross-analysis with ads
                if "google_ads_data" in datasets:
                    recommendations.append({
                        "title": "Alineación Clientes-Campañas",
                        "description": "Comparar ubicación de clientes actuales con inversión publicitaria",
                        "tables": ["industrial_clients", "geographic_performance"],
                        "priority": "critical"
                    })

        return recommendations

    async def get_data_context(self) -> str:
        """Get a concise data context string for the AI model.

        Returns:
            Formatted string describing available data
        """
        try:
            discovery = await self.discover_all_data()

            lines = ["## 📊 DATOS DISPONIBLES EN BIGQUERY\n"]

            for dataset_id, dataset_info in discovery.get("datasets", {}).items():
                lines.append(f"### Dataset: `{dataset_id}`")

                for table_id, table_info in dataset_info.get("tables", {}).items():
                    rows = table_info.get("rows", 0)
                    columns = [c["name"] for c in table_info.get("columns", [])]
                    lines.append(f"- **{table_id}** ({rows:,} filas): {', '.join(columns[:6])}")

                lines.append("")

            # Add relationships
            if discovery.get("relationships"):
                lines.append("### 🔗 Relaciones Detectadas")
                for rel in discovery["relationships"][:5]:
                    lines.append(f"- `{rel['table1']}` ↔ `{rel['table2']}` via `{', '.join(rel['join_columns'])}`")
                lines.append("")

            # Add recommendations
            if discovery.get("recommended_analyses"):
                lines.append("### 💡 Análisis Recomendados")
                for rec in discovery["recommended_analyses"][:3]:
                    lines.append(f"- **{rec['title']}**: {rec['description']}")

            return "\n".join(lines)

        except Exception as e:
            logger.error("Failed to get data context", error=str(e))
            return ""


class QueryPlanner:
    """Plans and optimizes multi-step queries."""

    def __init__(self) -> None:
        """Initialize query planner."""
        self.project_id = settings.gcp_project_id

    def plan_analysis(self, question: str, available_tables: list[str]) -> list[dict]:
        """Plan a multi-step analysis based on the question.

        Args:
            question: User's question
            available_tables: List of available tables

        Returns:
            List of planned query steps
        """
        question_lower = question.lower()
        steps = []

        # Detect intent and plan accordingly
        if any(word in question_lower for word in ["comparar", "cruzar", "relacionar", "vs"]):
            steps.append({
                "step": 1,
                "action": "identify_tables",
                "description": "Identificar tablas relevantes para el cruce"
            })
            steps.append({
                "step": 2,
                "action": "find_join_keys",
                "description": "Encontrar columnas comunes para hacer JOIN"
            })
            steps.append({
                "step": 3,
                "action": "execute_cross_query",
                "description": "Ejecutar consulta cruzada"
            })

        elif any(word in question_lower for word in ["tendencia", "evolución", "histórico", "tiempo"]):
            steps.append({
                "step": 1,
                "action": "identify_date_column",
                "description": "Identificar columna de fecha"
            })
            steps.append({
                "step": 2,
                "action": "aggregate_by_time",
                "description": "Agregar datos por período de tiempo"
            })
            steps.append({
                "step": 3,
                "action": "calculate_trends",
                "description": "Calcular tendencias y variaciones"
            })

        elif any(word in question_lower for word in ["top", "mejor", "peor", "ranking"]):
            steps.append({
                "step": 1,
                "action": "identify_metric",
                "description": "Identificar métrica principal"
            })
            steps.append({
                "step": 2,
                "action": "rank_entities",
                "description": "Ordenar entidades por métrica"
            })

        elif any(word in question_lower for word in ["anomalía", "problema", "alerta", "detectar"]):
            steps.append({
                "step": 1,
                "action": "calculate_baselines",
                "description": "Calcular líneas base y promedios"
            })
            steps.append({
                "step": 2,
                "action": "detect_outliers",
                "description": "Detectar valores atípicos"
            })
            steps.append({
                "step": 3,
                "action": "analyze_root_cause",
                "description": "Analizar posibles causas"
            })

        else:
            # Default exploratory analysis
            steps.append({
                "step": 1,
                "action": "explore_data",
                "description": "Explorar datos disponibles"
            })
            steps.append({
                "step": 2,
                "action": "summarize_findings",
                "description": "Resumir hallazgos principales"
            })

        return steps


class AutonomousAnalyzer:
    """Autonomous analysis engine that proactively explores data."""

    def __init__(self) -> None:
        """Initialize autonomous analyzer."""
        self.discovery = DataDiscovery()
        self.planner = QueryPlanner()
        self.client = bigquery.Client(project=settings.gcp_project_id)

    async def auto_analyze(self, context: str = "") -> dict[str, Any]:
        """Perform autonomous analysis of all available data.

        Args:
            context: Optional context about what to focus on

        Returns:
            Comprehensive analysis results
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "data_overview": {},
            "key_metrics": {},
            "anomalies": [],
            "opportunities": [],
            "recommendations": []
        }

        try:
            # 1. Discover all data
            discovery = await self.discovery.discover_all_data()
            results["data_overview"] = {
                "datasets": len(discovery.get("datasets", {})),
                "total_tables": sum(
                    len(d.get("tables", {}))
                    for d in discovery.get("datasets", {}).values()
                ),
                "relationships": len(discovery.get("relationships", []))
            }

            # 2. Analyze Google Ads performance
            if "google_ads_data" in discovery.get("datasets", {}):
                ads_analysis = await self._analyze_google_ads()
                results["key_metrics"]["google_ads"] = ads_analysis

            # 3. Analyze prospects/clients
            if "prospects_data" in discovery.get("datasets", {}):
                prospects_analysis = await self._analyze_prospects()
                results["key_metrics"]["prospects"] = prospects_analysis

            # 4. Cross-analysis
            if "google_ads_data" in discovery.get("datasets", {}) and \
               "prospects_data" in discovery.get("datasets", {}):
                cross_analysis = await self._cross_analyze()
                results["cross_analysis"] = cross_analysis

            # 5. Detect anomalies
            results["anomalies"] = await self._detect_anomalies()

            # 6. Generate recommendations
            results["recommendations"] = self._generate_action_items(results)

            logger.info("Autonomous analysis completed")
            return results

        except Exception as e:
            logger.error("Autonomous analysis failed", error=str(e))
            return {"error": str(e)}

    async def _analyze_google_ads(self) -> dict:
        """Analyze Google Ads performance."""
        try:
            query = """
                SELECT
                    campaign_name,
                    SUM(impressions) as impressions,
                    SUM(clicks) as clicks,
                    SUM(cost) as cost,
                    SUM(conversions) as conversions,
                    SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100 as ctr,
                    SAFE_DIVIDE(SUM(cost), SUM(clicks)) as cpc,
                    SAFE_DIVIDE(SUM(cost), NULLIF(SUM(conversions), 0)) as cpa
                FROM `mi-infraestructura-web.google_ads_data.campaign_performance`
                GROUP BY campaign_name
            """
            results = list(self.client.query(query).result())

            return {
                "campaigns": len(results),
                "total_spend": sum(r.cost or 0 for r in results),
                "total_conversions": sum(r.conversions or 0 for r in results),
                "avg_ctr": sum(r.ctr or 0 for r in results) / len(results) if results else 0,
                "campaigns_without_conversions": sum(1 for r in results if (r.conversions or 0) == 0)
            }
        except Exception as e:
            return {"error": str(e)}

    async def _analyze_prospects(self) -> dict:
        """Analyze prospects data."""
        try:
            query = """
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT city) as cities,
                    COUNT(DISTINCT state) as states,
                    COUNT(DISTINCT segment) as segments
                FROM `mi-infraestructura-web.prospects_data.industrial_clients`
            """
            result = list(self.client.query(query).result())[0]

            return {
                "total_clients": result.total,
                "unique_cities": result.cities,
                "unique_states": result.states,
                "segments": result.segments
            }
        except Exception as e:
            return {"error": str(e)}

    async def _cross_analyze(self) -> dict:
        """Cross-analyze different data sources."""
        try:
            # Get top client cities
            client_cities_query = """
                SELECT LOWER(TRIM(city)) as city, COUNT(*) as clients
                FROM `mi-infraestructura-web.prospects_data.industrial_clients`
                WHERE city IS NOT NULL
                GROUP BY 1
                ORDER BY clients DESC
                LIMIT 10
            """
            client_cities = {
                row.city: row.clients
                for row in self.client.query(client_cities_query).result()
            }

            # Get search terms with city names
            search_terms_query = """
                SELECT search_term, SUM(clicks) as clicks, SUM(cost) as cost
                FROM `mi-infraestructura-web.google_ads_data.search_terms`
                GROUP BY search_term
            """
            search_results = list(self.client.query(search_terms_query).result())

            # Find overlap
            city_coverage = {}
            for city, client_count in client_cities.items():
                matching_searches = [
                    s for s in search_results
                    if city in s.search_term.lower()
                ]
                city_coverage[city] = {
                    "clients": client_count,
                    "search_terms": len(matching_searches),
                    "clicks": sum(s.clicks or 0 for s in matching_searches),
                    "cost": sum(s.cost or 0 for s in matching_searches)
                }

            return {
                "client_cities_analyzed": len(client_cities),
                "cities_with_ad_coverage": sum(1 for c in city_coverage.values() if c["clicks"] > 0),
                "coverage_details": city_coverage
            }
        except Exception as e:
            return {"error": str(e)}

    async def _detect_anomalies(self) -> list[dict]:
        """Detect anomalies in the data."""
        anomalies = []

        try:
            # Check for campaigns with high spend and zero conversions
            query = """
                SELECT campaign_name, SUM(cost) as cost, SUM(conversions) as conv
                FROM `mi-infraestructura-web.google_ads_data.campaign_performance`
                GROUP BY campaign_name
                HAVING SUM(cost) > 100 AND SUM(conversions) = 0
            """
            for row in self.client.query(query).result():
                anomalies.append({
                    "type": "high_spend_no_conversions",
                    "severity": "critical",
                    "entity": row.campaign_name,
                    "details": f"${row.cost:.2f} gastados, 0 conversiones"
                })

            # Check for unusually high CPC
            cpc_query = """
                SELECT campaign_name,
                       SAFE_DIVIDE(SUM(cost), SUM(clicks)) as cpc
                FROM `mi-infraestructura-web.google_ads_data.campaign_performance`
                WHERE clicks > 0
                GROUP BY campaign_name
                HAVING SAFE_DIVIDE(SUM(cost), SUM(clicks)) > 5
            """
            for row in self.client.query(cpc_query).result():
                anomalies.append({
                    "type": "high_cpc",
                    "severity": "warning",
                    "entity": row.campaign_name,
                    "details": f"CPC de ${row.cpc:.2f} (muy alto)"
                })

        except Exception as e:
            logger.error("Anomaly detection failed", error=str(e))

        return anomalies

    def _generate_action_items(self, analysis: dict) -> list[dict]:
        """Generate actionable recommendations."""
        recommendations = []

        # Based on anomalies
        for anomaly in analysis.get("anomalies", []):
            if anomaly["type"] == "high_spend_no_conversions":
                recommendations.append({
                    "priority": "urgent",
                    "action": f"Revisar urgentemente campaña '{anomaly['entity']}'",
                    "reason": anomaly["details"],
                    "steps": [
                        "Verificar tracking de conversiones",
                        "Auditar landing page en móvil",
                        "Revisar calidad de keywords"
                    ]
                })

        # Based on cross-analysis
        cross = analysis.get("cross_analysis", {})
        if cross.get("cities_with_ad_coverage", 0) < cross.get("client_cities_analyzed", 0) / 2:
            recommendations.append({
                "priority": "high",
                "action": "Expandir targeting geográfico",
                "reason": "Menos del 50% de ciudades con clientes tienen cobertura publicitaria",
                "steps": [
                    "Crear campañas hiper-locales para ciudades desatendidas",
                    "Aumentar pujas en ubicaciones con clientes existentes"
                ]
            })

        return recommendations


# Singleton instances
_discovery_instance: Optional[DataDiscovery] = None
_analyzer_instance: Optional[AutonomousAnalyzer] = None


def get_data_discovery() -> Optional[DataDiscovery]:
    """Get or create data discovery instance."""
    global _discovery_instance
    if _discovery_instance is None:
        try:
            _discovery_instance = DataDiscovery()
        except Exception as e:
            logger.error("Failed to initialize DataDiscovery", error=str(e))
            return None
    return _discovery_instance


def get_autonomous_analyzer() -> Optional[AutonomousAnalyzer]:
    """Get or create autonomous analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        try:
            _analyzer_instance = AutonomousAnalyzer()
        except Exception as e:
            logger.error("Failed to initialize AutonomousAnalyzer", error=str(e))
            return None
    return _analyzer_instance
