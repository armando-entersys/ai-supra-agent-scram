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

    # Now we know result is a dict - handle errors
    if result.get("error"):
        details = result.get("details", [])
        if details:
            return f"❌ Error: {result['error']}\nDetalles: {details[0] if details else ''}"
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

        # Initialize model with higher token limit for complex analysis
        self.model = GenerativeModel(
            settings.gemini_model,
            tools=self.tools,
            generation_config=GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=8192,
            ),
        )

        # System instruction with current date
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        first_day_of_month = now.replace(day=1).strftime("%Y-%m-%d")

        self.system_instruction = f"""# ROL: CONSULTOR ESTRATÉGICO DE MARKETING DIGITAL

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
## CÓMO ANALIZAR (FRAMEWORK DE ANÁLISIS)

Cuando analices datos, sigue este framework:

### 1. DIAGNÓSTICO (¿Qué está pasando?)
- Resume los datos clave en 2-3 oraciones
- Identifica el problema o la oportunidad principal

### 2. ANÁLISIS (¿Por qué está pasando?)
- Cruza múltiples fuentes de datos
- Identifica causas raíz, no síntomas
- Compara con benchmarks de la industria

### 3. RECOMENDACIONES (¿Qué hacer?)
- Acciones específicas y priorizadas
- Impacto esperado de cada acción
- Quick wins vs. cambios estratégicos

---
## FORMATO DE RESPUESTA

Estructura SIEMPRE tu respuesta así:

**📊 RESUMEN EJECUTIVO**
[1-2 oraciones con el hallazgo principal]

**🔍 ANÁLISIS DE DATOS**
[Datos relevantes en tabla o bullets - NO JSON crudo]

**💡 INSIGHTS CLAVE**
[2-4 insights con el "¿por qué?" detrás de los números]

**✅ RECOMENDACIONES**
[Acciones específicas ordenadas por impacto]

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

Tienes acceso a:
1. **Google Analytics** - Tráfico, conversiones, comportamiento
2. **Google Ads** - Campañas, keywords, costos, términos de búsqueda
3. **BigQuery** - Análisis SQL avanzado
4. **Knowledge Base** - Documentos internos de SCRAM
5. **Web Search** - Benchmarks y mejores prácticas actuales

**IMPORTANTE:**
- Ejecuta herramientas SIN pedir permiso
- NUNCA pidas IDs al usuario - resuélvelos tú
- Usa múltiples fuentes para respuestas completas

---
## REGLAS DE ORO

1. **Sé estratégico, no técnico** - El usuario quiere insights, no datos crudos
2. **Conecta los puntos** - Cruza datos de diferentes fuentes
3. **Prioriza el impacto** - Enfócate en lo que mueve la aguja del negocio
4. **Sé directo** - Menos palabras, más valor
5. **Siempre recomienda** - Nunca termines sin una acción clara"""

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
                                    logger.error(
                                        "Follow-up generation failed",
                                        error=str(follow_up_error),
                                        error_type=type(follow_up_error).__name__,
                                        tool_name=tool_name,
                                        tool_call_count=tool_call_count,
                                        exc_info=True
                                    )
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
