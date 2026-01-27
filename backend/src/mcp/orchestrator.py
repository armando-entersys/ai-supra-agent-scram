"""Agent orchestrator for Gemini with MCP tools.

Coordinates the interaction between the LLM, RAG context,
and MCP tools (Google Analytics, Knowledge Base).

Improvements implemented:
- Temperature 1.0 (Google recommendation for Gemini 2.0+)
- Chain-of-Thought prompting
- Industry benchmarks integration
- Persistent memory system
- Proactive alerts
- Compositional function calling (up to 10 chained calls)
- Robust error handling with retries
"""

import json
from datetime import datetime
from typing import Any, AsyncGenerator
import asyncio

import structlog
from google.cloud import aiplatform
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Part,
    Tool,
)

from src.config import get_settings
from src.database.connection import async_session_maker
from src.mcp.google_analytics import GoogleAnalyticsTool
from src.mcp.google_ads import get_google_ads_tool, GoogleAdsTool
from src.mcp.knowledge_base import KnowledgeBaseTool
from src.mcp.web_search import get_web_search_tool, WebSearchTool
from src.mcp.bigquery import get_bigquery_tool, BigQueryTool
from src.mcp.autonomous_agent import get_data_discovery, get_autonomous_analyzer
from src.mcp.benchmarks import (
    get_benchmarks_for_campaign,
    compare_to_benchmark,
    format_benchmark_comparison,
    INDUSTRY_BENCHMARKS,
)
from src.mcp.memory import get_agent_memory
from src.mcp.alerts import get_campaign_alerts, format_alerts_for_display
from src.mcp.response_templates import ResponseTemplates
from src.rag.retrieval import get_context_for_query

logger = structlog.get_logger()
settings = get_settings()

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds


def _serialize_for_function_response(result: Any) -> dict:
    """Serialize result for Vertex AI function response.

    Vertex AI SDK has issues with complex nested structures (especially lists).
    Convert everything to a JSON string for maximum compatibility.

    Args:
        result: The raw result from a tool execution

    Returns:
        A dict suitable for Part.from_function_response
    """
    # Convert complex results to JSON string to avoid Vertex AI SDK issues
    # with nested lists and complex structures
    try:
        if result is None:
            return {"result": "null"}

        if isinstance(result, str):
            return {"result": result}

        if isinstance(result, (bool, int, float)):
            return {"result": str(result)}

        # For dicts and lists, convert to JSON string
        # This avoids the "'list' object has no attribute 'get'" error
        return {"result": json.dumps(result, ensure_ascii=False, default=str)}

    except Exception as e:
        # Ultimate fallback - stringify whatever we got
        return {"result": f"Result: {str(result)[:2000]}"}


