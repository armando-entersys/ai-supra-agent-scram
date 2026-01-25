"""Intelligent Agent with enhanced reasoning capabilities.

Combines RAG retrieval, semantic understanding, and context memory
for more intelligent and natural conversations.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional
import asyncio
import structlog
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Part

from src.config import get_settings
from src.mcp.autonomous_agent import get_data_discovery, get_autonomous_analyzer
from src.mcp.memory import get_agent_memory

logger = structlog.get_logger()
settings = get_settings()


class ConversationContext:
    """Manages conversation context and memory."""

    def __init__(self, session_id: str, max_turns: int = 20) -> None:
        """Initialize conversation context.

        Args:
            session_id: Unique session identifier
            max_turns: Maximum conversation turns to remember
        """
        self.session_id = session_id
        self.max_turns = max_turns
        self.turns: list[dict[str, Any]] = []
        self.entities: dict[str, Any] = {}  # Extracted entities
        self.topics: list[str] = []  # Conversation topics
        self.user_preferences: dict[str, Any] = {}
        self.pending_questions: list[str] = []

    def add_turn(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Add a conversation turn."""
        self.turns.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        })
        # Keep only recent turns
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def extract_entities(self, text: str) -> dict[str, Any]:
        """Extract named entities from text."""
        entities = {
            "campaigns": [],
            "metrics": [],
            "dates": [],
            "locations": [],
            "amounts": [],
        }

        text_lower = text.lower()

        # Campaign name patterns
        campaign_keywords = ["campaña", "campaign", "seguridad", "conectividad"]
        for kw in campaign_keywords:
            if kw in text_lower:
                # Find the context around the keyword
                idx = text_lower.find(kw)
                context = text[max(0, idx-10):idx+50]
                entities["campaigns"].append(context.strip())

        # Metric patterns
        metrics = ["ctr", "cpc", "cpa", "roas", "conversiones", "conversions", "clics", "clicks", "impresiones"]
        for metric in metrics:
            if metric in text_lower:
                entities["metrics"].append(metric)

        # Amount patterns (numbers with $ or %)
        import re
        amounts = re.findall(r'\$[\d,]+\.?\d*|\d+\.?\d*%', text)
        entities["amounts"] = amounts

        # Date patterns
        dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|ayer|hoy|esta semana|este mes|últimos \d+ días', text_lower)
        entities["dates"] = dates

        return entities

    def get_context_summary(self) -> str:
        """Get a summary of the conversation context."""
        if not self.turns:
            return ""

        recent_turns = self.turns[-5:]  # Last 5 turns
        summary_parts = []

        if self.topics:
            summary_parts.append(f"Temas discutidos: {', '.join(self.topics[-3:])}")

        if self.entities.get("campaigns"):
            summary_parts.append(f"Campañas mencionadas: {', '.join(set(self.entities['campaigns']))}")

        if self.entities.get("metrics"):
            summary_parts.append(f"Métricas de interés: {', '.join(set(self.entities['metrics']))}")

        # Add recent questions
        user_questions = [t["content"] for t in recent_turns if t["role"] == "user"]
        if user_questions:
            summary_parts.append(f"Preguntas recientes: {user_questions[-1][:100]}")

        return "\n".join(summary_parts) if summary_parts else ""


