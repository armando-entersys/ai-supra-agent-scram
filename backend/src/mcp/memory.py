"""Persistent memory system for AI agent.

Stores context, insights, and preferences across sessions using BigQuery.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional
import structlog
from google.cloud import bigquery
from google.api_core.exceptions import NotFound, Conflict

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class AgentMemory:
    """Persistent memory system using BigQuery."""

    DATASET_ID = "ai_memory"
    CONTEXT_TABLE = "conversation_context"
    INSIGHTS_TABLE = "campaign_insights"
    ACTIONS_TABLE = "action_history"

    def __init__(self) -> None:
        """Initialize memory system."""
        self.project_id = settings.gcp_project_id
        self.client = bigquery.Client(project=self.project_id)
        self._ensure_tables()
        logger.info("AgentMemory initialized", project_id=self.project_id)

    def _ensure_tables(self) -> None:
        """Ensure all memory tables exist."""
        dataset_ref = f"{self.project_id}.{self.DATASET_ID}"

        # Create dataset if not exists
        try:
            self.client.get_dataset(dataset_ref)
        except NotFound:
            try:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                self.client.create_dataset(dataset)
                logger.info("Created memory dataset", dataset=dataset_ref)
            except Conflict:
                pass

        # Create context table
        self._create_table_if_not_exists(
            f"{dataset_ref}.{self.CONTEXT_TABLE}",
            [
                bigquery.SchemaField("session_id", "STRING", description="Chat session ID"),
                bigquery.SchemaField("user_id", "STRING", description="User identifier"),
                bigquery.SchemaField("context_type", "STRING", description="preference, insight, action, summary"),
                bigquery.SchemaField("context_key", "STRING", description="Unique key for this context"),
                bigquery.SchemaField("content", "JSON", description="Context content as JSON"),
                bigquery.SchemaField("created_at", "TIMESTAMP", description="Creation time"),
                bigquery.SchemaField("expires_at", "TIMESTAMP", description="Expiration time (null = never)"),
                bigquery.SchemaField("importance", "INTEGER", description="Importance score 1-10"),
            ]
        )

        # Create insights table
        self._create_table_if_not_exists(
            f"{dataset_ref}.{self.INSIGHTS_TABLE}",
            [
                bigquery.SchemaField("insight_id", "STRING", description="Unique insight ID"),
                bigquery.SchemaField("campaign_id", "STRING", description="Related campaign ID"),
                bigquery.SchemaField("insight_type", "STRING", description="anomaly, trend, opportunity, risk"),
                bigquery.SchemaField("title", "STRING", description="Short title"),
                bigquery.SchemaField("description", "STRING", description="Detailed description"),
                bigquery.SchemaField("data", "JSON", description="Supporting data"),
                bigquery.SchemaField("severity", "STRING", description="info, warning, critical"),
                bigquery.SchemaField("status", "STRING", description="new, acknowledged, resolved"),
                bigquery.SchemaField("created_at", "TIMESTAMP", description="When detected"),
                bigquery.SchemaField("resolved_at", "TIMESTAMP", description="When resolved"),
            ]
        )

        # Create action history table
        self._create_table_if_not_exists(
            f"{dataset_ref}.{self.ACTIONS_TABLE}",
            [
                bigquery.SchemaField("action_id", "STRING", description="Unique action ID"),
                bigquery.SchemaField("session_id", "STRING", description="Session where proposed"),
                bigquery.SchemaField("action_type", "STRING", description="keyword_negative, bid_adjust, pause, etc"),
                bigquery.SchemaField("target_entity", "STRING", description="Campaign/keyword/ad ID"),
                bigquery.SchemaField("proposed_change", "JSON", description="What was proposed"),
                bigquery.SchemaField("status", "STRING", description="proposed, approved, rejected, executed"),
                bigquery.SchemaField("proposed_at", "TIMESTAMP"),
                bigquery.SchemaField("decided_at", "TIMESTAMP"),
                bigquery.SchemaField("executed_at", "TIMESTAMP"),
                bigquery.SchemaField("result", "JSON", description="Execution result"),
            ]
        )

    def _create_table_if_not_exists(
        self, table_ref: str, schema: list[bigquery.SchemaField]
    ) -> None:
        """Create a table if it doesn't exist."""
        try:
            self.client.get_table(table_ref)
        except NotFound:
            try:
                table = bigquery.Table(table_ref, schema=schema)
                self.client.create_table(table)
                logger.info("Created memory table", table=table_ref)
            except Conflict:
                pass

    async def store_context(
        self,
        session_id: str,
        context_type: str,
        context_key: str,
        content: dict[str, Any],
        user_id: str = "default",
        importance: int = 5,
        ttl_hours: Optional[int] = None
    ) -> bool:
        """Store context in memory.

        Args:
            session_id: Current session ID
            context_type: Type of context (preference, insight, action, summary)
            context_key: Unique key for this context
            content: Content to store
            user_id: User identifier
            importance: Importance score 1-10
            ttl_hours: Time-to-live in hours (None = forever)

        Returns:
            Success status
        """
        try:
            now = datetime.utcnow()
            expires_at = (now + timedelta(hours=ttl_hours)).isoformat() if ttl_hours else None

            rows = [{
                "session_id": session_id,
                "user_id": user_id,
                "context_type": context_type,
                "context_key": context_key,
                "content": json.dumps(content),
                "created_at": now.isoformat(),
                "expires_at": expires_at,
                "importance": importance,
            }]

            table_ref = f"{self.project_id}.{self.DATASET_ID}.{self.CONTEXT_TABLE}"
            errors = self.client.insert_rows_json(table_ref, rows)

            if errors:
                logger.error("Failed to store context", errors=errors)
                return False

            logger.info("Context stored", context_type=context_type, key=context_key)
            return True

        except Exception as e:
            logger.error("Error storing context", error=str(e))
            return False

    async def get_context(
        self,
        user_id: str = "default",
        context_types: Optional[list[str]] = None,
        limit: int = 20
    ) -> list[dict[str, Any]]:
        """Retrieve relevant context for a user.

        Args:
            user_id: User identifier
            context_types: Filter by context types
            limit: Max items to return

        Returns:
            List of context items
        """
        try:
            table_ref = f"{self.project_id}.{self.DATASET_ID}.{self.CONTEXT_TABLE}"

            where_clauses = [
                f"user_id = '{user_id}'",
                "(expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP())"
            ]

            if context_types:
                types_str = ", ".join([f"'{t}'" for t in context_types])
                where_clauses.append(f"context_type IN ({types_str})")

            query = f"""
                SELECT context_type, context_key, content, importance, created_at
                FROM `{table_ref}`
                WHERE {" AND ".join(where_clauses)}
                ORDER BY importance DESC, created_at DESC
                LIMIT {limit}
            """

            results = []
            for row in self.client.query(query).result():
                content = json.loads(row.content) if isinstance(row.content, str) else row.content
                results.append({
                    "type": row.context_type,
                    "key": row.context_key,
                    "content": content,
                    "importance": row.importance,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })

            return results

        except Exception as e:
            logger.error("Error retrieving context", error=str(e))
            return []

    async def store_insight(
        self,
        campaign_id: str,
        insight_type: str,
        title: str,
        description: str,
        data: dict[str, Any],
        severity: str = "info"
    ) -> str:
        """Store a campaign insight.

        Args:
            campaign_id: Related campaign
            insight_type: anomaly, trend, opportunity, risk
            title: Short title
            description: Detailed description
            data: Supporting data
            severity: info, warning, critical

        Returns:
            Insight ID
        """
        import uuid
        try:
            insight_id = str(uuid.uuid4())[:8]
            now = datetime.utcnow()

            rows = [{
                "insight_id": insight_id,
                "campaign_id": campaign_id,
                "insight_type": insight_type,
                "title": title,
                "description": description,
                "data": json.dumps(data),
                "severity": severity,
                "status": "new",
                "created_at": now.isoformat(),
                "resolved_at": None,
            }]

            table_ref = f"{self.project_id}.{self.DATASET_ID}.{self.INSIGHTS_TABLE}"
            errors = self.client.insert_rows_json(table_ref, rows)

            if errors:
                logger.error("Failed to store insight", errors=errors)
                return ""

            logger.info("Insight stored", insight_id=insight_id, type=insight_type)
            return insight_id

        except Exception as e:
            logger.error("Error storing insight", error=str(e))
            return ""

    async def get_pending_insights(
        self,
        campaign_id: Optional[str] = None,
        severity: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Get unresolved insights.

        Args:
            campaign_id: Filter by campaign
            severity: Filter by severity

        Returns:
            List of insights
        """
        try:
            table_ref = f"{self.project_id}.{self.DATASET_ID}.{self.INSIGHTS_TABLE}"

            where_clauses = ["status IN ('new', 'acknowledged')"]

            if campaign_id:
                where_clauses.append(f"campaign_id = '{campaign_id}'")
            if severity:
                where_clauses.append(f"severity = '{severity}'")

            query = f"""
                SELECT *
                FROM `{table_ref}`
                WHERE {" AND ".join(where_clauses)}
                ORDER BY
                    CASE severity
                        WHEN 'critical' THEN 1
                        WHEN 'warning' THEN 2
                        ELSE 3
                    END,
                    created_at DESC
                LIMIT 50
            """

            results = []
            for row in self.client.query(query).result():
                results.append({
                    "insight_id": row.insight_id,
                    "campaign_id": row.campaign_id,
                    "type": row.insight_type,
                    "title": row.title,
                    "description": row.description,
                    "data": json.loads(row.data) if isinstance(row.data, str) else row.data,
                    "severity": row.severity,
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })

            return results

        except Exception as e:
            logger.error("Error getting insights", error=str(e))
            return []

    async def propose_action(
        self,
        session_id: str,
        action_type: str,
        target_entity: str,
        proposed_change: dict[str, Any]
    ) -> str:
        """Propose an action for approval.

        Args:
            session_id: Current session
            action_type: Type of action (keyword_negative, bid_adjust, etc)
            target_entity: What to modify
            proposed_change: The proposed change details

        Returns:
            Action ID
        """
        import uuid
        try:
            action_id = str(uuid.uuid4())[:8]
            now = datetime.utcnow()

            rows = [{
                "action_id": action_id,
                "session_id": session_id,
                "action_type": action_type,
                "target_entity": target_entity,
                "proposed_change": json.dumps(proposed_change),
                "status": "proposed",
                "proposed_at": now.isoformat(),
                "decided_at": None,
                "executed_at": None,
                "result": None,
            }]

            table_ref = f"{self.project_id}.{self.DATASET_ID}.{self.ACTIONS_TABLE}"
            errors = self.client.insert_rows_json(table_ref, rows)

            if errors:
                logger.error("Failed to propose action", errors=errors)
                return ""

            logger.info("Action proposed", action_id=action_id, type=action_type)
            return action_id

        except Exception as e:
            logger.error("Error proposing action", error=str(e))
            return ""

    async def get_conversation_summary(self, user_id: str = "default") -> str:
        """Get a summary of past conversations for context.

        Args:
            user_id: User identifier

        Returns:
            Summary text
        """
        context = await self.get_context(
            user_id=user_id,
            context_types=["summary", "preference", "insight"],
            limit=10
        )

        if not context:
            return ""

        lines = ["**Contexto de sesiones anteriores:**\n"]

        for item in context:
            if item["type"] == "preference":
                lines.append(f"- Preferencia: {item['content'].get('description', '')}")
            elif item["type"] == "summary":
                lines.append(f"- Resumen previo: {item['content'].get('summary', '')}")
            elif item["type"] == "insight":
                lines.append(f"- Insight: {item['content'].get('title', '')}")

        return "\n".join(lines)


# Singleton instance
_memory_instance: Optional[AgentMemory] = None


def get_agent_memory() -> Optional[AgentMemory]:
    """Get or create agent memory instance."""
    global _memory_instance
    if _memory_instance is None:
        try:
            _memory_instance = AgentMemory()
        except Exception as e:
            logger.error("Failed to initialize AgentMemory", error=str(e))
            return None
    return _memory_instance
