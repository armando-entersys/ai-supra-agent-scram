"""Google Ads MCP Tool for AI-SupraAgent.

Provides tools to query Google Ads campaigns, ad groups, ads, and metrics
using the Google Ads API via GAQL (Google Ads Query Language).
"""

import json
import structlog
from typing import Any
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.protobuf import json_format
from vertexai.generative_models import FunctionDeclaration

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class GoogleAdsTool:
    """MCP Tool for Google Ads API operations."""

    def __init__(self):
        """Initialize the Google Ads client."""
        self._client = None
        self._customer_id = settings.google_ads_customer_id

    @property
    def client(self) -> GoogleAdsClient:
        """Lazy initialization of Google Ads client."""
        if self._client is None:
            try:
                # Load from YAML file or environment
                if settings.google_ads_config_path:
                    self._client = GoogleAdsClient.load_from_storage(
                        settings.google_ads_config_path
                    )
                else:
                    # Load from environment variables
                    config = {
                        "developer_token": settings.google_ads_developer_token,
                        "client_id": settings.google_ads_client_id,
                        "client_secret": settings.google_ads_client_secret,
                        "refresh_token": settings.google_ads_refresh_token,
                        "use_proto_plus": True,
                    }
                    # Only add login_customer_id if it has a value (for MCC accounts)
                    if settings.google_ads_login_customer_id:
                        config["login_customer_id"] = settings.google_ads_login_customer_id
                    self._client = GoogleAdsClient.load_from_dict(config)
                logger.info("Google Ads client initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize Google Ads client", error=str(e))
                raise
        return self._client

    def get_tools_schema(self) -> list[dict[str, Any]]:
        """Return the schema for Google Ads tools.

        Returns:
            List of tool definitions for the orchestrator
        """
        return [
            {
                "name": "google_ads_search",
                "description": """Execute a Google Ads Query Language (GAQL) query to retrieve campaign data,
                metrics, ad groups, ads, keywords, and more. Use this for custom queries and detailed analysis.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": """GAQL query string. Examples:
                            - SELECT campaign.name, campaign.status, metrics.impressions, metrics.clicks, metrics.cost_micros FROM campaign WHERE segments.date DURING LAST_30_DAYS
                            - SELECT ad_group.name, ad_group.status, metrics.conversions FROM ad_group WHERE campaign.id = '123456'
                            - SELECT ad_group_ad.ad.id, ad_group_ad.ad.name, metrics.impressions FROM ad_group_ad"""
                        },
                        "customer_id": {
                            "type": "string",
                            "description": "Google Ads customer ID (optional, uses default if not provided)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "google_ads_list_campaigns",
                "description": "List all campaigns with their status, budget, and key metrics for the last 30 days.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status_filter": {
                            "type": "string",
                            "enum": ["ALL", "ENABLED", "PAUSED", "REMOVED"],
                            "description": "Filter campaigns by status (default: ALL)"
                        },
                        "customer_id": {
                            "type": "string",
                            "description": "Google Ads customer ID (optional)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "google_ads_campaign_performance",
                "description": "Get detailed performance metrics for a specific campaign including clicks, impressions, conversions, cost, CTR, and CPC.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "The campaign ID to get performance for"
                        },
                        "date_range": {
                            "type": "string",
                            "enum": ["LAST_7_DAYS", "LAST_14_DAYS", "LAST_30_DAYS", "THIS_MONTH", "LAST_MONTH"],
                            "description": "Date range for metrics (default: LAST_30_DAYS)"
                        },
                        "customer_id": {
                            "type": "string",
                            "description": "Google Ads customer ID (optional)"
                        }
                    },
                    "required": ["campaign_id"]
                }
            },
            {
                "name": "google_ads_list_ad_groups",
                "description": "List all ad groups within a campaign with their metrics.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "Campaign ID to list ad groups for"
                        },
                        "customer_id": {
                            "type": "string",
                            "description": "Google Ads customer ID (optional)"
                        }
                    },
                    "required": ["campaign_id"]
                }
            },
            {
                "name": "google_ads_list_accessible_customers",
                "description": "List all Google Ads customer accounts accessible with the current credentials.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "google_ads_keyword_performance",
                "description": "Get keyword performance data for a campaign or ad group.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "Campaign ID (optional if ad_group_id provided)"
                        },
                        "ad_group_id": {
                            "type": "string",
                            "description": "Ad Group ID (optional if campaign_id provided)"
                        },
                        "date_range": {
                            "type": "string",
                            "enum": ["LAST_7_DAYS", "LAST_14_DAYS", "LAST_30_DAYS", "THIS_MONTH", "LAST_MONTH"],
                            "description": "Date range for metrics (default: LAST_30_DAYS)"
                        },
                        "customer_id": {
                            "type": "string",
                            "description": "Google Ads customer ID (optional)"
                        }
                    },
                    "required": []
                }
            }
        ]

    def get_function_declarations(self) -> list[FunctionDeclaration]:
        """Return Gemini FunctionDeclaration objects for the tools.

        Returns:
            List of FunctionDeclaration objects for Gemini
        """
        declarations = []
        for tool in self.get_tools_schema():
            declarations.append(
                FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=tool["parameters"],
                )
            )
        return declarations

    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute a Google Ads tool.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        try:
            if tool_name == "google_ads_search":
                return await self._search(parameters)
            elif tool_name == "google_ads_list_campaigns":
                return await self._list_campaigns(parameters)
            elif tool_name == "google_ads_campaign_performance":
                return await self._campaign_performance(parameters)
            elif tool_name == "google_ads_list_ad_groups":
                return await self._list_ad_groups(parameters)
            elif tool_name == "google_ads_list_accessible_customers":
                return await self._list_accessible_customers(parameters)
            elif tool_name == "google_ads_keyword_performance":
                return await self._keyword_performance(parameters)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except GoogleAdsException as ex:
            error_details = []
            for error in ex.failure.errors:
                error_details.append({
                    "error_code": str(error.error_code),
                    "message": error.message,
                })
            logger.error("Google Ads API error", tool=tool_name, errors=error_details)
            return {"error": "Google Ads API error", "details": error_details}
        except Exception as e:
            logger.error("Google Ads tool error", tool=tool_name, error=str(e))
            return {"error": str(e)}

    def _get_customer_id(self, parameters: dict[str, Any]) -> str:
        """Get customer ID from parameters or default."""
        customer_id = parameters.get("customer_id") or self._customer_id
        # Remove dashes if present
        return customer_id.replace("-", "") if customer_id else None

    def _convert_row_to_dict(self, row: Any) -> dict:
        """Convert a Google Ads row to a dictionary."""
        return json.loads(json_format.MessageToJson(row))

    async def _search(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute a GAQL query."""
        query = parameters.get("query")
        customer_id = self._get_customer_id(parameters)

        if not customer_id:
            return {"error": "Customer ID is required"}

        logger.info("Executing GAQL query", customer_id=customer_id, query=query[:100])

        ga_service = self.client.get_service("GoogleAdsService")
        response = ga_service.search(customer_id=customer_id, query=query)

        results = []
        for row in response:
            results.append(self._convert_row_to_dict(row))

        return {
            "success": True,
            "customer_id": customer_id,
            "query": query,
            "row_count": len(results),
            "results": results[:100]  # Limit to 100 rows
        }

    async def _list_campaigns(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """List all campaigns with metrics."""
        customer_id = self._get_customer_id(parameters)
        status_filter = parameters.get("status_filter", "ALL")

        if not customer_id:
            return {"error": "Customer ID is required"}

        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign.bidding_strategy_type,
                campaign_budget.amount_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM campaign
            WHERE segments.date DURING LAST_30_DAYS
        """

        if status_filter != "ALL":
            query += f" AND campaign.status = '{status_filter}'"

        query += " ORDER BY metrics.impressions DESC"

        logger.info("Listing campaigns", customer_id=customer_id)

        ga_service = self.client.get_service("GoogleAdsService")
        response = ga_service.search(customer_id=customer_id, query=query)

        campaigns = []
        for row in response:
            campaigns.append({
                "id": row.campaign.id,
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "channel_type": row.campaign.advertising_channel_type.name,
                "bidding_strategy": row.campaign.bidding_strategy_type.name,
                "budget_micros": row.campaign_budget.amount_micros,
                "budget": row.campaign_budget.amount_micros / 1_000_000,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost_micros": row.metrics.cost_micros,
                "cost": row.metrics.cost_micros / 1_000_000,
                "conversions": row.metrics.conversions,
                "ctr": round(row.metrics.ctr * 100, 2),
                "avg_cpc": row.metrics.average_cpc / 1_000_000,
            })

        return {
            "success": True,
            "customer_id": customer_id,
            "campaign_count": len(campaigns),
            "campaigns": campaigns
        }

    async def _campaign_performance(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get campaign performance metrics."""
        campaign_id = parameters.get("campaign_id")
        customer_id = self._get_customer_id(parameters)
        date_range = parameters.get("date_range", "LAST_30_DAYS")

        if not customer_id:
            return {"error": "Customer ID is required"}
        if not campaign_id:
            return {"error": "Campaign ID is required"}

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.ctr,
                metrics.average_cpc,
                metrics.cost_per_conversion,
                metrics.interaction_rate,
                metrics.video_views,
                metrics.video_view_rate
            FROM campaign
            WHERE campaign.id = {campaign_id}
                AND segments.date DURING {date_range}
            ORDER BY segments.date DESC
        """

        logger.info("Getting campaign performance", campaign_id=campaign_id)

        ga_service = self.client.get_service("GoogleAdsService")
        response = ga_service.search(customer_id=customer_id, query=query)

        daily_data = []
        totals = {
            "impressions": 0,
            "clicks": 0,
            "cost_micros": 0,
            "conversions": 0,
            "conversions_value": 0,
        }

        campaign_name = ""
        campaign_status = ""

        for row in response:
            campaign_name = row.campaign.name
            campaign_status = row.campaign.status.name

            daily_data.append({
                "date": row.segments.date,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost": row.metrics.cost_micros / 1_000_000,
                "conversions": row.metrics.conversions,
                "ctr": round(row.metrics.ctr * 100, 2),
            })

            totals["impressions"] += row.metrics.impressions
            totals["clicks"] += row.metrics.clicks
            totals["cost_micros"] += row.metrics.cost_micros
            totals["conversions"] += row.metrics.conversions
            totals["conversions_value"] += row.metrics.conversions_value

        return {
            "success": True,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "campaign_status": campaign_status,
            "date_range": date_range,
            "totals": {
                "impressions": totals["impressions"],
                "clicks": totals["clicks"],
                "cost": totals["cost_micros"] / 1_000_000,
                "conversions": totals["conversions"],
                "conversions_value": totals["conversions_value"],
                "ctr": round((totals["clicks"] / totals["impressions"] * 100), 2) if totals["impressions"] > 0 else 0,
                "cpc": round(totals["cost_micros"] / totals["clicks"] / 1_000_000, 2) if totals["clicks"] > 0 else 0,
            },
            "daily_data": daily_data[:30]  # Last 30 days
        }

    async def _list_ad_groups(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """List ad groups for a campaign."""
        campaign_id = parameters.get("campaign_id")
        customer_id = self._get_customer_id(parameters)

        if not customer_id:
            return {"error": "Customer ID is required"}
        if not campaign_id:
            return {"error": "Campaign ID is required"}

        query = f"""
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.type,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc
            FROM ad_group
            WHERE campaign.id = {campaign_id}
                AND segments.date DURING LAST_30_DAYS
            ORDER BY metrics.impressions DESC
        """

        logger.info("Listing ad groups", campaign_id=campaign_id)

        ga_service = self.client.get_service("GoogleAdsService")
        response = ga_service.search(customer_id=customer_id, query=query)

        ad_groups = []
        for row in response:
            ad_groups.append({
                "id": row.ad_group.id,
                "name": row.ad_group.name,
                "status": row.ad_group.status.name,
                "type": row.ad_group.type_.name,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost": row.metrics.cost_micros / 1_000_000,
                "conversions": row.metrics.conversions,
                "ctr": round(row.metrics.ctr * 100, 2),
                "avg_cpc": row.metrics.average_cpc / 1_000_000,
            })

        return {
            "success": True,
            "campaign_id": campaign_id,
            "ad_group_count": len(ad_groups),
            "ad_groups": ad_groups
        }

    async def _list_accessible_customers(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """List all accessible customer accounts."""
        customer_service = self.client.get_service("CustomerService")

        accessible_customers = customer_service.list_accessible_customers()

        customers = []
        for resource_name in accessible_customers.resource_names:
            customer_id = resource_name.split("/")[-1]
            customers.append({
                "resource_name": resource_name,
                "customer_id": customer_id,
            })

        logger.info("Listed accessible customers", count=len(customers))

        return {
            "success": True,
            "customer_count": len(customers),
            "customers": customers
        }

    async def _keyword_performance(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get keyword performance data."""
        campaign_id = parameters.get("campaign_id")
        ad_group_id = parameters.get("ad_group_id")
        customer_id = self._get_customer_id(parameters)
        date_range = parameters.get("date_range", "LAST_30_DAYS")

        if not customer_id:
            return {"error": "Customer ID is required"}
        if not campaign_id and not ad_group_id:
            return {"error": "Either campaign_id or ad_group_id is required"}

        query = f"""
            SELECT
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group_criterion.quality_info.quality_score,
                campaign.name,
                ad_group.name,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr,
                metrics.average_cpc,
                metrics.average_cost
            FROM keyword_view
            WHERE segments.date DURING {date_range}
        """

        if campaign_id:
            query += f" AND campaign.id = {campaign_id}"
        if ad_group_id:
            query += f" AND ad_group.id = {ad_group_id}"

        query += " ORDER BY metrics.impressions DESC LIMIT 100"

        logger.info("Getting keyword performance", campaign_id=campaign_id, ad_group_id=ad_group_id)

        ga_service = self.client.get_service("GoogleAdsService")
        response = ga_service.search(customer_id=customer_id, query=query)

        keywords = []
        for row in response:
            keywords.append({
                "keyword": row.ad_group_criterion.keyword.text,
                "match_type": row.ad_group_criterion.keyword.match_type.name,
                "status": row.ad_group_criterion.status.name,
                "quality_score": row.ad_group_criterion.quality_info.quality_score if row.ad_group_criterion.quality_info.quality_score else None,
                "campaign": row.campaign.name,
                "ad_group": row.ad_group.name,
                "impressions": row.metrics.impressions,
                "clicks": row.metrics.clicks,
                "cost": row.metrics.cost_micros / 1_000_000,
                "conversions": row.metrics.conversions,
                "ctr": round(row.metrics.ctr * 100, 2),
                "avg_cpc": row.metrics.average_cpc / 1_000_000,
            })

        return {
            "success": True,
            "date_range": date_range,
            "keyword_count": len(keywords),
            "keywords": keywords
        }


# Singleton instance
_google_ads_tool: GoogleAdsTool | None = None


def get_google_ads_tool() -> GoogleAdsTool | None:
    """Get or create the Google Ads tool instance.

    Returns:
        GoogleAdsTool instance if configured, None otherwise
    """
    global _google_ads_tool

    # Check if Google Ads is configured
    if not settings.google_ads_developer_token and not settings.google_ads_config_path:
        logger.info("Google Ads not configured, skipping tool initialization")
        return None

    if _google_ads_tool is None:
        try:
            _google_ads_tool = GoogleAdsTool()
        except Exception as e:
            logger.error("Failed to initialize Google Ads tool", error=str(e))
            return None

    return _google_ads_tool