class IntentClassifier:
    """Classifies user intents for better response routing."""

    # Intent patterns
    INTENTS = {
        "analysis_request": [
            "analiza", "analyze", "análisis", "analysis",
            "diagnóstico", "diagnostic", "evalúa", "evaluate",
        ],
        "comparison": [
            "compara", "compare", "versus", "vs", "diferencia", "difference",
        ],
        "trend_analysis": [
            "tendencia", "trend", "evolución", "evolution", "histórico", "history",
            "cómo ha cambiado", "how has it changed",
        ],
        "recommendation": [
            "recomienda", "recommend", "sugieres", "suggest", "qué hacer", "what to do",
            "mejora", "improve", "optimiza", "optimize",
        ],
        "status_query": [
            "cómo va", "how is", "estado", "status", "resumen", "summary",
            "qué tal", "hows it going",
        ],
        "data_exploration": [
            "qué datos", "what data", "muéstrame", "show me",
            "lista", "list", "cuántos", "how many",
        ],
        "problem_diagnosis": [
            "por qué", "why", "problema", "problem", "error", "falla", "fail",
            "no funciona", "doesn't work", "cero conversiones", "zero conversions",
        ],
        "forecast": [
            "predicción", "prediction", "proyección", "projection", "futuro", "future",
            "qué esperar", "what to expect",
        ],
    }

    @classmethod
    def classify(cls, text: str) -> list[tuple[str, float]]:
        """Classify the intent of a user message.

        Args:
            text: User message text

        Returns:
            List of (intent, confidence) tuples, sorted by confidence
        """
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for intent, keywords in cls.INTENTS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > 0:
                # Score based on number of matches and keyword specificity
                scores[intent] = matches / len(keywords)

        # Sort by score
        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_intents if sorted_intents else [("general", 0.5)]


