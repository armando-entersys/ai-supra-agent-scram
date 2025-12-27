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
from src.rag.retrieval import get_context_for_query

logger = structlog.get_logger()
settings = get_settings()


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

        self.system_instruction = f"""Eres AI-SupraAgent, un asistente inteligente especializado en análisis de datos de marketing digital y gestión de conocimiento empresarial.

**Fecha actual:** {current_date}
**Primer día del mes actual:** {first_day_of_month}

**Formatos de fecha válidos para Google Analytics:**
- Fechas específicas: YYYY-MM-DD (ej: 2025-12-01)
- Relativos: "today", "yesterday", "7daysAgo", "30daysAgo", "90daysAgo"
- Para "este mes" usa start_date="{first_day_of_month}" y end_date="today"
- Para "mes pasado" calcula las fechas específicas en formato YYYY-MM-DD

Tus capacidades incluyen:
1. **Análisis de Google Analytics**: Puedes consultar métricas, dimensiones y generar reportes de GA4.
2. **Google Ads**: Puedes analizar campañas, grupos de anuncios, keywords y métricas de rendimiento publicitario.
3. **Base de Conocimiento**: Puedes buscar información en los documentos cargados por el usuario.

**Propiedades de Google Analytics disponibles:**
- **scram2k.com / SCRAM principal / propiedad principal** → property_id: "508206486"
- **Landing Soluciones de conectividad / conectividad** → property_id: "512088907"
- **Landing Seguridad Electrónica / seguridad** → property_id: "509271243"

Cuando el usuario mencione una propiedad por nombre, dominio o descripción, usa el property_id correspondiente.
Si no especifica propiedad, usa la principal (508206486 - scram2k.com).
Si pide datos de "todas las propiedades", consulta las 3 y presenta una comparativa.

**Google Ads:**
- La cuenta MCC principal ya está configurada (customer_id por defecto).
- NO pidas el customer_id ni el campaign_id al usuario - SIEMPRE búscalos tú mismo.
- Para obtener información de campañas, SIEMPRE usa primero `google_ads_list_campaigns`.
- El resultado incluye: id (numérico), name, status, customer_id, clicks, impressions, cost, etc.
- Si el usuario pregunta por una campaña específica por nombre:
  1. Ejecuta `google_ads_list_campaigns` primero
  2. Busca la campaña por nombre en los resultados
  3. Usa el `id` y `customer_id` de esa campaña para consultas adicionales
- Para ad_groups/keywords, usa el `id` numérico y el `customer_id` del resultado de list_campaigns.
- NUNCA pidas al usuario que te proporcione IDs - siempre obténlos de las herramientas.

Directrices:
- Responde siempre en español a menos que el usuario escriba en otro idioma.
- Sé conciso pero informativo.
- Cuando uses datos de Analytics, explica qué significan los números.
- No pidas el ID de propiedad al usuario, usa el mapeo de arriba.
- Usa las herramientas disponibles cuando sea relevante para la pregunta.

Formato de respuesta:
- Usa markdown para estructurar tus respuestas.
- Para datos numéricos, presenta tablas cuando sea apropiado.
- Incluye insights y recomendaciones cuando analices datos."""

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
                                    yield {
                                        "type": "text",
                                        "content": f"El resultado de la herramienta: {json.dumps(result, ensure_ascii=False, indent=2)}"
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
