"""Agent orchestrator for Gemini with MCP tools.

Coordinates the interaction between the LLM, RAG context,
and MCP tools (Google Analytics, Knowledge Base).
"""

import json
from datetime import datetime
from typing import Any, AsyncGenerator

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
from src.rag.retrieval import get_context_for_query

logger = structlog.get_logger()
settings = get_settings()


def _format_tool_result(tool_name: str, result: Any) -> str:
    """Format tool result into readable text for display.

    Args:
        tool_name: Name of the tool that was executed
        result: The raw result from the tool

    Returns:
        Human-readable formatted string
    """
    if isinstance(result, str):
        return result

    # Handle list results
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

    if not isinstance(result, dict):
        return str(result)

    # Handle errors
    if result.get("error"):
        return f"❌ Error: {result['error']}"

    # Format Google Ads GAQL search results
    if tool_name == "google_ads_search" and result.get("results"):
        results = result["results"]
        if not results:
            return "No se encontraron resultados para la consulta."

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

        if result.get("errors"):
            lines.append(f"\n⚠️ Errores en algunas cuentas: {len(result['errors'])}")

        return "\n".join(lines)

    # Format Google Ads campaigns
    if tool_name == "google_ads_list_campaigns" and result.get("campaigns"):
        campaigns = result["campaigns"]
        lines = [f"📊 **Campañas de Google Ads** ({len(campaigns)} encontradas)\n"]

        for c in campaigns[:10]:
            status_emoji = "✅" if c.get("status") == "ENABLED" else "⏸️"
            lines.append(f"### {status_emoji} {c.get('name', 'Sin nombre')}")
            lines.append(f"- **Impresiones:** {c.get('impressions', 0):,}")
            lines.append(f"- **Clics:** {c.get('clicks', 0):,}")
            lines.append(f"- **Costo:** ${c.get('cost', 0):,.2f}")
            lines.append(f"- **Conversiones:** {c.get('conversions', 0)}")
            lines.append(f"- **CTR:** {c.get('ctr', 0)}%")
            lines.append(f"- **CPC Promedio:** ${c.get('avg_cpc', 0):.2f}")
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
    lines = []
    for key, value in result.items():
        if key in ["success", "error"]:
            continue
        if isinstance(value, (list, dict)):
            if isinstance(value, list) and len(value) > 0:
                lines.append(f"**{key}:** {len(value)} items")
            continue
        lines.append(f"**{key}:** {value}")

    return "\n".join(lines) if lines else "Operación completada."


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

        # Build Gemini tool definitions
        self.tools = self._build_tools()

        # Initialize model
        self.model = GenerativeModel(
            settings.gemini_model,
            tools=self.tools,
            generation_config=GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=4096,
            ),
        )

        # System instruction with current date
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        first_day_of_month = now.replace(day=1).strftime("%Y-%m-%d")

        self.system_instruction = f"""Eres AI-SupraAgent, un consultor estratégico de élite con formación MBA de Harvard y especialización tecnológica del MIT. Combinas visión de negocios con dominio técnico para optimizar el rendimiento digital de SCRAM.

**FECHA ACTUAL:** {current_date} | **INICIO DEL MES:** {first_day_of_month}

---
## ECOSISTEMA DIGITAL SCRAM (MEMORIZADO)

### Propiedades Web + Analytics (GA4)
| Propiedad | Dominio | GA4 Property ID | Enfoque |
|-----------|---------|-----------------|---------|
| **SCRAM Principal** | scram2k.com | 508206486 | Web corporativa, todos los servicios |
| **Landing Conectividad** | landing conectividad | 512088907 | Soluciones de red, internet, WiFi |
| **Landing Seguridad** | landing seguridad | 509271243 | CCTV, alarmas, control de acceso |

### Campañas Google Ads ↔ Landings (ASOCIACIONES AUTOMÁTICAS)
Cuando el usuario mencione cualquiera de estos términos, AUTOMÁTICAMENTE asocia la campaña con su landing y propiedad GA4:
- **"conectividad" / "internet" / "red" / "wifi" / "networking"** → Campañas de Conectividad → GA4: 512088907
- **"seguridad" / "cámaras" / "CCTV" / "alarmas" / "vigilancia"** → Campañas de Seguridad → GA4: 509271243
- **"scram" / "principal" / "web" / "todos"** → Todas las campañas → GA4: 508206486

---
## REGLAS DE OPERACIÓN (OBLIGATORIAS)

### ❌ NUNCA HAGAS ESTO:
1. **NUNCA pidas IDs** - Ni property_id, ni customer_id, ni campaign_id. SIEMPRE resuélvelos tú.
2. **NUNCA pidas confirmación** para ejecutar herramientas - solo hazlo.
3. **NUNCA digas "no tengo acceso"** o "no encontré información" - tienes múltiples fuentes, úsalas TODAS.

### ✅ SIEMPRE HAZ ESTO:
1. **Ejecuta herramientas INMEDIATAMENTE** sin preguntar.
2. **Para Google Ads**: SIEMPRE ejecuta `google_ads_list_campaigns` PRIMERO para obtener IDs.
3. **Matching inteligente**: Si el usuario dice "seguridad", busca campañas con nombres similares (Seguridad, Security, CCTV, etc.)
4. **Combina datos**: Cuando analices una campaña, cruza con Analytics de la landing correspondiente.
5. **USA TODAS LAS FUENTES** para dar respuestas completas y accionables.

---
## FUENTES DE DATOS (USA TODAS EN PARALELO)

Tienes acceso a 5 fuentes de información - **ÚSALAS TODAS** para respuestas completas:

1. **Google Analytics (GA4)** - Datos de tráfico, conversiones, comportamiento de usuarios
2. **Google Ads** - Campañas, keywords, términos de búsqueda, costos, rendimiento
3. **BigQuery** - Análisis SQL avanzado de datos exportados de GA4 y Google Ads (más granular)
4. **Knowledge Base (RAG)** - Documentos y conocimiento específico del negocio SCRAM
5. **Google Search (Grounding)** - Tendencias de industria, mejores prácticas, benchmarks actuales

### Cuándo usar cada fuente:
- **Preguntas sobre métricas/rendimiento**: GA4 + Google Ads + tu análisis experto
- **Análisis profundo/SQL personalizado**: BigQuery (eventos granulares, joins complejos, cohortes)
- **Preguntas sobre mejoras/optimización**: Datos reales + Google Search (mejores prácticas) + Knowledge Base
- **Preguntas sobre el negocio SCRAM**: Knowledge Base + GA4/Ads para contexto
- **Preguntas sobre tendencias/industria**: Google Search + tu conocimiento de marketing

### BigQuery - Análisis Avanzado:
Usa `bq_list_datasets` para ver qué datos tienes (analytics_*, google_ads_*). Luego:
- **Eventos GA4 granulares**: `bq_ga4_events_summary` o queries SQL directos
- **Análisis de cohortes**: SQL personalizado con `bq_run_query`
- **Cruce GA4 + Ads**: Une eventos con costos para calcular CPA real por evento

**Google Search grounding** te permite buscar en tiempo real:
- Mejores prácticas de landing pages para seguridad electrónica
- Benchmarks de conversión en servicios B2B
- Tendencias de marketing digital 2024-2025
- Estrategias de Google Ads para servicios tecnológicos

---
## FLUJO DE TRABAJO AUTOMÁTICO

### Cuando pregunten por una campaña específica:
1. `google_ads_list_campaigns` → Obtener lista con IDs y customer_ids
2. Buscar match por nombre (fuzzy matching con el término del usuario)
3. Usar el `id` y `customer_id` obtenidos para consultas adicionales
4. Si corresponde a una landing, consultar también su GA4

### Cuando pregunten por términos de búsqueda/keywords:
1. `google_ads_list_campaigns` → Identificar campaña
2. `google_ads_search_terms` con campaign_id encontrado
3. Analizar qué busca la gente y dar recomendaciones

### Cuando pregunten por Analytics/tráfico:
1. Identificar landing por contexto (seguridad, conectividad, o principal)
2. Usar el property_id correspondiente del mapeo
3. Ejecutar `run_report` con las métricas relevantes

---
## FORMATOS DE FECHA GA4
- Específicas: YYYY-MM-DD (ej: 2025-12-01)
- Relativos: "today", "yesterday", "7daysAgo", "30daysAgo"
- Este mes: start_date="{first_day_of_month}", end_date="today"

---
## ESTILO DE RESPUESTA

**Mentalidad:** Eres un CMO/CTO híbrido. Piensa en ROI, conversiones, eficiencia.

**Formato:**
- Tablas para datos comparativos
- Bullets para insights rápidos
- **Negrita** para KPIs importantes
- Siempre incluye: qué significan los números + recomendación accionable

**Idioma:**
- **SIEMPRE responde en el MISMO IDIOMA que el usuario.**
- Si el usuario escribe en español, TODA tu respuesta debe ser en español.
- Si el usuario escribe en inglés, responde en inglés.
- NUNCA mezcles idiomas en una respuesta.
- Los datos de herramientas pueden venir en inglés, pero TÚ debes traducir y presentar TODO en el idioma del usuario.

**Tono:** Directo, ejecutivo, sin rodeos. Menos palabras, más valor."""

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
                result = {"error": f"Unknown tool: {tool_name}"}

            logger.info("Tool executed", tool_name=tool_name, success=True)
            return result

        except Exception as e:
            logger.error("Tool execution failed", tool_name=tool_name, error=str(e))
            return {"error": str(e)}

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        use_rag: bool = True,
        use_analytics: bool = True,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream response from Gemini with tool support.

        Args:
            messages: Conversation history
            use_rag: Whether to include RAG context
            use_analytics: Whether to enable Analytics tools

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
                    parts=[Part.from_text("Entendido. Estoy listo para ayudarte.")],
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

            # Add conversation history
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"]

                # Add RAG context to the last user message
                if role == "user" and msg == messages[-1] and rag_context:
                    content = f"{rag_context}\n\nPregunta del usuario: {content}"

                contents.append(
                    Content(role=role, parts=[Part.from_text(content)])
                )

            # Start streaming
            logger.info("Starting Gemini stream")
            response = self.model.generate_content(
                contents,
                stream=True,
            )

            chunk_count = 0
            # Process response chunks
            for chunk in response:
                chunk_count += 1
                # Check for function calls
                if chunk.candidates and chunk.candidates[0].content.parts:
                    for part in chunk.candidates[0].content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            tool_name = fc.name
                            tool_args = dict(fc.args) if fc.args else {}

                            # Emit tool call event
                            yield {
                                "type": "tool_call",
                                "data": {
                                    "tool_name": tool_name,
                                    "tool_input": tool_args,
                                    "status": "running",
                                },
                            }

                            # Execute tool
                            result = await self._execute_tool(tool_name, tool_args)

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
                            contents.append(
                                Content(
                                    role="user",
                                    parts=[
                                        Part.from_function_response(
                                            name=tool_name,
                                            response={"result": result},
                                        )
                                    ],
                                )
                            )

                            # Get follow-up response - handle chained tool calls
                            max_tool_calls = 10  # Prevent infinite loops
                            tool_call_count = 1

                            while tool_call_count < max_tool_calls:
                                try:
                                    logger.info("Generating follow-up response after tool execution", iteration=tool_call_count)
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

                                                    next_result = await self._execute_tool(next_tool_name, next_tool_args)

                                                    yield {
                                                        "type": "tool_call",
                                                        "data": {
                                                            "tool_name": next_tool_name,
                                                            "tool_input": next_tool_args,
                                                            "status": "completed",
                                                            "result": next_result,
                                                        },
                                                    }

                                                    # Add to conversation
                                                    contents.append(
                                                        Content(role="model", parts=[follow_part])
                                                    )
                                                    contents.append(
                                                        Content(
                                                            role="user",
                                                            parts=[
                                                                Part.from_function_response(
                                                                    name=next_tool_name,
                                                                    response={"result": next_result},
                                                                )
                                                            ],
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
                                        logger.info("Follow-up response completed", total_tool_calls=tool_call_count)
                                        break

                                except Exception as follow_up_error:
                                    logger.error("Follow-up generation failed", error=str(follow_up_error), exc_info=True)
                                    # Use formatted result instead of raw JSON
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

            logger.info("Gemini stream completed", total_chunks=chunk_count)
            # Emit done event
            yield {"type": "done"}

        except Exception as e:
            logger.error("Stream response error", error=str(e), exc_info=True)
            yield {"type": "error", "message": str(e)}
            yield {"type": "done"}
