# Fase 3: Agente Autonomo e Inteligente

**Fecha:** 2026-01-25
**Version:** 3.0

---

## Resumen de Mejoras

Se implementaron capacidades avanzadas para hacer al agente:
1. **Mas Autonomo** - Explora y analiza datos proactivamente
2. **Mas Inteligente** - RAG mejorado con comprension semantica
3. **Conversacional por Voz** - Soporte para STT/TTS (preparado para futuro)

---

## Nuevos Archivos Creados

### 1. `backend/src/mcp/autonomous_agent.py`
**Capacidades de exploracion autonoma de datos**

```python
class DataDiscovery:
    """Descubrimiento automatico de datos en BigQuery."""
    async def discover_all_data()      # Explora todos los datasets/tablas
    async def get_data_context()       # Genera contexto para el modelo
    def _detect_relationships()        # Detecta relaciones entre tablas
    def _generate_recommendations()    # Sugiere analisis automaticamente

class QueryPlanner:
    """Planificador de queries multi-paso."""
    def plan_analysis(question, tables)  # Planifica queries basado en pregunta

class AutonomousAnalyzer:
    """Motor de analisis autonomo."""
    async def auto_analyze()            # Analisis completo automatico
    async def _analyze_google_ads()     # Analiza datos de Google Ads
    async def _analyze_prospects()      # Analiza datos de prospectos
    async def _cross_analyze()          # Cruza multiples fuentes
    async def _detect_anomalies()       # Detecta anomalias automaticamente
```

### 2. `backend/src/mcp/intelligent_agent.py`
**Agente con razonamiento mejorado**

```python
class ConversationContext:
    """Maneja contexto y memoria de conversacion."""
    def add_turn()                      # Agrega turno a la conversacion
    def extract_entities()              # Extrae entidades del texto
    def get_context_summary()           # Resume el contexto actual

class IntentClassifier:
    """Clasifica intenciones del usuario."""
    @classmethod
    def classify(text) -> list[(intent, confidence)]

class IntelligentAgent:
    """Agente con awareness de contexto."""
    async def preprocess_query()        # Preprocesa consultas
    async def generate_proactive_insights()  # Genera insights proactivos
    async def enhance_response()        # Mejora respuestas con contexto
```

### 3. `backend/src/services/audio_service.py`
**Servicio de voz (STT/TTS)**

```python
class AudioService:
    """Servicio para conversaciones por voz."""
    async def speech_to_text()          # Convierte audio a texto
    async def speech_to_text_streaming()  # STT en tiempo real
    async def text_to_speech()          # Convierte texto a audio
    def detect_language()               # Detecta idioma
```

### 4. `backend/src/api/v1/audio.py`
**Endpoints de API para audio**

```
POST /api/v1/audio/transcribe       # Transcribe archivo de audio
POST /api/v1/audio/transcribe/base64  # Transcribe audio en base64
POST /api/v1/audio/synthesize       # Sintetiza texto a voz
GET  /api/v1/audio/voices           # Lista voces disponibles
POST /api/v1/audio/conversation     # Turno completo de voz
GET  /api/v1/audio/health           # Estado del servicio de audio
```

---

## Nuevas Herramientas BigQuery

### `bq_discover_data`
Descubre AUTOMATICAMENTE todos los datos disponibles en BigQuery.

**Retorna:**
- Lista de datasets y tablas
- Esquema y columnas
- Valores de ejemplo
- Relaciones detectadas
- Analisis recomendados

### `bq_auto_analyze`
Realiza ANALISIS AUTONOMO completo:
1. Explora Google Ads
2. Analiza prospectos
3. Cruza datos de multiples fuentes
4. Detecta anomalias
5. Genera recomendaciones

**Ejemplo de uso:**
```
Usuario: "Como van mis campanas?"
Agente: [Usa bq_auto_analyze automaticamente]
        -> Analiza todo
        -> Detecta anomalias
        -> Genera recomendaciones
```

### `bq_smart_query`
Ejecuta consultas inteligentes en lenguaje natural:

```
Usuario: "Cuantos clientes estan en zonas con publicidad?"
Agente: [Usa bq_smart_query]
        -> Detecta tablas relevantes
        -> Encuentra columnas de JOIN
        -> Ejecuta cross-query
        -> Retorna analisis
```

---

## Clasificacion de Intenciones

El agente ahora clasifica automaticamente las intenciones:

| Intencion | Keywords | Herramientas Sugeridas |
|-----------|----------|------------------------|
| analysis_request | analiza, diagnostico | bq_auto_analyze |
| comparison | compara, vs, diferencia | bq_smart_query |
| trend_analysis | tendencia, evolucion | bq_run_query |
| problem_diagnosis | por que, problema, error | bq_auto_analyze |
| data_exploration | que datos, muestrame | bq_discover_data |
| recommendation | recomienda, mejora | bq_auto_analyze |

---

## Soporte de Voz (Futuro)

### Arquitectura
```
[Usuario habla]
    -> STT (Google Cloud Speech)
    -> Procesamiento AI (Gemini)
    -> Respuesta texto
    -> TTS (Google Cloud Text-to-Speech)
    -> [Usuario escucha]
```

### Voces Disponibles
- **es-MX-Neural2-A** - Espanol mexicano, femenino
- **es-MX-Neural2-B** - Espanol mexicano, masculino
- **en-US-Neural2-A** - Ingles americano, femenino
- **en-US-Neural2-D** - Ingles americano, masculino

### Ejemplo de Uso (API)
```bash
# Transcribir audio
curl -X POST http://localhost:8000/api/v1/audio/transcribe \
  -F "audio=@pregunta.wav" \
  -F "language_code=es-MX"

# Sintetizar respuesta
curl -X POST http://localhost:8000/api/v1/audio/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Las campanas van bien", "language_code": "es-MX"}'
```

---

## Dependencias Nuevas

```
# requirements.txt
google-cloud-speech>=2.24.0
google-cloud-texttospeech>=2.16.0
```

---

## Sistema Prompt Actualizado

El prompt del sistema ahora incluye:

1. **Herramientas Autonomas** como primera opcion
2. **Reglas de comportamiento autonomo**
3. **Exploracion proactiva** cuando no conoce los datos

```
HERRAMIENTAS AUTONOMAS (PREFERIR ESTAS):
- bq_discover_data - Descubre datos automaticamente
- bq_auto_analyze - Analisis autonomo completo
- bq_smart_query - Consultas en lenguaje natural

REGLAS:
6. COMPORTAMIENTO AUTONOMO: Para preguntas complejas,
   usa bq_auto_analyze automaticamente
7. EXPLORACION PROACTIVA: Si no sabes que datos existen,
   usa bq_discover_data para explorar
```

---

## Proximos Pasos

### Fase 4 (Planificado)
1. **Integracion WebSocket** para streaming de voz en tiempo real
2. **Wake word detection** ("Hola SCRAM")
3. **UI de voz** en el frontend React
4. **Memoria conversacional persistente** entre sesiones
5. **Aprendizaje de preferencias** del usuario

---

## Testing

### Probar herramientas autonomas
```bash
# En el chat
"Dame un analisis completo de todo"
-> Deberia usar bq_auto_analyze automaticamente

"Que datos tengo disponibles?"
-> Deberia usar bq_discover_data

"Cuantos clientes estan donde hacemos publicidad?"
-> Deberia usar bq_smart_query
```

### Probar API de audio
```bash
curl http://localhost:8000/api/v1/audio/health
curl http://localhost:8000/api/v1/audio/voices
```

---

*Documento generado por Claude AI - Fase 3*