def _format_tool_result(tool_name: str, result: Any) -> str:
    """Format tool result into readable text for display.

    Args:
        tool_name: Name of the tool that was executed
        result: The raw result from the tool

    Returns:
        Human-readable formatted string
    """
    # Handle None
    if result is None:
        return "Operación completada sin resultados."

    # Handle strings
    if isinstance(result, str):
        return result

    # Handle list results FIRST (before trying .get())
    if isinstance(result, list):
        if not result:
            return "No se encontraron resultados."
        # Try to format as table if items are dicts
        if isinstance(result[0], dict):
            headers = list(result[0].keys())[:6]  # Limit columns
            lines = ["| " + " | ".join(headers) + " |"]
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for item in result[:20]:
                values = [str(item.get(h, ""))[:25] for h in headers]
                lines.append("| " + " | ".join(values) + " |")
            return "\n".join(lines)
        return "\n".join([f"- {item}" for item in result[:20]])

    # Handle non-dict types
    if not isinstance(result, dict):
        return str(result)

    # Now we know result is a dict - handle errors with user-friendly messages
    if result.get("error"):
        details = result.get("details", [])
        error_msg = str(result['error']).lower()
        details_str = str(details[0]).lower() if details else ""

        # Google Ads specific errors
        if "customer_not_found" in error_msg or "customer_not_found" in details_str:
            return "⚠️ Cuenta de Google Ads no encontrada. Buscando en otras cuentas disponibles..."
        if "authentication" in error_msg or "oauth" in error_msg:
            return "⚠️ Problema de autenticación con Google Ads. El sistema intentará reconectarse."
        if "authorization" in error_msg:
            return "⚠️ Sin autorización para esta cuenta de Google Ads."

        # GA4 specific errors
        if "property" in error_msg and "not found" in error_msg:
            return "⚠️ Propiedad de Google Analytics no encontrada."

        # General errors
        if "quota" in error_msg or "rate limit" in error_msg:
            return "⚠️ Límite de consultas alcanzado. Reintentando en unos segundos..."
        if "permission" in error_msg or "access" in error_msg:
            return "⚠️ Sin permisos para acceder a este recurso."
        if "timeout" in error_msg:
            return "⚠️ La consulta tardó demasiado. Intentando con menos datos..."
        if "not found" in error_msg:
            return "⚠️ Recurso no encontrado."

        # Generic fallback - don't show technical details
        return "⚠️ No se pudieron obtener estos datos. Continuando con información disponible..."

    # Format Google Ads GAQL search results
    if tool_name == "google_ads_search":
        results = result.get("results", [])
        errors = result.get("errors", [])

        # Handle empty results with errors
        if not results and errors:
            return "⚠️ La consulta no retornó resultados. Usa herramientas específicas como `google_ads_list_campaigns` o `google_ads_search_terms`."

        if not results:
            return "No se encontraron datos para esta consulta."

        lines = [f"📊 **Resultados de Google Ads** ({len(results)} filas)\n"]

        # Get headers from first result, excluding internal fields
        headers = [k for k in results[0].keys() if not k.startswith("_")][:6]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for r in results[:25]:
            values = []
            for h in headers:
                val = r.get(h, "")
                # Handle nested dicts
                if isinstance(val, dict):
                    val = str(list(val.values())[0]) if val else ""
                values.append(str(val)[:30])
            lines.append("| " + " | ".join(values) + " |")

        if errors:
            lines.append(f"\n⚠️ Errores en algunas cuentas: {len(errors)}")

        return "\n".join(lines)

    # Format Google Ads campaigns with benchmark comparison
    if tool_name == "google_ads_list_campaigns" and result.get("campaigns"):
        campaigns = result["campaigns"]
        lines = [f"📊 **Campañas de Google Ads** ({len(campaigns)} encontradas)\n"]

        for c in campaigns[:10]:
            status_emoji = "✅" if c.get("status") == "ENABLED" else "⏸️"
            campaign_name = c.get('name', 'Sin nombre')
            lines.append(f"### {status_emoji} {campaign_name}")
            lines.append(f"- **Impresiones:** {c.get('impressions', 0):,}")
            lines.append(f"- **Clics:** {c.get('clicks', 0):,}")
            lines.append(f"- **Costo:** ${c.get('cost', 0):,.2f}")
            lines.append(f"- **Conversiones:** {c.get('conversions', 0)}")
            lines.append(f"- **CTR:** {c.get('ctr', 0)}%")
            lines.append(f"- **CPC Promedio:** ${c.get('avg_cpc', 0):.2f}")

            # Add benchmark comparison
            try:
                benchmarks = get_benchmarks_for_campaign(campaign_name)
                actual_ctr = float(c.get('ctr', 0))
                benchmark_ctr = benchmarks.get('avg_ctr', 3.0)
                if actual_ctr > 0:
                    ctr_diff = ((actual_ctr - benchmark_ctr) / benchmark_ctr) * 100
                    ctr_indicator = "✅" if actual_ctr >= benchmark_ctr else "⚠️"
                    sign = "+" if ctr_diff > 0 else ""
                    lines.append(f"- **vs Benchmark CTR:** {ctr_indicator} {sign}{ctr_diff:.0f}%")
            except Exception:
                pass

            lines.append("")

        return "\n".join(lines)

    # Format Google Ads search terms
    if tool_name == "google_ads_search_terms" and result.get("search_terms"):
        terms = result["search_terms"]
        lines = [f"🔍 **Términos de Búsqueda** ({len(terms)} encontrados)\n"]
        lines.append("| Término | Clics | Costo | Conv |")
        lines.append("|---------|-------|-------|------|")

        for t in terms[:20]:
            lines.append(f"| {t.get('search_term', '')[:40]} | {t.get('clicks', 0)} | ${t.get('cost', 0):.2f} | {t.get('conversions', 0)} |")

        return "\n".join(lines)

    # Format Google Ads keywords
    if tool_name == "google_ads_keyword_performance" and result.get("keywords"):
        keywords = result["keywords"]
        lines = [f"🎯 **Keywords** ({len(keywords)} encontrados)\n"]
        lines.append("| Keyword | Clics | Costo | CTR |")
        lines.append("|---------|-------|-------|-----|")

        for k in keywords[:15]:
            lines.append(f"| {k.get('keyword', '')[:30]} | {k.get('clicks', 0)} | ${k.get('cost', 0):.2f} | {k.get('ctr', 0)}% |")

        return "\n".join(lines)

    # Format GA4 reports
    if tool_name == "run_report" and result.get("rows"):
        rows = result["rows"]
        lines = [f"📈 **Reporte GA4** ({len(rows)} filas)\n"]

        if rows:
            # Get headers from first row
            headers = list(rows[0].keys())
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

            for row in rows[:20]:
                values = [str(row.get(h, ""))[:20] for h in headers]
                lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)

    # Format BigQuery results
    if tool_name == "bq_run_query":
        return result  # Already formatted as string

    if tool_name == "bq_export_google_ads":
        return result  # Already formatted as string

    # Format web search results
    if tool_name == "web_search" and result.get("results"):
        results = result["results"]
        lines = ["🌐 **Resultados de búsqueda:**\n"]

        for r in results[:5]:
            lines.append(f"- **{r.get('title', '')}**")
            lines.append(f"  {r.get('snippet', '')[:200]}")
            lines.append("")

        return "\n".join(lines)

    # Generic fallback - format as key-value pairs
    # Skip technical fields that shouldn't be shown to users
    skip_fields = ["success", "error", "query", "row_count", "errors", "mcc_customer_id",
                   "accounts_queried", "customer_id", "_customer_id"]

    lines = []
    for key, value in result.items():
        if key in skip_fields:
            continue
        if isinstance(value, (list, dict)):
            if isinstance(value, list) and len(value) > 0:
                lines.append(f"**{key}:** {len(value)} elementos")
            continue
        # Skip empty values
        if value is None or value == "" or value == 0:
            continue
        lines.append(f"**{key}:** {value}")

    return "\n".join(lines) if lines else "Consulta ejecutada correctamente."


