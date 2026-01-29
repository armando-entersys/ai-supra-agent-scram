"""Agent orchestrator using the new Google Gen AI SDK.

This is the new implementation using google-genai SDK which replaces
the deprecated vertexai.generative_models (deprecated June 2025).

Key differences from legacy orchestrator:
- Uses genai.Client instead of GenerativeModel
- Uses types.FunctionDeclaration instead of vertexai FunctionDeclaration
- Different streaming API
- Can use automatic function calling (disabled for our use case)
"""

import json
import os
from datetime import datetime
from typing import Any, AsyncGenerator
import asyncio

import structlog
from google import genai
from google.genai import types

from src.config import get_settings
from src.database.connection import async_session_maker
from src.mcp.google_analytics import GoogleAnalyticsTool
from src.mcp.google_ads import get_google_ads_tool, GoogleAdsTool
from src.mcp.knowledge_base import KnowledgeBaseTool
from src.mcp.web_search import get_web_search_tool, WebSearchTool
from src.mcp.bigquery import get_bigquery_tool, BigQueryTool
from src.mcp.leads_tool import get_leads_tool, LeadsTool
from src.mcp.memory import get_agent_memory
from src.mcp.alerts import get_campaign_alerts
from src.rag.retrieval import get_context_for_query

logger = structlog.get_logger()
settings = get_settings()

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0


def _serialize_result(result: Any) -> dict:
    """Serialize tool result for function response."""
    try:
        if result is None:
            return {"result": "null"}
        if isinstance(result, str):
            return {"result": result}
        if isinstance(result, (bool, int, float)):
            return {"result": str(result)}
        return {"result": json.dumps(result, ensure_ascii=False, default=str)}
    except Exception:
        return {"result": str(result)[:2000]}


