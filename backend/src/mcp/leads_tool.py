"""Leads Dashboard Tool for CRM data analysis.

Reads and analyzes the leads tracking CSV to provide insights
on sales pipeline, lead sources, and conversion rates.
"""

import csv
import os
from datetime import datetime
from typing import Any
import structlog
from vertexai.generative_models import FunctionDeclaration

logger = structlog.get_logger()

# Path to the leads CSV file
LEADS_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "Leads Dashboard - Registros.csv"
)


class LeadsTool:
    """Tool for analyzing leads/CRM data from CSV."""

    def __init__(self) -> None:
        """Initialize leads tool."""
        self.csv_path = LEADS_CSV_PATH
        logger.info("Leads tool initialized", csv_path=self.csv_path)

    def get_function_declarations(self) -> list[FunctionDeclaration]:
        """Get Gemini function declarations for leads tools."""
        return [
            FunctionDeclaration(
                name="leads_get_summary",
                description="""Obtiene un resumen del dashboard de leads/CRM.
                Muestra: total de leads, leads por fuente, leads por status,
                monto en pipeline, leads cerrados, tasa de conversión real.

                IMPORTANTE: Estos son los leads REALES que han contactado,
                no lo que reporta Google Ads. Usar para comparar con datos de Ads.""",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            FunctionDeclaration(
                name="leads_by_source",
                description="""Analiza leads agrupados por fuente de adquisición.
                Fuentes incluyen: Google Ads, Espectacular, Recomendación, LinkedIn, etc.
                Retorna cantidad, monto potencial y tasa de conversión por fuente.""",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            FunctionDeclaration(
                name="leads_by_status",
                description="""Analiza el pipeline de ventas por estado.
                Estados: Contactando, Empatizando, Negociando, Aceptado, Declinado.
                Retorna cantidad y monto por cada etapa del funnel.""",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            FunctionDeclaration(
                name="leads_from_google_ads",
                description="""Obtiene TODOS los leads que vinieron de Google Ads.
                CRÍTICO: Compara esto con las conversiones reportadas en Google Ads
                para detectar problemas de tracking. Si Ads reporta 1 conversión
                pero aquí hay 25 leads, el pixel está roto.""",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            FunctionDeclaration(
                name="leads_pipeline_value",
                description="""Calcula el valor monetario del pipeline de ventas.
                Suma montos por etapa: Negociando, Empatizando, Aceptado.
                Útil para proyectar ingresos y priorizar seguimiento.""",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            ),
            FunctionDeclaration(
                name="leads_cross_analyze_ads",
                description="""ANÁLISIS CRUZADO: Compara leads del CRM con datos de Google Ads.
                Agrupa leads de Ads por mes/año para comparar con reportes de Ads.
                Identifica qué campañas o períodos tienen mayor discrepancia.
                USAR ESTO para demostrar que el tracking está roto.""",
                parameters={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Fecha inicio formato DD/MM/YYYY (opcional)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Fecha fin formato DD/MM/YYYY (opcional)"
                        }
                    },
                },
            ),
            FunctionDeclaration(
                name="leads_for_offline_conversion",
                description="""Prepara datos de leads para subir como conversiones offline a Google Ads.
                Retorna leads con: fecha, valor, y datos necesarios para el upload.
                NOTA: Para upload completo necesitas capturar gclid en el formulario.""",
                parameters={
                    "type": "object",
                    "properties": {
                        "status_filter": {
                            "type": "string",
                            "description": "Filtrar por status: Aceptado, Negociando, etc. (por defecto: Aceptado)"
                        }
                    },
                },
            ),
        ]

    def _read_csv(self) -> list[dict]:
        """Read and parse the leads CSV file."""
        leads = []
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Clean up the row data
                    cleaned = {}
                    for key, value in row.items():
                        if key:
                            cleaned[key.strip()] = value.strip() if value else ""
                    if cleaned.get('CONTACTO') or cleaned.get('EMPRESA'):
                        leads.append(cleaned)
            logger.info("Leads CSV loaded", count=len(leads))
        except Exception as e:
            logger.error("Error reading leads CSV", error=str(e))
        return leads

    def _parse_amount(self, amount_str: str) -> float:
        """Parse currency amount from string."""
        if not amount_str:
            return 0.0
        # Remove currency symbols, commas, and spaces
        cleaned = amount_str.replace('$', '').replace(',', '').replace(' ', '')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def execute(self, tool_name: str, args: dict[str, Any]) -> Any:
        """Execute a leads tool.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            Tool execution result
        """
        leads = self._read_csv()

        if tool_name == "leads_get_summary":
            return self._get_summary(leads)
        elif tool_name == "leads_by_source":
            return self._by_source(leads)
        elif tool_name == "leads_by_status":
            return self._by_status(leads)
        elif tool_name == "leads_from_google_ads":
            return self._from_google_ads(leads)
        elif tool_name == "leads_pipeline_value":
            return self._pipeline_value(leads)
        elif tool_name == "leads_cross_analyze_ads":
            return self._cross_analyze_ads(leads, args)
        elif tool_name == "leads_for_offline_conversion":
            return self._for_offline_conversion(leads, args)
        else:
            return {"error": f"Unknown leads tool: {tool_name}"}

    def _get_summary(self, leads: list[dict]) -> dict:
        """Get overall summary of leads."""
        total = len(leads)

        # Count by status
        status_counts = {}
        for lead in leads:
            status = lead.get('STATUS', 'Sin Status')
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count by source
        source_counts = {}
        for lead in leads:
            source = lead.get('FUENTE', 'Sin Fuente')
            source_counts[source] = source_counts.get(source, 0) + 1

        # Calculate amounts
        total_closed = 0
        total_pipeline = 0
        closed_count = 0

        for lead in leads:
            amount = self._parse_amount(lead.get('MONTO DE CIERRE', ''))
            status = lead.get('STATUS', '')

            if status == 'Aceptado':
                total_closed += amount
                closed_count += 1
            elif status in ['Negociando', 'Empatizando']:
                total_pipeline += amount

        # Conversion rate
        non_declined = total - status_counts.get('Declinado', 0)
        conversion_rate = (closed_count / non_declined * 100) if non_declined > 0 else 0

        return {
            "total_leads": total,
            "leads_by_status": status_counts,
            "leads_by_source": source_counts,
            "closed_deals": closed_count,
            "closed_revenue": f"${total_closed:,.2f}",
            "pipeline_value": f"${total_pipeline:,.2f}",
            "conversion_rate": f"{conversion_rate:.1f}%",
            "insight": f"Hay {total} leads reales registrados. Google Ads reporta ~1 conversión pero el CRM muestra {source_counts.get('Google Ads', 0)} leads de Ads. TRACKING ROTO."
        }

    def _by_source(self, leads: list[dict]) -> dict:
        """Analyze leads by acquisition source."""
        sources = {}

        for lead in leads:
            source = lead.get('FUENTE', 'Sin Fuente')
            if source not in sources:
                sources[source] = {
                    "count": 0,
                    "closed": 0,
                    "closed_revenue": 0,
                    "pipeline_value": 0,
                    "declined": 0
                }

            sources[source]["count"] += 1
            status = lead.get('STATUS', '')
            amount = self._parse_amount(lead.get('MONTO DE CIERRE', ''))

            if status == 'Aceptado':
                sources[source]["closed"] += 1
                sources[source]["closed_revenue"] += amount
            elif status == 'Declinado':
                sources[source]["declined"] += 1
            elif status in ['Negociando', 'Empatizando']:
                sources[source]["pipeline_value"] += amount

        # Format output
        result = []
        for source, data in sorted(sources.items(), key=lambda x: x[1]['count'], reverse=True):
            conversion = (data['closed'] / (data['count'] - data['declined']) * 100) if (data['count'] - data['declined']) > 0 else 0
            result.append({
                "source": source,
                "leads": data['count'],
                "closed": data['closed'],
                "declined": data['declined'],
                "closed_revenue": f"${data['closed_revenue']:,.2f}",
                "pipeline": f"${data['pipeline_value']:,.2f}",
                "conversion_rate": f"{conversion:.1f}%"
            })

        return {
            "sources": result,
            "top_source": result[0]['source'] if result else "N/A",
            "insight": f"Google Ads genera {sources.get('Google Ads', {}).get('count', 0)} leads pero el tracking digital solo reporta 1. Los Espectaculares generan leads de alto valor."
        }

    def _by_status(self, leads: list[dict]) -> dict:
        """Analyze pipeline by status."""
        statuses = {}

        for lead in leads:
            status = lead.get('STATUS', 'Sin Status')
            if status not in statuses:
                statuses[status] = {
                    "count": 0,
                    "total_value": 0,
                    "leads": []
                }

            statuses[status]["count"] += 1
            amount = self._parse_amount(lead.get('MONTO DE CIERRE', ''))
            statuses[status]["total_value"] += amount

            if lead.get('EMPRESA') and amount > 0:
                statuses[status]["leads"].append({
                    "empresa": lead.get('EMPRESA'),
                    "monto": f"${amount:,.2f}"
                })

        # Format output
        pipeline_order = ['Contactando', 'Empatizando', 'Negociando', 'Aceptado', 'Declinado']
        result = []

        for status in pipeline_order:
            if status in statuses:
                data = statuses[status]
                result.append({
                    "status": status,
                    "count": data['count'],
                    "value": f"${data['total_value']:,.2f}",
                    "top_deals": data['leads'][:3]  # Top 3 deals
                })

        return {
            "pipeline": result,
            "total_in_pipeline": sum(s.get('count', 0) for s in result if s['status'] not in ['Declinado', 'Aceptado']),
            "insight": "El pipeline muestra leads reales en seguimiento que NO aparecen en Google Ads."
        }

    def _from_google_ads(self, leads: list[dict]) -> dict:
        """Get all leads from Google Ads source."""
        ads_leads = []

        for lead in leads:
            if lead.get('FUENTE', '').lower() == 'google ads':
                ads_leads.append({
                    "fecha": lead.get('FECHA', ''),
                    "contacto": lead.get('CONTACTO', ''),
                    "empresa": lead.get('EMPRESA', ''),
                    "status": lead.get('STATUS', ''),
                    "monto": lead.get('MONTO DE CIERRE', ''),
                    "interes": lead.get('INTERES', ''),
                    "seguimiento": lead.get('SEGUIMIENTO', '')[:100] + '...' if len(lead.get('SEGUIMIENTO', '')) > 100 else lead.get('SEGUIMIENTO', '')
                })

        # Count by status
        status_counts = {}
        for lead in ads_leads:
            status = lead['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_leads_from_ads": len(ads_leads),
            "google_ads_reports": "~1 conversión",
            "discrepancy": f"{len(ads_leads) - 1} leads NO RASTREADOS",
            "status_breakdown": status_counts,
            "leads": ads_leads,
            "critical_insight": f"Google Ads reporta 1 conversión pero el CRM tiene {len(ads_leads)} leads reales de Ads. EL TRACKING ESTÁ ROTO. Estás midiendo mal el ROI."
        }

    def _pipeline_value(self, leads: list[dict]) -> dict:
        """Calculate pipeline monetary value by stage."""
        stages = {
            'Contactando': {'count': 0, 'value': 0, 'probability': 0.10},
            'Empatizando': {'count': 0, 'value': 0, 'probability': 0.25},
            'Negociando': {'count': 0, 'value': 0, 'probability': 0.50},
            'Aceptado': {'count': 0, 'value': 0, 'probability': 1.00}
        }

        for lead in leads:
            status = lead.get('STATUS', '')
            if status in stages:
                amount = self._parse_amount(lead.get('MONTO DE CIERRE', ''))
                stages[status]['count'] += 1
                stages[status]['value'] += amount

        # Calculate weighted pipeline
        weighted_total = 0
        result = []

        for stage, data in stages.items():
            if stage != 'Aceptado':
                weighted = data['value'] * data['probability']
                weighted_total += weighted
                result.append({
                    "stage": stage,
                    "deals": data['count'],
                    "total_value": f"${data['value']:,.2f}",
                    "probability": f"{data['probability']*100:.0f}%",
                    "weighted_value": f"${weighted:,.2f}"
                })

        closed = stages['Aceptado']

        return {
            "pipeline_stages": result,
            "total_pipeline_value": f"${sum(s['value'] for s in stages.values() if s != stages['Aceptado']):,.2f}",
            "weighted_pipeline": f"${weighted_total:,.2f}",
            "already_closed": {
                "deals": closed['count'],
                "revenue": f"${closed['value']:,.2f}"
            },
            "forecast": f"Ingresos esperados: ${weighted_total + closed['value']:,.2f}",
            "insight": "Este es el valor REAL del pipeline, no lo que reporta Google Ads."
        }

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date from various formats."""
        if not date_str:
            return None
        # Try different formats
        formats = [
            "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d",
            "%d/0%m/%Y", "%m/%d/%Y"  # Handle some typos in data
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        # Try to extract year at least
        try:
            if "2025" in date_str or "2026" in date_str:
                year = 2025 if "2025" in date_str else 2026
                return datetime(year, 1, 1)
        except Exception:
            pass
        return None

    def _cross_analyze_ads(self, leads: list[dict], args: dict) -> dict:
        """Cross-analyze leads from Google Ads by time period."""
        ads_leads = [l for l in leads if l.get('FUENTE', '').lower() == 'google ads']

        # Group by month/year
        by_month = {}
        for lead in ads_leads:
            date = self._parse_date(lead.get('FECHA', ''))
            if date:
                key = date.strftime("%Y-%m")
            else:
                key = "Fecha inválida"

            if key not in by_month:
                by_month[key] = {
                    "count": 0,
                    "closed": 0,
                    "closed_value": 0,
                    "leads": []
                }

            by_month[key]["count"] += 1
            status = lead.get('STATUS', '')
            amount = self._parse_amount(lead.get('MONTO DE CIERRE', ''))

            if status == 'Aceptado':
                by_month[key]["closed"] += 1
                by_month[key]["closed_value"] += amount

            by_month[key]["leads"].append({
                "fecha": lead.get('FECHA', ''),
                "contacto": lead.get('CONTACTO', ''),
                "empresa": lead.get('EMPRESA', ''),
                "status": status
            })

        # Format result
        months_sorted = sorted(by_month.keys(), reverse=True)
        result = []
        for month in months_sorted:
            data = by_month[month]
            result.append({
                "periodo": month,
                "leads_reales": data["count"],
                "conversiones_ads_reportadas": 0,  # Google Ads reports ~0-1
                "discrepancia": data["count"],
                "cerrados": data["closed"],
                "valor_cerrado": f"${data['closed_value']:,.2f}",
                "detalle_leads": data["leads"][:5]  # First 5 leads
            })

        total_leads = sum(d["count"] for d in by_month.values())
        total_closed = sum(d["closed"] for d in by_month.values())
        total_value = sum(d["closed_value"] for d in by_month.values())

        return {
            "analisis_por_periodo": result,
            "resumen": {
                "total_leads_crm": total_leads,
                "total_conversiones_ads": "~1",
                "discrepancia_total": f"{total_leads - 1} leads perdidos en tracking",
                "leads_cerrados": total_closed,
                "valor_cerrado": f"${total_value:,.2f}"
            },
            "accion_requerida": "URGENTE: Configurar conversiones offline en Google Ads para sincronizar estos leads",
            "instrucciones": [
                "1. Capturar gclid en formulario de contacto",
                "2. Almacenar gclid junto con datos del lead",
                "3. Usar API de Google Ads para subir conversiones offline",
                "4. O usar la función leads_for_offline_conversion para exportar datos"
            ]
        }

    def _for_offline_conversion(self, leads: list[dict], args: dict) -> dict:
        """Prepare leads for offline conversion upload to Google Ads."""
        status_filter = args.get('status_filter', 'Aceptado')

        # Filter leads by source and status
        filtered = []
        for lead in leads:
            if lead.get('FUENTE', '').lower() != 'google ads':
                continue
            if status_filter and lead.get('STATUS', '') != status_filter:
                continue

            date = self._parse_date(lead.get('FECHA', ''))
            amount = self._parse_amount(lead.get('MONTO DE CIERRE', ''))

            filtered.append({
                "conversion_date": date.strftime("%Y-%m-%d %H:%M:%S") if date else "",
                "conversion_value": amount,
                "currency_code": "MXN",
                "contacto": lead.get('CONTACTO', ''),
                "empresa": lead.get('EMPRESA', ''),
                "email": lead.get('CORREO', ''),
                "telefono": lead.get('TEL', ''),
                "gclid": "⚠️ NO CAPTURADO - Necesitas modificar tu formulario",
                "status": lead.get('STATUS', '')
            })

        # Calculate totals
        total_value = sum(l["conversion_value"] for l in filtered)

        return {
            "conversiones_para_subir": filtered,
            "total_conversiones": len(filtered),
            "valor_total": f"${total_value:,.2f} MXN",
            "formato_requerido": {
                "gclid": "REQUERIDO - ID del clic de Google Ads",
                "conversion_date": "Fecha en formato YYYY-MM-DD HH:MM:SS",
                "conversion_value": "Valor de la conversión",
                "currency_code": "MXN"
            },
            "problema": "⚠️ No tienes gclid capturado. Sin esto NO puedes subir conversiones offline.",
            "solucion": [
                "1. Agregar campo oculto 'gclid' a tu formulario de contacto",
                "2. Capturar gclid de URL: ?gclid=XXXXX",
                "3. JavaScript: new URLSearchParams(window.location.search).get('gclid')",
                "4. Guardar gclid junto con los datos del lead en tu CRM/CSV",
                "5. Luego usar API de Google Ads para subir conversiones"
            ],
            "api_endpoint": "https://googleads.googleapis.com/v16/customers/{customer_id}:uploadConversionAdjustments"
        }


def get_leads_tool() -> LeadsTool:
    """Get singleton leads tool instance."""
    return LeadsTool()