class AgentOrchestrator:
    """Orchestrates LLM interactions with MCP tools."""

    def __init__(self) -> None:
        """Initialize the orchestrator with Gemini and tools."""
        # Initialize Vertex AI
        aiplatform.init(
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )

        # Initialize tools
        self.ga_tool = GoogleAnalyticsTool()
        self.kb_tool = KnowledgeBaseTool()
        self.ads_tool = get_google_ads_tool()  # May be None if not configured
        self.web_tool = get_web_search_tool()  # Web search tool
        self.bq_tool = get_bigquery_tool()  # BigQuery for advanced analytics

        # Initialize memory and alerts (may be None if BigQuery not available)
        self.memory = get_agent_memory()
        self.alerts = get_campaign_alerts()

        # Build Gemini tool definitions
        self.tools = self._build_tools()

        # Initialize model with TEMPERATURE 1.0 (Google recommendation for Gemini 2.0+)
        self.model = GenerativeModel(
            settings.gemini_model,
            tools=self.tools,
            generation_config=GenerationConfig(
                temperature=1.0,  # Recommended by Google for Gemini 2.0+
                top_p=0.95,
                max_output_tokens=8192,
            ),
        )

        # System instruction with Chain-of-Thought prompting
        self.system_instruction = self._build_system_instruction()

        # Count tools safely
        try:
            tools_count = len(self.tools[0]._raw_tool.function_declarations) if self.tools else 0
        except (AttributeError, IndexError):
            tools_count = len(self.tools) if self.tools else 0

        logger.info(
            "AgentOrchestrator initialized",
            model=settings.gemini_model,
            temperature=1.0,
            tools_count=tools_count,
            memory_enabled=self.memory is not None,
            alerts_enabled=self.alerts is not None,
        )

    def _build_system_instruction(self) -> str:
        """Build the system instruction with CoT prompting."""
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")

        # Get industry benchmarks for context
        benchmarks_context = "\n".join([
            f"- **{industry.replace('_', ' ').title()}**: CTR {data['avg_ctr']}%, CPC ${data['avg_cpc']}, Conv Rate {data['avg_conversion_rate']}%"
            for industry, data in list(INDUSTRY_BENCHMARKS.items())[:3]
        ])

        return f"""# ROL: CONSULTOR ESTRATÉGICO DE MARKETING DIGITAL

Eres un consultor de élite que combina:
- **Visión de negocios** nivel Harvard MBA (ROI, estrategia, decisiones basadas en datos)
- **Expertise técnico** nivel MIT (análisis de datos, optimización digital, growth hacking)

Tu cliente es **SCRAM**, empresa de tecnología y seguridad electrónica.

---
## REGLA #1: IDIOMA (CRÍTICO)

**SIEMPRE responde en el MISMO IDIOMA que el usuario.**
- Usuario escribe en español → Respuesta 100% en español
- Usuario escribe en inglés → Respuesta 100% en inglés
- NUNCA mezcles idiomas
- Traduce TODOS los datos técnicos al idioma del usuario

---
## REGLA #2: CERO PENSAMIENTO VISIBLE (MÁXIMA PRIORIDAD)

🚫 **LISTA NEGRA DE FRASES - NUNCA ESCRIBAS ESTO:**
- "Pensamiento", "Thought", "Thinking", "Análisis interno"
- "Voy a", "Primero voy a", "Necesito", "Déjame"
- "RECUERDA", "PROCEDE", "IMPORTANTE:"
- "Let me", "I need to", "I will"
- Cualquier narración de tus acciones

✅ **TU PRIMERA PALABRA DEBE SER:**
- Un emoji de sección (📊, 🔍, ✅)
- O directamente la respuesta ("Sí", "No", "El problema es...")

**VIOLACIÓN = FALLA CRÍTICA DEL SISTEMA**

---
## REGLA #3: ADAPTAR LONGITUD A LA PREGUNTA

**Pregunta SIMPLE** (sí/no, número, comparación):
→ Respuesta de 2-4 oraciones máximo
→ Ejemplo: "¿Me conviene invertir más?" → "No. Estás perdiendo $X por cada $Y invertido. Primero arregla la landing page."

**Pregunta COMPLEJA** (análisis, plan, diagnóstico):
→ Usar formato completo con secciones
→ RESUMEN → ANÁLISIS → INSIGHTS → RECOMENDACIONES

---
## FRAMEWORK DE ANÁLISIS (Solo para preguntas complejas)

**📊 RESUMEN EJECUTIVO** - 1-2 oraciones con el hallazgo principal

**🔍 ANÁLISIS DE DATOS**
[Datos relevantes en tabla o bullets - NO JSON crudo]

**💡 INSIGHTS CLAVE**
[2-4 insights con el "¿por qué?" detrás de los números]

**✅ RECOMENDACIONES**
[Acciones específicas ordenadas por impacto]

---
## BENCHMARKS DE INDUSTRIA (Referencia)

{benchmarks_context}

Usa estos benchmarks para contextualizar el rendimiento del cliente.

---
## ECOSISTEMA SCRAM

**Fecha actual:** {current_date}

**Propiedades GA4:**
- scram2k.com (Principal): 508206486
- Landing Conectividad: 512088907
- Landing Seguridad: 509271243

**Mapeo automático:**
- "seguridad/cámaras/CCTV/alarmas" → GA4: 509271243
- "conectividad/internet/red/wifi" → GA4: 512088907

---
## HERRAMIENTAS DISPONIBLES

**🤖 HERRAMIENTAS AUTÓNOMAS (PREFERIR ESTAS):**
- `bq_discover_data` - Descubre AUTOMÁTICAMENTE todos los datos disponibles
- `bq_auto_analyze` - Análisis AUTÓNOMO completo (Ads + Prospectos + Cross-data)
- `bq_smart_query` - Consultas inteligentes en lenguaje natural

**Google Ads (USAR ESTAS, no GAQL):**
- `google_ads_list_campaigns` - Lista todas las campañas con métricas
- `google_ads_search_terms` - Términos de búsqueda reales (requiere campaign_id + customer_id)
- `google_ads_keyword_performance` - Rendimiento de keywords
- `google_ads_campaign_performance` - Métricas detalladas de una campaña
- `google_ads_device_performance` - Rendimiento por dispositivo

**Google Analytics (GA4):**
- `run_report` - Reportes personalizados con dimensiones y métricas

**BigQuery (Avanzado):**
- `bq_list_datasets` - Lista datasets disponibles
- `bq_list_tables` - Lista tablas en un dataset
- `bq_get_table_schema` - Obtiene el esquema de una tabla
- `bq_run_query` - Ejecutar consultas SQL personalizadas
- `bq_export_google_ads` - Exportar datos de Google Ads a BigQuery

**Otros:**
- `search_knowledge_base` - Documentos internos SCRAM
- `web_search` - Búsqueda en internet para benchmarks

**REGLAS CRÍTICAS DE HERRAMIENTAS:**
1. NUNCA uses `google_ads_search` con GAQL - las queries fallan. Usa las herramientas específicas.
2. Ejecuta herramientas SIN pedir permiso
3. NUNCA pidas IDs al usuario - obtén los IDs llamando primero a `google_ads_list_campaigns`
4. Siempre usa `google_ads_list_campaigns` PRIMERO para obtener campaign_id y customer_id
5. PUEDES encadenar múltiples herramientas para análisis profundo (hasta 10 llamadas)
6. **COMPORTAMIENTO AUTÓNOMO:** Para preguntas complejas o análisis cruzados, usa `bq_auto_analyze` o `bq_smart_query` que automáticamente exploran y cruzan datos
7. **EXPLORACIÓN PROACTIVA:** Si no sabes qué datos existen, usa `bq_discover_data` para explorar automáticamente

---
## EJEMPLO DE RESPUESTA IDEAL

**Pregunta:** "¿Por qué tenemos cero conversiones en la campaña de Seguridad?"

**📊 RESUMEN EJECUTIVO**
La campaña de Seguridad Electrónica ha generado 1,457 clics con una inversión de $1,603, pero no ha registrado conversiones. El problema principal es la combinación de tráfico móvil sin landing optimizada.

**🔍 ANÁLISIS DE DATOS**
| Métrica | Valor | vs Benchmark |
|---------|-------|--------------|
| CTR | 3.02% | ✅ +6% |
| CPC | $1.10 | ✅ -41% |
| Conv. Rate | 0% | ⚠️ -100% |

| Dispositivo | Clics | % Total |
|-------------|-------|---------|
| Móvil | 1,412 | 97% |
| Desktop | 35 | 2% |
| Tablet | 10 | 1% |

**💡 INSIGHTS CLAVE**
1. **97% del tráfico es móvil** - Si la landing no está optimizada para móvil, perdemos casi todo el tráfico
2. **El CTR es excelente** - Los anuncios son relevantes, el problema está post-clic
3. **Keywords de intención local** - "cámaras CDMX", "instalación cámaras" sugieren urgencia de compra

**✅ RECOMENDACIONES**
1. **URGENTE:** Auditar landing page en móvil - velocidad, formulario, CTA
2. **Verificar tracking** - Confirmar que el pixel de conversión está disparando
3. **Agregar extensiones de ubicación** - Capitalizar intención local
4. **Implementar click-to-call** - Para el 97% de tráfico móvil

---
## REGLAS DE ORO

1. **Sé estratégico, no técnico** - El usuario quiere insights, no datos crudos
2. **Conecta los puntos** - Cruza datos de diferentes fuentes
3. **Prioriza el impacto** - Enfócate en lo que mueve la aguja del negocio
4. **Sé directo** - Menos palabras, más valor
5. **Siempre recomienda** - Nunca termines sin una acción clara
6. **Compara con benchmarks** - Contextualiza cada métrica
7. **Identifica la causa raíz** - No solo síntomas"""

    def _build_tools(self) -> list[Tool]:
        """Build Gemini tool definitions from MCP tools.

        Returns:
            List of Gemini Tool objects
        """
        function_declarations = []

        # Google Analytics tools
        ga_functions = self.ga_tool.get_function_declarations()
        function_declarations.extend(ga_functions)

        # Knowledge Base tools
        kb_functions = self.kb_tool.get_function_declarations()
        function_declarations.extend(kb_functions)

        # Google Ads tools (if configured)
        if self.ads_tool:
            ads_functions = self.ads_tool.get_function_declarations()
            function_declarations.extend(ads_functions)

        # Web Search tool (always available)
        if self.web_tool:
            web_functions = self.web_tool.get_function_declarations()
            function_declarations.extend(web_functions)
            logger.info("Web Search tool enabled")

        # BigQuery tool for advanced analytics
        if self.bq_tool:
            bq_functions = self.bq_tool.get_function_declarations()
            function_declarations.extend(bq_functions)
            logger.info("BigQuery tool enabled")

        return [Tool(function_declarations=function_declarations)]

    async def _execute_tool_with_retry(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        max_retries: int = MAX_RETRIES
    ) -> dict[str, Any]:
        """Execute a tool call with retry logic.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool
            max_retries: Maximum retry attempts

        Returns:
            Tool execution result
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                result = await self._execute_tool(tool_name, tool_args)

                # Check if result indicates an error that might be transient
                if isinstance(result, dict) and result.get("error"):
                    error_msg = result["error"].lower()
                    # Retry on transient errors
                    if any(x in error_msg for x in ["timeout", "rate limit", "temporarily"]):
                        if attempt < max_retries - 1:
                            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                            continue

                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    "Tool execution attempt failed",
                    tool_name=tool_name,
                    attempt=attempt + 1,
                    error=str(e)
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))

        logger.error("Tool execution failed after retries", tool_name=tool_name, error=str(last_error))
        return {"error": f"Error después de {max_retries} intentos: {str(last_error)}"}

    async def _execute_tool(self, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call and return the result.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool

        Returns:
            Tool execution result
        """
        logger.info("Executing tool", tool_name=tool_name, args=tool_args)

        try:
            # Route to appropriate tool
            if tool_name.startswith("ga_") or tool_name in [
                "run_report",
                "run_realtime_report",
                "get_property_details",
                "get_account_summaries",
            ]:
                result = await self.ga_tool.execute(tool_name, tool_args)
            elif tool_name.startswith("kb_") or tool_name in [
                "search_knowledge_base",
                "list_documents",
            ]:
                result = await self.kb_tool.execute(tool_name, tool_args)
            elif tool_name.startswith("google_ads_") and self.ads_tool:
                result = await self.ads_tool.execute(tool_name, tool_args)
            elif tool_name == "web_search" and self.web_tool:
                result = await self.web_tool.execute(tool_name, tool_args)
            elif tool_name.startswith("bq_") and self.bq_tool:
                result = await self.bq_tool.execute(tool_name, tool_args)
            else:
                result = {"error": f"Herramienta desconocida: {tool_name}"}

            logger.info("Tool executed", tool_name=tool_name, success=True)
            return result

        except Exception as e:
            logger.error("Tool execution failed", tool_name=tool_name, error=str(e))
            return {"error": str(e)}

    async def _get_memory_context(self, user_id: str = "default") -> str:
        """Get relevant context from memory system.

        Args:
            user_id: User identifier

        Returns:
            Memory context string or empty
        """
        if not self.memory:
            return ""

        try:
            return await self.memory.get_conversation_summary(user_id)
        except Exception as e:
            logger.warning("Failed to get memory context", error=str(e))
            return ""

    async def _check_proactive_alerts(self) -> str:
        """Check for any proactive alerts to include.

        Returns:
            Alerts summary or empty string
        """
        if not self.alerts:
            return ""

        try:
            alerts = await self.alerts.check_all_alerts()
            critical_alerts = [a for a in alerts if a.get("severity") == "critical"]

            if critical_alerts:
                return f"\n\n⚠️ **ALERTAS CRÍTICAS DETECTADAS:**\n{format_alerts_for_display(critical_alerts[:3])}"

            return ""
        except Exception as e:
            logger.warning("Failed to check alerts", error=str(e))
            return ""

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        use_rag: bool = True,
        use_analytics: bool = True,
        session_id: str = "default",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream response from Gemini with tool support.

        Args:
            messages: Conversation history
            use_rag: Whether to include RAG context
            use_analytics: Whether to enable Analytics tools
            session_id: Session identifier for memory

        Yields:
            Stream events (text, tool_call, error, done)
        """
        try:
            # Build conversation contents
            contents: list[Content] = []

            # Add system instruction as first user message
            contents.append(
                Content(
                    role="user",
                    parts=[Part.from_text(self.system_instruction)],
                )
            )
            contents.append(
                Content(
                    role="model",
                    parts=[Part.from_text("Entendido. Estoy listo para ayudarte con análisis estratégico de marketing. Responderé siempre en tu idioma, usando datos reales y dando recomendaciones accionables.")],
                )
            )

            # Get RAG context for the last user message
            rag_context = ""
            if use_rag and messages:
                last_user_msg = next(
                    (m["content"] for m in reversed(messages) if m["role"] == "user"),
                    None,
                )
                if last_user_msg:
                    async with async_session_maker() as db:
                        rag_context = await get_context_for_query(db, last_user_msg)

            # Get memory context
            memory_context = await self._get_memory_context()

            # Add conversation history
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"]

                # Add RAG and memory context to the last user message
                if role == "user" and msg == messages[-1]:
                    context_parts = []
                    if memory_context:
                        context_parts.append(f"**Contexto de sesiones anteriores:**\n{memory_context}")
                    if rag_context:
                        context_parts.append(f"**Documentos relevantes:**\n{rag_context}")

                    if context_parts:
                        content = "\n\n".join(context_parts) + f"\n\n**Pregunta del usuario:** {content}"

                contents.append(
                    Content(role=role, parts=[Part.from_text(content)])
                )

            # Start streaming
            logger.info("Starting Gemini stream", session_id=session_id)
            response = self.model.generate_content(
                contents,
                stream=True,
            )

            chunk_count = 0
            total_tool_calls = 0

            # Process response chunks
            for chunk in response:
                chunk_count += 1
                # Check for function calls
                try:
                    has_parts = chunk.candidates and chunk.candidates[0].content.parts
                except Exception as chunk_err:
                    logger.warning("Error accessing chunk content", error=str(chunk_err), chunk_num=chunk_count)
                    continue
                if has_parts:
                    for part in chunk.candidates[0].content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            tool_name = fc.name
                            # Safely convert args - handle potential proto/dict conversion issues
                            try:
                                tool_args = dict(fc.args) if fc.args else {}
                            except (TypeError, AttributeError) as arg_err:
                                logger.warning("Failed to convert args", error=str(arg_err), args_type=type(fc.args).__name__)
                                tool_args = {}

                            # Emit tool call event
                            yield {
                                "type": "tool_call",
                                "data": {
                                    "tool_name": tool_name,
                                    "tool_input": tool_args,
                                    "status": "running",
                                },
                            }

                            # Execute tool with retry logic
                            result = await self._execute_tool_with_retry(tool_name, tool_args)
                            total_tool_calls += 1

                            # Emit tool result
                            yield {
                                "type": "tool_call",
                                "data": {
                                    "tool_name": tool_name,
                                    "tool_input": tool_args,
                                    "status": "completed",
                                    "result": result,
                                },
                            }

                            # Continue conversation with tool result
                            contents.append(
                                Content(
                                    role="model",
                                    parts=[part],
                                )
                            )

                            # Add tool result with synthesis instruction
                            synthesis_instruction = """RESPONDE AHORA. Tienes los datos.

