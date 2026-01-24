"""CSV to BigQuery Upload Tool.

Uploads CSV files containing prospect/lead data to BigQuery
with proper schema definition, encoding handling, and optimization.
"""

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Any
import structlog
from google.cloud import bigquery
from google.api_core.exceptions import NotFound, Conflict

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class CSVToBigQueryUploader:
    """Uploads CSV data to BigQuery with proper schema and optimization."""

    def __init__(self) -> None:
        """Initialize the uploader."""
        self.project_id = settings.gcp_project_id
        self.client = bigquery.Client(project=self.project_id)
        logger.info("CSVToBigQueryUploader initialized", project_id=self.project_id)

    def _ensure_dataset(self, dataset_id: str) -> None:
        """Ensure BigQuery dataset exists."""
        dataset_ref = f"{self.project_id}.{dataset_id}"
        try:
            self.client.get_dataset(dataset_ref)
            logger.info("Dataset exists", dataset=dataset_ref)
        except NotFound:
            try:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                self.client.create_dataset(dataset)
                logger.info("Created dataset", dataset=dataset_ref)
            except Conflict:
                logger.info("Dataset already exists")

    def _get_industrial_clients_schema(self) -> list[bigquery.SchemaField]:
        """Schema for industrial clients/prospects table."""
        return [
            bigquery.SchemaField("email", "STRING", description="Contact email"),
            bigquery.SchemaField("phone", "STRING", description="Phone number"),
            bigquery.SchemaField("first_name", "STRING", description="First name"),
            bigquery.SchemaField("last_name", "STRING", description="Last name"),
            bigquery.SchemaField("company_name", "STRING", description="Company name"),
            bigquery.SchemaField("country", "STRING", description="Country"),
            bigquery.SchemaField("city", "STRING", description="City"),
            bigquery.SchemaField("state", "STRING", description="State/Province"),
            bigquery.SchemaField("zip_code", "STRING", description="ZIP/Postal code"),
            bigquery.SchemaField("segment", "STRING", description="Business segment"),
            bigquery.SchemaField("source_file", "STRING", description="Source CSV file"),
            bigquery.SchemaField("uploaded_at", "TIMESTAMP", description="Upload timestamp"),
        ]

    def _get_contractors_schema(self) -> list[bigquery.SchemaField]:
        """Schema for contractors/third-party table."""
        return [
            bigquery.SchemaField("company_name", "STRING", description="Company name"),
            bigquery.SchemaField("rfc", "STRING", description="RFC tax ID"),
            bigquery.SchemaField("representative_name", "STRING", description="Legal representative"),
            bigquery.SchemaField("representative_email", "STRING", description="Representative email"),
            bigquery.SchemaField("work_type", "STRING", description="Type of work"),
            bigquery.SchemaField("contractor_type", "STRING", description="Contractor classification"),
            bigquery.SchemaField("risk_level", "STRING", description="Risk level"),
            bigquery.SchemaField("cedis", "STRING", description="CEDIS location"),
            bigquery.SchemaField("active_projects", "INTEGER", description="Active projects count"),
            bigquery.SchemaField("workers_count", "INTEGER", description="Number of workers"),
            bigquery.SchemaField("repse_status", "STRING", description="REPSE compliance status"),
            bigquery.SchemaField("documents_status", "STRING", description="Documentation status"),
            bigquery.SchemaField("imss_status", "STRING", description="IMSS compliance status"),
            bigquery.SchemaField("created_date", "DATE", description="Registration date"),
            bigquery.SchemaField("source_file", "STRING", description="Source CSV file"),
            bigquery.SchemaField("uploaded_at", "TIMESTAMP", description="Upload timestamp"),
        ]

    async def upload_industrial_clients(
        self,
        file_path: str,
        write_mode: str = "WRITE_TRUNCATE"
    ) -> dict[str, Any]:
        """Upload industrial clients CSV to BigQuery.

        Args:
            file_path: Path to the CSV file
            write_mode: WRITE_TRUNCATE (replace) or WRITE_APPEND (add)
        """
        try:
            dataset_id = "prospects_data"
            table_name = "industrial_clients"
            self._ensure_dataset(dataset_id)

            table_ref = f"{self.project_id}.{dataset_id}.{table_name}"

            # Read and transform CSV
            rows = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append({
                        "email": row.get("Email", "").strip() or None,
                        "phone": row.get("Phone", "").strip() or None,
                        "first_name": row.get("First Name", "").strip() or None,
                        "last_name": row.get("Last Name", "").strip() or None,
                        "company_name": row.get("Company Name", "").strip() or None,
                        "country": row.get("Country", "").strip() or None,
                        "city": row.get("City", "").strip() or None,
                        "state": row.get("State", "").strip() or None,
                        "zip_code": row.get("Zip", "").strip() or None,
                        "segment": row.get("Segmento Scram", "").strip() or None,
                        "source_file": Path(file_path).name,
                        "uploaded_at": datetime.utcnow().isoformat(),
                    })

            if not rows:
                return {"success": False, "error": "No data found in CSV"}

            # Create table with clustering
            schema = self._get_industrial_clients_schema()
            table = bigquery.Table(table_ref, schema=schema)
            table.clustering_fields = ["segment", "country"]

            try:
                self.client.create_table(table)
                logger.info("Created table", table=table_ref)
            except Conflict:
                pass  # Table exists

            # Upload data
            job_config = bigquery.LoadJobConfig(
                schema=schema,
                write_disposition=getattr(bigquery.WriteDisposition, write_mode),
            )

            job = self.client.load_table_from_json(rows, table_ref, job_config=job_config)
            job.result()

            # Get stats
            table = self.client.get_table(table_ref)

            # Count by segment
            query = f"""
                SELECT segment, COUNT(*) as count
                FROM `{table_ref}`
                GROUP BY segment
                ORDER BY count DESC
                LIMIT 10
            """
            segments = list(self.client.query(query).result())

            # Count by country
            query = f"""
                SELECT country, COUNT(*) as count
                FROM `{table_ref}`
                GROUP BY country
                ORDER BY count DESC
            """
            countries = list(self.client.query(query).result())

            return {
                "success": True,
                "table": table_ref,
                "rows_uploaded": len(rows),
                "total_rows": table.num_rows,
                "segments": [{"segment": r.segment, "count": r.count} for r in segments],
                "countries": [{"country": r.country, "count": r.count} for r in countries],
            }

        except Exception as e:
            logger.error("Upload failed", error=str(e))
            return {"success": False, "error": str(e)}

    async def upload_contractors(
        self,
        file_path: str,
        write_mode: str = "WRITE_TRUNCATE"
    ) -> dict[str, Any]:
        """Upload contractors/third-party CSV to BigQuery."""
        try:
            dataset_id = "prospects_data"
            table_name = "contractors"
            self._ensure_dataset(dataset_id)

            table_ref = f"{self.project_id}.{dataset_id}.{table_name}"

            # Read and transform CSV
            rows = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse integer fields safely
                    try:
                        active_projects = int(row.get("Proyectos En Proceso", 0) or 0)
                    except:
                        active_projects = 0

                    try:
                        workers = int(row.get("N° Trabajadores por empresa", 0) or 0)
                    except:
                        workers = 0

                    # Parse date
                    created_str = row.get("Creado", "")
                    created_date = None
                    if created_str:
                        try:
                            # Format: 28/12/25 01:34 p.m.
                            date_part = created_str.split()[0]
                            day, month, year = date_part.split("/")
                            created_date = f"20{year}-{month}-{day}"
                        except:
                            pass

                    rows.append({
                        "company_name": row.get("Nombre de empresa contratista y subcontratista", "").strip() or None,
                        "rfc": row.get("RFC", "").strip() or None,
                        "representative_name": row.get("Nombre y Apellidos del Representante de la Empresa", "").strip() or None,
                        "representative_email": row.get("Correo electronico del Representante Contratista", "").strip() or None,
                        "work_type": row.get("Tipo de Trabajo a Ejecutar", "").strip() or None,
                        "contractor_type": row.get("Tipo de Tercero", "").strip() or None,
                        "risk_level": row.get("ID Credencial correspondiente", "").strip() or None,
                        "cedis": row.get("CEDIS", "").strip() or None,
                        "active_projects": active_projects,
                        "workers_count": workers,
                        "repse_status": row.get("REPSE", "").strip() or None,
                        "documents_status": row.get("Documentos Generales", "").strip() or None,
                        "imss_status": row.get("Opinión de cumplimiento IMSS", "").strip() or None,
                        "created_date": created_date,
                        "source_file": Path(file_path).name,
                        "uploaded_at": datetime.utcnow().isoformat(),
                    })

            if not rows:
                return {"success": False, "error": "No data found in CSV"}

            # Create table
            schema = self._get_contractors_schema()
            table = bigquery.Table(table_ref, schema=schema)
            table.clustering_fields = ["contractor_type", "repse_status"]

            try:
                self.client.create_table(table)
            except Conflict:
                pass

            # Upload
            job_config = bigquery.LoadJobConfig(
                schema=schema,
                write_disposition=getattr(bigquery.WriteDisposition, write_mode),
            )

            job = self.client.load_table_from_json(rows, table_ref, job_config=job_config)
            job.result()

            table = self.client.get_table(table_ref)

            return {
                "success": True,
                "table": table_ref,
                "rows_uploaded": len(rows),
                "total_rows": table.num_rows,
            }

        except Exception as e:
            logger.error("Upload failed", error=str(e))
            return {"success": False, "error": str(e)}


def get_csv_uploader() -> CSVToBigQueryUploader | None:
    """Get CSV uploader instance."""
    try:
        return CSVToBigQueryUploader()
    except Exception as e:
        logger.error("Failed to init uploader", error=str(e))
        return None