class GenAIOrchestrator:
    """Orchestrator using the new Google Gen AI SDK."""

    def __init__(self) -> None:
        """Initialize the orchestrator with Gen AI client."""
        # Set environment for Vertex AI
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        os.environ["GOOGLE_CLOUD_PROJECT"] = settings.gcp_project_id
        os.environ["GOOGLE_CLOUD_LOCATION"] = settings.vertex_ai_location

        # Initialize Gen AI client
        self.client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.vertex_ai_location,
        )

        # Initialize tools
        self.ga_tool = GoogleAnalyticsTool()
        self.kb_tool = KnowledgeBaseTool()
        self.ads_tool = get_google_ads_tool()
        self.web_tool = get_web_search_tool()
        self.bq_tool = get_bigquery_tool()
        self.leads_tool = get_leads_tool()

        # Memory and alerts
        self.memory = get_agent_memory()
        self.alerts = get_campaign_alerts()

        # Build tool declarations
        self.tools = self._build_tools()

        # System instruction
        self.system_instruction = self._build_system_instruction()

        # Model name
        self.model_name = settings.gemini_model

        logger.info(
            "GenAIOrchestrator initialized",
            model=self.model_name,
            tools_count=len(self.tools),
        )

    def _build_system_instruction(self) -> str:
        """Build optimized system instruction."""
        current_date = datetime.now().strftime("%Y-%m-%d")

        return f"""ROL: Consultor estratégico de marketing digital para SCRAM (tecnología y seguridad electrónica).
Fecha: {current_date}

REGLAS CRÍTICAS:
1. IDIOMA: Responde en el MISMO idioma del usuario. Nunca mezcles.
2. SIN PENSAMIENTO VISIBLE: Nunca escribas "Pensamiento", "Voy a", "Déjame", "Let me". Primera palabra = emoji o respuesta directa.
3. LONGITUD ADAPTATIVA:
   - Pregunta simple (sí/no, cuánto) → 2-4 oraciones
   - Pregunta compleja (análisis) → 📊RESUMEN → 🔍ANÁLISIS → 💡INSIGHTS → ✅RECOMENDACIONES

ECOSISTEMA:
- GA4 Principal (scram2k.com): 508206486
- GA4 Seguridad: 509271243
- GA4 Conectividad: 512088907

HERRAMIENTAS - Flujo recomendado:
1. `google_ads_list_campaigns` PRIMERO para obtener IDs
2. `leads_from_google_ads` para datos REALES del CRM
3. Compara siempre: Ads reporta ~1 conversión pero CRM tiene 25+ leads de Ads = TRACKING ROTO

REGLAS DE HERRAMIENTAS:
- NO uses `google_ads_search` con GAQL (falla)
- Ejecuta herramientas SIN pedir permiso
- NUNCA pidas IDs al usuario
- Encadena hasta 10 herramientas si es necesario
- Para análisis cruzado usa `bq_auto_analyze`

BENCHMARKS: CTR >2% bueno, CPC <$2 bueno, Conv Rate >3% bueno

PRINCIPIOS:
- Sé estratégico, no técnico
- Cruza datos de múltiples fuentes
- Siempre da recomendaciones accionables
- Identifica causa raíz, no síntomas"""

    def _build_tools(self) -> list[types.FunctionDeclaration]:
        """Build function declarations for Gen AI SDK."""
        declarations = []

        # Helper to convert legacy FunctionDeclaration to dict
        def convert_declaration(fd) -> dict:
            # Use to_dict() if available (vertexai FunctionDeclaration)
            if hasattr(fd, 'to_dict'):
                return fd.to_dict()
            # Fallback for other types
            return {
                "name": getattr(fd, 'name', fd._raw_function_declaration.name if hasattr(fd, '_raw_function_declaration') else 'unknown'),
                "description": getattr(fd, 'description', fd._raw_function_declaration.description if hasattr(fd, '_raw_function_declaration') else ''),
                "parameters": getattr(fd, 'parameters', {}),
            }

        # Google Analytics
        for fd in self.ga_tool.get_function_declarations():
            declarations.append(convert_declaration(fd))

        # Knowledge Base
        for fd in self.kb_tool.get_function_declarations():
            declarations.append(convert_declaration(fd))

        # Google Ads
        if self.ads_tool:
            for fd in self.ads_tool.get_function_declarations():
                declarations.append(convert_declaration(fd))

        # Web Search
        if self.web_tool:
            for fd in self.web_tool.get_function_declarations():
                declarations.append(convert_declaration(fd))

        # BigQuery
        if self.bq_tool:
            for fd in self.bq_tool.get_function_declarations():
                declarations.append(convert_declaration(fd))

        # Leads
        if self.leads_tool:
            for fd in self.leads_tool.get_function_declarations():
                declarations.append(convert_declaration(fd))

        return declarations

    async def _execute_tool(self, tool_name: str, tool_args: dict) -> Any:
        """Execute a tool and return result."""
        logger.info("Executing tool", tool_name=tool_name, args=tool_args)

        try:
            if tool_name.startswith("ga_") or tool_name in [
                "run_report", "run_realtime_report", "get_property_details", "get_account_summaries"
            ]:
                return await self.ga_tool.execute(tool_name, tool_args)
            elif tool_name.startswith("kb_") or tool_name in ["search_knowledge_base", "list_documents"]:
                return await self.kb_tool.execute(tool_name, tool_args)
            elif tool_name.startswith("google_ads_") and self.ads_tool:
                return await self.ads_tool.execute(tool_name, tool_args)
            elif tool_name == "web_search" and self.web_tool:
                return await self.web_tool.execute(tool_name, tool_args)
            elif tool_name.startswith("bq_") and self.bq_tool:
                return await self.bq_tool.execute(tool_name, tool_args)
            elif tool_name.startswith("leads_") and self.leads_tool:
                return self.leads_tool.execute(tool_name, tool_args)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error("Tool execution failed", tool_name=tool_name, error=str(e))
            return {"error": str(e)}

    async def stream_response(
        self,
        messages: list[dict[str, str]],
        use_rag: bool = True,
        use_analytics: bool = True,
        session_id: str = "default",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream response using Gen AI SDK.

        Args:
            messages: Conversation history
            use_rag: Whether to include RAG context
            use_analytics: Whether to enable Analytics tools
            session_id: Session identifier

        Yields:
            Stream events (text, tool_call, error, done)
        """
        try:
            # Build contents
            contents = []

            # Get RAG context
            rag_context = ""
            if use_rag and messages:
                last_user_msg = next(
                    (m["content"] for m in reversed(messages) if m["role"] == "user"),
                    None,
                )
                if last_user_msg:
                    async with async_session_maker() as db:
                        rag_context = await get_context_for_query(db, last_user_msg)

            # Build conversation
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"]

                # Add context to last user message
                if role == "user" and msg == messages[-1] and rag_context:
                    content = f"**Contexto:**\n{rag_context}\n\n**Pregunta:** {content}"

                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content)]
                ))

            # Generate config with tools
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=1.0,
                top_p=0.95,
                max_output_tokens=8192,
                tools=[types.Tool(function_declarations=self.tools)],
                # Disable automatic function calling - we handle it manually
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            )

            # Generate with streaming
            total_tool_calls = 0
            max_iterations = 10
            total_text_emitted = 0  # Track total text length to detect complete responses
            text_response_count = 0  # Track how many times we've emitted text

            for iteration in range(max_iterations):
                logger.info("Generating response", iteration=iteration,
                           text_emitted=total_text_emitted, text_responses=text_response_count)

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )

                # Check for function calls
                if response.candidates and response.candidates[0].content.parts:
                    text_parts = []
                    function_calls = []

                    # First pass: categorize all parts
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_calls.append(part.function_call)
                        elif hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)

                    # Calculate total text in this response
                    response_text_length = sum(len(t) for t in text_parts)

                    # SIMPLE RULE: If we already emitted one text response, stop
                    # This prevents the model from regenerating after tool calls
                    if text_response_count > 0 and response_text_length > 100:
                        logger.info("Stopping - already have a text response",
                                   previous_responses=text_response_count)
                        break

                    # Emit all text parts and STOP if we have any text
                    if text_parts:
                        for text in text_parts:
                            yield {"type": "text", "content": text}
                            total_text_emitted += len(text)
                        # Once we emit text, we're DONE - don't process any more tool calls
                        logger.info("Text response emitted, stopping loop",
                                   text_length=total_text_emitted)
                        break

                    # If there are function calls (and NO text), process ALL of them
                    # Gen AI SDK requires response to ALL function calls in a turn
                    if function_calls:
                        function_response_parts = []

                        for fc in function_calls:
                            tool_name = fc.name
                            tool_args = dict(fc.args) if fc.args else {}

                            # Emit tool call running event
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
                            total_tool_calls += 1

                            # Emit tool call completed event
                            yield {
                                "type": "tool_call",
                                "data": {
                                    "tool_name": tool_name,
                                    "tool_input": tool_args,
                                    "status": "completed",
                                    "result": result,
                                },
                            }

                            # Collect function response part
                            function_response_parts.append(
                                types.Part.from_function_response(
                                    name=tool_name,
                                    response=_serialize_result(result),
                                )
                            )

                        # Add model response and ALL tool results to contents
                        contents.append(response.candidates[0].content)
                        contents.append(types.Content(
                            role="user",
                            parts=function_response_parts
                        ))
                        # Continue loop to get model's response to tool results
                    else:
                        # No text and no function calls - we're done
                        break
                else:
                    # No content, we're done
                    break

            logger.info("Generation completed", total_tool_calls=total_tool_calls)
            yield {"type": "done"}

        except Exception as e:
            logger.error("Stream response error", error=str(e), exc_info=True)
            yield {"type": "error", "message": str(e)}
            yield {"type": "done"}


# Singleton instance
_genai_orchestrator: GenAIOrchestrator | None = None


def get_genai_orchestrator() -> GenAIOrchestrator:
    """Get or create the Gen AI orchestrator instance."""
    global _genai_orchestrator
    if _genai_orchestrator is None:
        _genai_orchestrator = GenAIOrchestrator()
    return _genai_orchestrator