🚫 PROHIBIDO: "Pensamiento", "Voy a", "RECUERDA", tablas crudas, JSON
✅ TU PRIMERA PALABRA: emoji (📊/🔍/✅) o respuesta directa

ADAPTA LA LONGITUD:
- Pregunta simple (sí/no, cuánto, cuál) → 2-4 oraciones máximo
- Pregunta compleja (por qué, analiza, plan) → formato completo:
  📊 RESUMEN (1 oración) → 🔍 ANÁLISIS → 💡 INSIGHTS → ✅ RECOMENDACIONES

Si faltan datos, llama otra herramienta. Si ya tienes suficiente, RESPONDE."""

                            # Add function response as separate Content
                            # (combining with text can cause SDK issues)
                            contents.append(
                                Content(
                                    role="user",
                                    parts=[
                                        Part.from_function_response(
                                            name=tool_name,
                                            response=_serialize_for_function_response(result),
                                        ),
                                    ],
                                )
                            )
                            # Add synthesis instruction as separate user message
                            contents.append(
                                Content(
                                    role="user",
                                    parts=[Part.from_text(synthesis_instruction)],
                                )
                            )

                            # Get follow-up response - handle chained tool calls
                            max_tool_calls = 10  # Allow up to 10 chained calls
                            tool_call_count = 1

                            while tool_call_count < max_tool_calls:
                                try:
                                    logger.info("Generating follow-up response", iteration=tool_call_count, total=total_tool_calls)
                                    follow_up = self.model.generate_content(
                                        contents,
                                        stream=True,
                                    )

                                    has_function_call = False
                                    for follow_chunk in follow_up:
                                        if follow_chunk.candidates and follow_chunk.candidates[0].content.parts:
                                            for follow_part in follow_chunk.candidates[0].content.parts:
                                                if hasattr(follow_part, "function_call") and follow_part.function_call:
                                                    # Another tool call - execute it
                                                    has_function_call = True
                                                    fc = follow_part.function_call
                                                    next_tool_name = fc.name
                                                    next_tool_args = dict(fc.args) if fc.args else {}

                                                    yield {
                                                        "type": "tool_call",
                                                        "data": {
                                                            "tool_name": next_tool_name,
                                                            "tool_input": next_tool_args,
                                                            "status": "running",
                                                        },
                                                    }

                                                    next_result = await self._execute_tool_with_retry(
                                                        next_tool_name, next_tool_args
                                                    )
                                                    total_tool_calls += 1

                                                    yield {
                                                        "type": "tool_call",
                                                        "data": {
                                                            "tool_name": next_tool_name,
                                                            "tool_input": next_tool_args,
                                                            "status": "completed",
                                                            "result": next_result,
                                                        },
                                                    }

                                                    # Add to conversation with synthesis reminder
                                                    contents.append(
                                                        Content(role="model", parts=[follow_part])
                                                    )

                                                    # Add function response as separate Content
                                                    contents.append(
                                                        Content(
                                                            role="user",
                                                            parts=[
                                                                Part.from_function_response(
                                                                    name=next_tool_name,
                                                                    response=_serialize_for_function_response(next_result),
                                                                ),
                                                            ],
                                                        )
                                                    )
                                                    # Add synthesis reminder as separate user message
                                                    synthesis_reminder = """Datos obtenidos. RESPONDE AHORA o llama otra herramienta.
