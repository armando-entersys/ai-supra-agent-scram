"""Google Ads to BigQuery Export Tool.

Exports Google Ads data directly to BigQuery using the Ads API.
Supports direct client account access without requiring an MCC.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any
import structlog
from google.cloud import bigquery
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class AdsTooBigQueryExporter:
    """Exports Google Ads data to BigQuery."""

    def __init__(self) -> None:
        """Initialize the exporter."""
        self.bq_client = bigquery.Client(project=settings.gcp_project_id)
        self.dataset_id = "google_ads_data"
        self.project_id = settings.gcp_project_id

        # Build config for Google Ads client
        ads_config = {
            "developer_token": settings.google_ads_developer_token,
            "client_id": settings.google_ads_client_id,
            "client_secret": settings.google_ads_client_secret,
            "refresh_token": settings.google_ads_refresh_token,
            "use_proto_plus": True,
        }

        # Only add login_customer_id if MCC is configured
        if settings.google_ads_login_customer_id:
            ads_config["login_customer_id"] = settings.google_ads_login_customer_id

        self.ads_client = GoogleAdsClient.load_from_dict(ads_config)

        # Get client accounts - prefer explicit config, fallback to discovery
        self.client_accounts = self._get_client_accounts()

        logger.info("AdsTooBigQueryExporter initialized",
                   client_accounts=self.client_accounts,
                   using_mcc=bool(settings.google_ads_login_customer_id))

    def _get_client_accounts(self) -> list[str]:
        """Get list of client accounts to export.

        Priority:
        1. Explicit list from GOOGLE_ADS_CLIENT_ACCOUNTS env var
        2. Auto-discover accessible accounts
        """
        # First check for explicitly configured accounts
        if settings.ads_client_account_list:
            accounts = settings.ads_client_account_list
            logger.info("Using configured client accounts", accounts=accounts)
            return accounts

        # Fallback: discover accessible accounts
        try:
            customer_service = self.ads_client.get_service("CustomerService")
            accessible = customer_service.list_accessible_customers()

            accounts = []
            mcc_id = settings.google_ads_login_customer_id or settings.google_ads_customer_id

            for resource_name in accessible.resource_names:
                customer_id = resource_name.split("/")[-1]
                # Skip the MCC itself if configured
                if mcc_id and customer_id == mcc_id:
                    continue
                accounts.append(customer_id)

            logger.info("Discovered accessible accounts", accounts=accounts)
            return accounts

        except Exception as e:
            logger.error("Failed to get client accounts", error=str(e))
            # Last resort: use default customer_id
            if settings.google_ads_customer_id:
                return [settings.google_ads_customer_id]
            return []

    def _ensure_dataset(self) -> None:
        """Ensure BigQuery dataset exists."""
        from google.api_core.exceptions import NotFound, Conflict

        dataset_ref = f"{self.project_id}.{self.dataset_id}"
        try:
            self.bq_client.get_dataset(dataset_ref)
            logger.info("BigQuery dataset exists", dataset=dataset_ref)
        except NotFound:
            try:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                self.bq_client.create_dataset(dataset)
                logger.info("Created BigQuery dataset", dataset=dataset_ref)
            except Conflict:
                # Dataset was created by another process
                logger.info("BigQuery dataset already exists", dataset=dataset_ref)

    async def export_campaign_performance(self, days_back: int = 30) -> dict[str, Any]:
        """Export campaign performance data to BigQuery.

        Args:
            days_back: Number of days of historical data to export

        Returns:
            Export result summary
        """
        try:
            self._ensure_dataset()

            # Calculate date range
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            ga_service = self.ads_client.get_service("GoogleAdsService")

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    campaign.advertising_channel_type,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc,
                    segments.date
                FROM campaign
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY segments.date DESC
            """

            # Query all client accounts
            rows = []
            errors = []

            for customer_id in self.client_accounts:
                try:
                    response = ga_service.search(customer_id=customer_id, query=query)
                    for row in response:
                        rows.append({
                            "date": row.segments.date,
                            "customer_id": customer_id,
                            "campaign_id": str(row.campaign.id),
                            "campaign_name": row.campaign.name,
                            "campaign_status": row.campaign.status.name,
                            "channel_type": row.campaign.advertising_channel_type.name,
                            "impressions": row.metrics.impressions,
                            "clicks": row.metrics.clicks,
                            "cost": row.metrics.cost_micros / 1_000_000,
                            "conversions": row.metrics.conversions,
                            "conversions_value": row.metrics.conversions_value,
                            "ctr": row.metrics.ctr,
                            "avg_cpc": row.metrics.average_cpc / 1_000_000,
                            "exported_at": datetime.utcnow().isoformat(),
                        })
                    logger.info(f"Exported campaigns from account {customer_id}")
                except GoogleAdsException as e:
                    error_msg = f"Account {customer_id}: {str(e)[:100]}"
                    errors.append(error_msg)
                    logger.warning(f"Skipping account {customer_id}: {e}")
                    continue

            if rows:
                table_id = f"{self.project_id}.{self.dataset_id}.campaign_performance"
                await self._write_to_bigquery(table_id, rows, self._campaign_schema())

            return {
                "success": len(rows) > 0 or len(errors) == 0,
                "table": "campaign_performance",
                "rows_exported": len(rows),
                "date_range": f"{start_date} to {end_date}",
                "accounts_processed": len(self.client_accounts),
                "errors": errors if errors else None,
            }

        except GoogleAdsException as e:
            logger.error("Google Ads API error", error=str(e))
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error("Export error", error=str(e))
            return {"success": False, "error": str(e)}

    async def export_keyword_performance(self, days_back: int = 30) -> dict[str, Any]:
        """Export keyword performance data to BigQuery."""
        try:
            self._ensure_dataset()

            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            ga_service = self.ads_client.get_service("GoogleAdsService")

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    ad_group.id,
                    ad_group.name,
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc,
                    segments.date
                FROM keyword_view
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY metrics.impressions DESC
            """

            rows = []
            errors = []

            for customer_id in self.client_accounts:
                try:
                    response = ga_service.search(customer_id=customer_id, query=query)
                    for row in response:
                        rows.append({
                            "date": row.segments.date,
                            "customer_id": customer_id,
                            "campaign_id": str(row.campaign.id),
                            "campaign_name": row.campaign.name,
                            "ad_group_id": str(row.ad_group.id),
                            "ad_group_name": row.ad_group.name,
                            "keyword": row.ad_group_criterion.keyword.text,
                            "match_type": row.ad_group_criterion.keyword.match_type.name,
                            "impressions": row.metrics.impressions,
                            "clicks": row.metrics.clicks,
                            "cost": row.metrics.cost_micros / 1_000_000,
                            "conversions": row.metrics.conversions,
                            "ctr": row.metrics.ctr,
                            "avg_cpc": row.metrics.average_cpc / 1_000_000,
                            "exported_at": datetime.utcnow().isoformat(),
                        })
                    logger.info(f"Exported keywords from account {customer_id}")
                except GoogleAdsException as e:
                    errors.append(f"Account {customer_id}: {str(e)[:100]}")
                    logger.warning(f"Skipping keywords for account {customer_id}: {e}")
                    continue

            if rows:
                table_id = f"{self.project_id}.{self.dataset_id}.keyword_performance"
                await self._write_to_bigquery(table_id, rows, self._keyword_schema())

            return {
                "success": len(rows) > 0 or len(errors) == 0,
                "table": "keyword_performance",
                "rows_exported": len(rows),
                "date_range": f"{start_date} to {end_date}",
                "errors": errors if errors else None,
            }

        except GoogleAdsException as e:
            logger.error("Google Ads API error", error=str(e))
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error("Export error", error=str(e))
            return {"success": False, "error": str(e)}

    async def export_search_terms(self, days_back: int = 30) -> dict[str, Any]:
        """Export search terms report to BigQuery."""
        try:
            self._ensure_dataset()

            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            ga_service = self.ads_client.get_service("GoogleAdsService")

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    ad_group.id,
                    ad_group.name,
                    search_term_view.search_term,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    segments.date
                FROM search_term_view
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY metrics.impressions DESC
                LIMIT 5000
            """

            rows = []
            errors = []

            for customer_id in self.client_accounts:
                try:
                    response = ga_service.search(customer_id=customer_id, query=query)
                    for row in response:
                        rows.append({
                            "date": row.segments.date,
                            "customer_id": customer_id,
                            "campaign_id": str(row.campaign.id),
                            "campaign_name": row.campaign.name,
                            "ad_group_id": str(row.ad_group.id),
                            "ad_group_name": row.ad_group.name,
                            "search_term": row.search_term_view.search_term,
                            "impressions": row.metrics.impressions,
                            "clicks": row.metrics.clicks,
                            "cost": row.metrics.cost_micros / 1_000_000,
                            "conversions": row.metrics.conversions,
                            "exported_at": datetime.utcnow().isoformat(),
                        })
                    logger.info(f"Exported search terms from account {customer_id}")
                except GoogleAdsException as e:
                    errors.append(f"Account {customer_id}: {str(e)[:100]}")
                    logger.warning(f"Skipping search terms for account {customer_id}: {e}")
                    continue

            if rows:
                table_id = f"{self.project_id}.{self.dataset_id}.search_terms"
                await self._write_to_bigquery(table_id, rows, self._search_terms_schema())

            return {
                "success": len(rows) > 0 or len(errors) == 0,
                "table": "search_terms",
                "rows_exported": len(rows),
                "date_range": f"{start_date} to {end_date}",
                "errors": errors if errors else None,
            }

        except GoogleAdsException as e:
            logger.error("Google Ads API error", error=str(e))
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error("Export error", error=str(e))
            return {"success": False, "error": str(e)}

    async def export_ad_group_performance(self, days_back: int = 30) -> dict[str, Any]:
        """Export ad group performance data to BigQuery."""
        try:
            self._ensure_dataset()
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            ga_service = self.ads_client.get_service("GoogleAdsService")
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.type,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    metrics.average_cpc,
                    segments.date
                FROM ad_group
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY metrics.impressions DESC
            """

            rows = []
            for customer_id in self.client_accounts:
                try:
                    response = ga_service.search(customer_id=customer_id, query=query)
                    for row in response:
                        rows.append({
                            "date": row.segments.date,
                            "customer_id": customer_id,
                            "campaign_id": str(row.campaign.id),
                            "campaign_name": row.campaign.name,
                            "ad_group_id": str(row.ad_group.id),
                            "ad_group_name": row.ad_group.name,
                            "ad_group_status": row.ad_group.status.name,
                            "ad_group_type": row.ad_group.type_.name,
                            "impressions": row.metrics.impressions,
                            "clicks": row.metrics.clicks,
                            "cost": row.metrics.cost_micros / 1_000_000,
                            "conversions": row.metrics.conversions,
                            "ctr": row.metrics.ctr,
                            "avg_cpc": row.metrics.average_cpc / 1_000_000,
                            "exported_at": datetime.utcnow().isoformat(),
                        })
                except GoogleAdsException:
                    continue

            if rows:
                table_id = f"{self.project_id}.{self.dataset_id}.ad_group_performance"
                await self._write_to_bigquery(table_id, rows, self._ad_group_schema())

            return {"success": True, "table": "ad_group_performance", "rows_exported": len(rows)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def export_geographic_performance(self, days_back: int = 30) -> dict[str, Any]:
        """Export geographic performance data to BigQuery."""
        try:
            self._ensure_dataset()
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            ga_service = self.ads_client.get_service("GoogleAdsService")
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    geographic_view.country_criterion_id,
                    geographic_view.location_type,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    segments.date
                FROM geographic_view
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY metrics.impressions DESC
                LIMIT 1000
            """

            rows = []
            for customer_id in self.client_accounts:
                try:
                    response = ga_service.search(customer_id=customer_id, query=query)
                    for row in response:
                        rows.append({
                            "date": row.segments.date,
                            "customer_id": customer_id,
                            "campaign_id": str(row.campaign.id),
                            "campaign_name": row.campaign.name,
                            "country_id": str(row.geographic_view.country_criterion_id),
                            "location_type": row.geographic_view.location_type.name,
                            "impressions": row.metrics.impressions,
                            "clicks": row.metrics.clicks,
                            "cost": row.metrics.cost_micros / 1_000_000,
                            "conversions": row.metrics.conversions,
                            "exported_at": datetime.utcnow().isoformat(),
                        })
                except GoogleAdsException:
                    continue

            if rows:
                table_id = f"{self.project_id}.{self.dataset_id}.geographic_performance"
                await self._write_to_bigquery(table_id, rows, self._geographic_schema())

            return {"success": True, "table": "geographic_performance", "rows_exported": len(rows)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def export_device_performance(self, days_back: int = 30) -> dict[str, Any]:
        """Export device performance data to BigQuery."""
        try:
            self._ensure_dataset()
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            ga_service = self.ads_client.get_service("GoogleAdsService")
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    segments.device,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.ctr,
                    segments.date
                FROM campaign
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            """

            rows = []
            for customer_id in self.client_accounts:
                try:
                    response = ga_service.search(customer_id=customer_id, query=query)
                    for row in response:
                        rows.append({
                            "date": row.segments.date,
                            "customer_id": customer_id,
                            "campaign_id": str(row.campaign.id),
                            "campaign_name": row.campaign.name,
                            "device": row.segments.device.name,
                            "impressions": row.metrics.impressions,
                            "clicks": row.metrics.clicks,
                            "cost": row.metrics.cost_micros / 1_000_000,
                            "conversions": row.metrics.conversions,
                            "ctr": row.metrics.ctr,
                            "exported_at": datetime.utcnow().isoformat(),
                        })
                except GoogleAdsException:
                    continue

            if rows:
                table_id = f"{self.project_id}.{self.dataset_id}.device_performance"
                await self._write_to_bigquery(table_id, rows, self._device_schema())

            return {"success": True, "table": "device_performance", "rows_exported": len(rows)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def export_hourly_performance(self, days_back: int = 30) -> dict[str, Any]:
        """Export hourly performance data to BigQuery."""
        try:
            self._ensure_dataset()
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

            ga_service = self.ads_client.get_service("GoogleAdsService")
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    segments.hour,
                    segments.day_of_week,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    segments.date
                FROM campaign
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            """

            rows = []
            for customer_id in self.client_accounts:
                try:
                    response = ga_service.search(customer_id=customer_id, query=query)
                    for row in response:
                        rows.append({
                            "date": row.segments.date,
                            "customer_id": customer_id,
                            "campaign_id": str(row.campaign.id),
                            "campaign_name": row.campaign.name,
                            "hour": row.segments.hour,
                            "day_of_week": row.segments.day_of_week.name,
                            "impressions": row.metrics.impressions,
                            "clicks": row.metrics.clicks,
                            "cost": row.metrics.cost_micros / 1_000_000,
                            "conversions": row.metrics.conversions,
                            "exported_at": datetime.utcnow().isoformat(),
                        })
                except GoogleAdsException:
                    continue

            if rows:
                table_id = f"{self.project_id}.{self.dataset_id}.hourly_performance"
                await self._write_to_bigquery(table_id, rows, self._hourly_schema())

            return {"success": True, "table": "hourly_performance", "rows_exported": len(rows)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def export_all(self, days_back: int = 30) -> dict[str, Any]:
        """Export all Google Ads data to BigQuery."""
        if not self.client_accounts:
            return {
                "success": False,
                "error": "No client accounts configured. Set GOOGLE_ADS_CLIENT_ACCOUNTS env var.",
                "hint": "Example: GOOGLE_ADS_CLIENT_ACCOUNTS=9375199963,2102656007",
            }

        results = {
            "campaigns": await self.export_campaign_performance(days_back),
            "keywords": await self.export_keyword_performance(days_back),
            "search_terms": await self.export_search_terms(days_back),
            "ad_groups": await self.export_ad_group_performance(days_back),
            "geographic": await self.export_geographic_performance(days_back),
            "devices": await self.export_device_performance(days_back),
            "hourly": await self.export_hourly_performance(days_back),
        }

        total_rows = sum(
            r.get("rows_exported", 0) for r in results.values() if r.get("success")
        )

        return {
            "success": any(r.get("success") for r in results.values()),
            "total_rows_exported": total_rows,
            "client_accounts": self.client_accounts,
            "tables_created": len([r for r in results.values() if r.get("success")]),
            "details": results,
        }

    async def _write_to_bigquery(
        self,
        table_id: str,
        rows: list[dict],
        schema: list[bigquery.SchemaField]
    ) -> None:
        """Write rows to BigQuery table."""
        job_config = bigquery.LoadJobConfig(
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        job = self.bq_client.load_table_from_json(
            rows,
            table_id,
            job_config=job_config,
        )
        job.result()  # Wait for completion

        logger.info("Data written to BigQuery", table=table_id, rows=len(rows))

    def _campaign_schema(self) -> list[bigquery.SchemaField]:
        """Schema for campaign performance table."""
        return [
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("campaign_id", "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("campaign_status", "STRING"),
            bigquery.SchemaField("channel_type", "STRING"),
            bigquery.SchemaField("impressions", "INTEGER"),
            bigquery.SchemaField("clicks", "INTEGER"),
            bigquery.SchemaField("cost", "FLOAT"),
            bigquery.SchemaField("conversions", "FLOAT"),
            bigquery.SchemaField("conversions_value", "FLOAT"),
            bigquery.SchemaField("ctr", "FLOAT"),
            bigquery.SchemaField("avg_cpc", "FLOAT"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]

    def _keyword_schema(self) -> list[bigquery.SchemaField]:
        """Schema for keyword performance table."""
        return [
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("campaign_id", "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("ad_group_id", "STRING"),
            bigquery.SchemaField("ad_group_name", "STRING"),
            bigquery.SchemaField("keyword", "STRING"),
            bigquery.SchemaField("match_type", "STRING"),
            bigquery.SchemaField("impressions", "INTEGER"),
            bigquery.SchemaField("clicks", "INTEGER"),
            bigquery.SchemaField("cost", "FLOAT"),
            bigquery.SchemaField("conversions", "FLOAT"),
            bigquery.SchemaField("ctr", "FLOAT"),
            bigquery.SchemaField("avg_cpc", "FLOAT"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]

    def _search_terms_schema(self) -> list[bigquery.SchemaField]:
        """Schema for search terms table."""
        return [
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("campaign_id", "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("ad_group_id", "STRING"),
            bigquery.SchemaField("ad_group_name", "STRING"),
            bigquery.SchemaField("search_term", "STRING"),
            bigquery.SchemaField("impressions", "INTEGER"),
            bigquery.SchemaField("clicks", "INTEGER"),
            bigquery.SchemaField("cost", "FLOAT"),
            bigquery.SchemaField("conversions", "FLOAT"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]

    def _ad_group_schema(self) -> list[bigquery.SchemaField]:
        """Schema for ad group performance table."""
        return [
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("campaign_id", "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("ad_group_id", "STRING"),
            bigquery.SchemaField("ad_group_name", "STRING"),
            bigquery.SchemaField("ad_group_status", "STRING"),
            bigquery.SchemaField("ad_group_type", "STRING"),
            bigquery.SchemaField("impressions", "INTEGER"),
            bigquery.SchemaField("clicks", "INTEGER"),
            bigquery.SchemaField("cost", "FLOAT"),
            bigquery.SchemaField("conversions", "FLOAT"),
            bigquery.SchemaField("ctr", "FLOAT"),
            bigquery.SchemaField("avg_cpc", "FLOAT"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]

    def _geographic_schema(self) -> list[bigquery.SchemaField]:
        """Schema for geographic performance table."""
        return [
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("campaign_id", "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("country_id", "STRING"),
            bigquery.SchemaField("location_type", "STRING"),
            bigquery.SchemaField("impressions", "INTEGER"),
            bigquery.SchemaField("clicks", "INTEGER"),
            bigquery.SchemaField("cost", "FLOAT"),
            bigquery.SchemaField("conversions", "FLOAT"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]

    def _device_schema(self) -> list[bigquery.SchemaField]:
        """Schema for device performance table."""
        return [
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("campaign_id", "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("device", "STRING"),
            bigquery.SchemaField("impressions", "INTEGER"),
            bigquery.SchemaField("clicks", "INTEGER"),
            bigquery.SchemaField("cost", "FLOAT"),
            bigquery.SchemaField("conversions", "FLOAT"),
            bigquery.SchemaField("ctr", "FLOAT"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]

    def _hourly_schema(self) -> list[bigquery.SchemaField]:
        """Schema for hourly performance table."""
        return [
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("customer_id", "STRING"),
            bigquery.SchemaField("campaign_id", "STRING"),
            bigquery.SchemaField("campaign_name", "STRING"),
            bigquery.SchemaField("hour", "INTEGER"),
            bigquery.SchemaField("day_of_week", "STRING"),
            bigquery.SchemaField("impressions", "INTEGER"),
            bigquery.SchemaField("clicks", "INTEGER"),
            bigquery.SchemaField("cost", "FLOAT"),
            bigquery.SchemaField("conversions", "FLOAT"),
            bigquery.SchemaField("exported_at", "TIMESTAMP"),
        ]


def get_ads_exporter() -> AdsTooBigQueryExporter | None:
    """Get Ads to BigQuery exporter instance."""
    try:
        if not settings.google_ads_developer_token:
            logger.warning("Google Ads not configured - missing developer token")
            return None
        return AdsTooBigQueryExporter()
    except Exception as e:
        logger.error("Failed to initialize Ads exporter", error=str(e))
        return None