class IntelligentAgent:
    """Agent with enhanced reasoning and context awareness."""

    def __init__(self) -> None:
        """Initialize the intelligent agent."""
        self.discovery = get_data_discovery()
        self.analyzer = get_autonomous_analyzer()
        self.memory = get_agent_memory()
        self.contexts: dict[str, ConversationContext] = {}

        # Initialize Vertex AI
        if settings.gcp_project_id and settings.gcp_location:
            aiplatform.init(
                project=settings.gcp_project_id,
                location=settings.gcp_location,
            )

        logger.info("Intelligent agent initialized")

    def get_or_create_context(self, session_id: str) -> ConversationContext:
        """Get or create a conversation context for a session."""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext(session_id)
        return self.contexts[session_id]

    async def preprocess_query(self, query: str, session_id: str) -> dict[str, Any]:
        """Preprocess a user query for better understanding.

        Args:
            query: User's raw query
            session_id: Session identifier

        Returns:
            Preprocessed query information
        """
        context = self.get_or_create_context(session_id)

        # Extract entities
        entities = context.extract_entities(query)
        context.entities.update({
            k: list(set(context.entities.get(k, []) + v))
            for k, v in entities.items()
        })

        # Classify intent
        intents = IntentClassifier.classify(query)
        primary_intent = intents[0][0] if intents else "general"

        # Detect language
        lang = self._detect_language(query)

        # Add turn to context
        context.add_turn("user", query, {"intent": primary_intent, "entities": entities})

        return {
            "original_query": query,
            "intent": primary_intent,
            "intent_confidence": intents[0][1] if intents else 0.5,
            "entities": entities,
            "language": lang,
            "context_summary": context.get_context_summary(),
            "requires_data": self._requires_data_access(primary_intent),
            "suggested_tools": self._suggest_tools(primary_intent, entities),
        }

    def _detect_language(self, text: str) -> str:
        """Simple language detection."""
        spanish_indicators = ["qué", "cómo", "cuál", "análisis", "campaña", "conversiones", "rendimiento"]
        english_indicators = ["what", "how", "which", "analysis", "campaign", "conversions", "performance"]

        text_lower = text.lower()
        spanish_count = sum(1 for w in spanish_indicators if w in text_lower)
        english_count = sum(1 for w in english_indicators if w in text_lower)

        return "es" if spanish_count >= english_count else "en"

    def _requires_data_access(self, intent: str) -> bool:
        """Determine if the intent requires data access."""
        data_intents = {
            "analysis_request", "comparison", "trend_analysis",
            "status_query", "data_exploration", "problem_diagnosis", "forecast"
        }
        return intent in data_intents

    def _suggest_tools(self, intent: str, entities: dict) -> list[str]:
        """Suggest tools based on intent and entities."""
        tool_map = {
            "analysis_request": ["bq_auto_analyze", "google_ads_list_campaigns"],
            "comparison": ["bq_smart_query", "google_ads_campaign_performance"],
            "trend_analysis": ["bq_run_query", "run_report"],
            "status_query": ["google_ads_list_campaigns", "bq_auto_analyze"],
            "data_exploration": ["bq_discover_data", "bq_list_datasets"],
            "problem_diagnosis": ["bq_auto_analyze", "google_ads_device_performance"],
            "forecast": ["bq_run_query", "bq_smart_query"],
            "recommendation": ["bq_auto_analyze", "search_knowledge_base"],
        }
        return tool_map.get(intent, ["bq_discover_data"])

    async def generate_proactive_insights(self, session_id: str) -> list[dict[str, Any]]:
        """Generate proactive insights based on current data.

        Args:
            session_id: Session identifier

        Returns:
            List of proactive insights
        """
        insights = []

        try:
            if self.analyzer:
                analysis = await self.analyzer.auto_analyze()

                # Check for anomalies
                anomalies = analysis.get("anomalies", [])
                for anomaly in anomalies:
                    insights.append({
                        "type": "anomaly",
                        "severity": anomaly.get("severity", "info"),
                        "title": f"Alerta: {anomaly.get('entity', 'N/A')}",
                        "description": anomaly.get("details", ""),
                        "suggested_action": "Investigar esta anomalía",
                    })

                # Check for recommendations
                recommendations = analysis.get("recommendations", [])
                for rec in recommendations[:3]:  # Top 3
                    insights.append({
                        "type": "recommendation",
                        "severity": "info" if rec.get("priority") != "urgent" else "warning",
                        "title": rec.get("action", ""),
                        "description": rec.get("reason", ""),
                        "suggested_action": rec.get("steps", [])[0] if rec.get("steps") else None,
                    })

        except Exception as e:
            logger.error("Failed to generate proactive insights", error=str(e))

        return insights

    async def enhance_response(
        self,
        response: str,
        query_info: dict[str, Any],
        session_id: str,
    ) -> str:
        """Enhance a response with additional context and insights.

        Args:
            response: Original response
            query_info: Preprocessed query information
            session_id: Session identifier

        Returns:
            Enhanced response
        """
        context = self.get_or_create_context(session_id)

        # Add turn to context
        context.add_turn("assistant", response)

        # Add follow-up suggestions based on intent
        follow_ups = self._generate_follow_up_suggestions(query_info["intent"])

        if follow_ups:
            response += "\n\n---\n**Preguntas relacionadas:**\n"
            for fu in follow_ups[:3]:
                response += f"- {fu}\n"

        return response

    def _generate_follow_up_suggestions(self, intent: str) -> list[str]:
        """Generate follow-up question suggestions."""
        suggestions_map = {
            "analysis_request": [
                "Quiero ver el detalle por dispositivo",
                "Compara con el mes anterior",
                "Qué keywords tienen mejor rendimiento?",
            ],
            "comparison": [
                "Qué factores explican esta diferencia?",
                "Muéstrame la tendencia histórica",
                "Qué recomendaciones tienes?",
            ],
            "trend_analysis": [
                "Qué causó los cambios más significativos?",
                "Hay estacionalidad en los datos?",
                "Qué proyectas para el próximo mes?",
            ],
            "problem_diagnosis": [
                "Cómo puedo solucionarlo?",
                "Hay patrones similares en otras campañas?",
                "Cuál es el impacto financiero?",
            ],
            "status_query": [
                "Dame más detalles sobre la campaña con peor rendimiento",
                "Qué oportunidades hay para mejorar?",
                "Compara con benchmarks de la industria",
            ],
        }
        return suggestions_map.get(intent, [
            "Analiza el rendimiento general",
            "Qué recomendaciones tienes?",
            "Muestra datos de Google Ads",
        ])


# Singleton instance
_intelligent_agent: Optional[IntelligentAgent] = None


def get_intelligent_agent() -> Optional[IntelligentAgent]:
    """Get or create intelligent agent instance."""
    global _intelligent_agent
    if _intelligent_agent is None:
        try:
            _intelligent_agent = IntelligentAgent()
        except Exception as e:
            logger.error("Failed to initialize intelligent agent", error=str(e))
            return None
    return _intelligent_agent