🚫 Sin "Pensamiento", "Voy a", tablas crudas
✅ Adapta longitud: simple=2-4 oraciones, complejo=formato completo"""
                                                    contents.append(
                                                        Content(
                                                            role="user",
                                                            parts=[Part.from_text(synthesis_reminder)],
                                                        )
                                                    )
                                                    tool_call_count += 1
                                                    break  # Break to generate next follow-up

                                                elif hasattr(follow_part, "text") and follow_part.text:
                                                    yield {"type": "text", "content": follow_part.text}

                                        # Also check direct text access for streaming
                                        elif hasattr(follow_chunk, "text") and follow_chunk.text:
                                            yield {"type": "text", "content": follow_chunk.text}

                                    if not has_function_call:
                                        logger.info("Follow-up completed", total_tool_calls=total_tool_calls)
                                        break

                                except Exception as follow_up_error:
                                    logger.error(
                                        "Follow-up generation failed",
                                        error=str(follow_up_error),
                                        error_type=type(follow_up_error).__name__,
                                        tool_name=tool_name,
                                        tool_call_count=tool_call_count,
                                        exc_info=True
                                    )
                                    # Use formatted result with template
                                    formatted_result = _format_tool_result(tool_name, result)
                                    yield {
                                        "type": "text",
                                        "content": formatted_result
                                    }
                                    break

                        elif hasattr(part, "text") and part.text:
                            yield {"type": "text", "content": part.text}
                else:
                    # Log when chunk has no usable content
                    if chunk_count <= 3:
                        logger.debug("Chunk has no candidates or parts", chunk_num=chunk_count)

            logger.info("Gemini stream completed", total_chunks=chunk_count, total_tool_calls=total_tool_calls)

            # Store conversation summary in memory if available
            if self.memory and messages:
                try:
                    last_msg = messages[-1].get("content", "")[:200]
                    await self.memory.store_context(
                        session_id=session_id,
                        context_type="summary",
                        context_key=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M')}",
                        content={"summary": last_msg, "tool_calls": total_tool_calls},
                        ttl_hours=168  # 1 week
                    )
                except Exception as mem_error:
                    logger.warning("Failed to store memory", error=str(mem_error))

            # Emit done event
            yield {"type": "done"}

        except Exception as e:
            logger.error("Stream response error", error=str(e), exc_info=True)
            yield {"type": "error", "message": str(e)}
            yield {"type": "done"}

    async def get_daily_digest(self) -> str:
        """Generate a daily digest with alerts and insights.

        Returns:
            Formatted daily digest
        """
        if not self.alerts:
            return "Sistema de alertas no disponible."

        try:
            return await self.alerts.get_daily_digest()
        except Exception as e:
            logger.error("Failed to generate daily digest", error=str(e))
            return f"Error generando resumen: {str(e)}"
