"""Knowledge Base MCP tool for RAG queries.

Provides tools to search the document knowledge base.
"""

from typing import Any

import structlog
from sqlalchemy import func, select
from vertexai.generative_models import FunctionDeclaration

from src.database.connection import async_session_maker
from src.database.models import Document
from src.rag.retrieval import search_similar_chunks
from src.schemas.documents import DocumentStatus

logger = structlog.get_logger()


class KnowledgeBaseTool:
    """MCP tool for knowledge base queries."""

    def get_function_declarations(self) -> list[FunctionDeclaration]:
        """Get Gemini function declarations for KB tools.

        Returns:
            List of function declarations
        """
        return [
            FunctionDeclaration(
                name="search_knowledge_base",
                description="Busca información relevante en la base de conocimiento empresarial. Usa esto cuando el usuario pregunte sobre documentación, políticas, procedimientos o información específica de la empresa.",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "La consulta de búsqueda en lenguaje natural",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Número máximo de resultados (default: 5)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            FunctionDeclaration(
                name="list_documents",
                description="Lista los documentos disponibles en la base de conocimiento. Útil para saber qué información está disponible.",
                parameters={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "processing", "indexed", "error"],
                            "description": "Filtrar por estado del documento",
                        },
                    },
                },
            ),
        ]

    async def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a knowledge base tool.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            Tool execution result
        """
        if tool_name == "search_knowledge_base":
            return await self._search(args)
        elif tool_name == "list_documents":
            return await self._list_documents(args)
        else:
            return {"error": f"Unknown KB tool: {tool_name}"}

    async def _search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Search the knowledge base.

        Args:
            args: Search parameters

        Returns:
            Search results
        """
        query = args.get("query", "")
        top_k = args.get("top_k", 5)

        if not query:
            return {"error": "Query is required"}

        try:
            async with async_session_maker() as db:
                results = await search_similar_chunks(
                    db=db,
                    query=query,
                    top_k=top_k,
                    threshold=0.6,  # Lower threshold for tool use
                )

                logger.info(
                    "Knowledge base search",
                    query=query[:50],
                    results=len(results),
                )

                if not results:
                    return {
                        "query": query,
                        "results": [],
                        "message": "No se encontraron resultados relevantes en la base de conocimiento.",
                    }

                return {
                    "query": query,
                    "results": [
                        {
                            "content": r.content,
                            "similarity": r.similarity,
                            "document_id": str(r.document_id),
                        }
                        for r in results
                    ],
                    "total_results": len(results),
                }

        except Exception as e:
            logger.error("KB search failed", error=str(e), exc_info=True)
            return {"error": str(e)}

    async def _list_documents(self, args: dict[str, Any]) -> dict[str, Any]:
        """List available documents.

        Args:
            args: Filter parameters

        Returns:
            Document list
        """
        status_filter = args.get("status")

        try:
            async with async_session_maker() as db:
                query = select(
                    Document.id,
                    Document.original_name,
                    Document.status,
                    Document.chunk_count,
                    Document.created_at,
                )

                if status_filter:
                    query = query.where(Document.status == status_filter)

                query = query.order_by(Document.created_at.desc()).limit(20)

                result = await db.execute(query)
                rows = result.fetchall()

                return {
                    "documents": [
                        {
                            "id": str(row.id),
                            "name": row.original_name,
                            "status": row.status,
                            "chunks": row.chunk_count,
                            "created_at": row.created_at.isoformat(),
                        }
                        for row in rows
                    ],
                    "total": len(rows),
                }

        except Exception as e:
            logger.error("List documents failed", error=str(e), exc_info=True)
            return {"error": str(e)}
