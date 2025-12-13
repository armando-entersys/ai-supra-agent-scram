# AI-SupraAgent

Agente de IA conversacional con RAG y herramientas MCP para Google Analytics 4.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         TRAEFIK (SSL)                           │
│                    ai.scram2k.com / api.ai.scram2k.com          │
└─────────────────────┬───────────────────────┬───────────────────┘
                      │                       │
          ┌───────────▼───────────┐ ┌────────▼────────┐
          │      FRONTEND         │ │     BACKEND     │
          │   React 19 + MUI      │ │  FastAPI + MCP  │
          │      (Nginx)          │ │   (Uvicorn)     │
          └───────────────────────┘ └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
          ┌─────────▼─────────┐   ┌─────────▼─────────┐   ┌─────────▼─────────┐
          │    PostgreSQL     │   │    Vertex AI      │   │   GA4 Data API    │
          │    + pgvector     │   │   (Embeddings)    │   │    (Analytics)    │
          └───────────────────┘   └───────────────────┘   └───────────────────┘
```

## Stack Tecnologico

| Capa | Tecnologia |
|------|------------|
| **Frontend** | React 19, Vite 6, MUI v6, TanStack Query, Zustand |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic V2 |
| **Database** | PostgreSQL 16 + pgvector |
| **AI/ML** | Vertex AI (text-embedding-004), Gemini 2.0 |
| **Infrastructure** | Docker Compose, Traefik, Let's Encrypt |

## Estructura del Proyecto

```
/srv/servicios/ai-supra-agent/
├── docker-compose.yml       # Orquestacion de servicios
├── .env                     # Variables de entorno (gitignored)
├── .env.example             # Template de configuracion
├── secrets/
│   └── gcp-sa-key.json      # Service Account GCP (gitignored)
├── scripts/
│   ├── deploy.sh            # Script de despliegue
│   ├── healthcheck.sh       # Verificacion de salud
│   └── backup-db.sh         # Backup de base de datos
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py          # FastAPI application
│       ├── config.py        # Pydantic Settings
│       ├── schemas/         # Request/Response models
│       ├── database/        # SQLAlchemy models
│       ├── api/v1/          # REST endpoints
│       ├── mcp/             # MCP tools (GA4, RAG)
│       └── rag/             # RAG pipeline
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── src/
        ├── App.tsx          # Main component
        ├── theme.ts         # SCRAM theme
        ├── components/      # UI components
        ├── containers/      # Smart components
        ├── hooks/           # Custom hooks
        └── services/        # API clients
```

## Requisitos Previos

1. **Docker & Docker Compose** v2.20+
2. **Red Docker Traefik** existente (`docker network create traefik`)
3. **Service Account de GCP** con permisos:
   - Analytics Data API (lectura)
   - Analytics Admin API (lectura)
   - Vertex AI API

## Instalacion

### 1. Clonar/Copiar proyecto

```bash
cd /srv/servicios/ai-supra-agent
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
nano .env  # Editar con valores reales
```

Variables requeridas:
- `GCP_PROJECT_ID` - ID del proyecto en Google Cloud
- `GA4_PROPERTY_ID` - ID de la propiedad de Google Analytics
- `POSTGRES_PASSWORD` - Password seguro para PostgreSQL
- `API_SECRET_KEY` - Clave secreta (generar con `openssl rand -hex 32`)

### 3. Agregar credenciales GCP

```bash
mkdir -p secrets
# Copiar archivo JSON de Service Account
cp /path/to/your-service-account.json secrets/gcp-sa-key.json
chmod 600 secrets/gcp-sa-key.json
```

### 4. Desplegar

```bash
chmod +x scripts/*.sh
./scripts/deploy.sh
```

## URLs de Acceso

| Servicio | URL |
|----------|-----|
| Frontend | https://ai.scram2k.com |
| Backend API | https://api.ai.scram2k.com |
| API Docs (Swagger) | https://api.ai.scram2k.com/docs |
| API Docs (ReDoc) | https://api.ai.scram2k.com/redoc |

## Comandos Utiles

```bash
# Ver logs en tiempo real
docker compose logs -f

# Ver logs de un servicio especifico
docker compose logs -f backend

# Reiniciar servicios
docker compose restart

# Reconstruir sin cache
docker compose build --no-cache
docker compose up -d

# Verificar salud del sistema
./scripts/healthcheck.sh

# Backup de base de datos
./scripts/backup-db.sh

# Acceder a la base de datos
docker compose exec database psql -U ai_user -d vector_store

# Ver estadisticas de recursos
docker stats
```

## API Endpoints

### Chat

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | `/api/v1/chat/sessions` | Crear sesion |
| GET | `/api/v1/chat/sessions` | Listar sesiones |
| GET | `/api/v1/chat/sessions/{id}` | Obtener sesion |
| GET | `/api/v1/chat/sessions/{id}/messages` | Obtener mensajes |
| DELETE | `/api/v1/chat/sessions/{id}` | Eliminar sesion |
| POST | `/api/v1/chat/stream` | Chat con streaming SSE |

### Documents

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Subir documento |
| GET | `/api/v1/documents` | Listar documentos |
| GET | `/api/v1/documents/{id}` | Obtener documento |
| DELETE | `/api/v1/documents/{id}` | Eliminar documento |
| POST | `/api/v1/documents/{id}/reindex` | Re-indexar |
| POST | `/api/v1/documents/search` | Busqueda semantica |

### Health

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/health` | Health check basico |
| GET | `/api/v1/health` | Health check API |
| GET | `/api/v1/health/db` | Health check DB |

## MCP Tools Disponibles

El agente tiene acceso a las siguientes herramientas:

### Google Analytics
- `run_report` - Reportes con metricas y dimensiones
- `run_realtime_report` - Datos en tiempo real
- `get_property_details` - Info de propiedad

### Knowledge Base
- `search_knowledge_base` - Busqueda RAG semantica
- `list_documents` - Listar documentos disponibles

## Seguridad

- Base de datos aislada en red interna (sin exposicion externa)
- SSL/TLS automatico via Traefik + Let's Encrypt
- Secretos montados como volumenes read-only
- CORS configurado solo para dominio frontend
- Validacion de tipos MIME con magic numbers
- Usuario non-root en contenedores

## Troubleshooting

### Backend no inicia
```bash
docker compose logs backend
# Verificar que .env tenga todas las variables
# Verificar que secrets/gcp-sa-key.json exista
```

### Error de conexion a DB
```bash
docker compose exec database pg_isready -U ai_user
# Si falla, reiniciar: docker compose restart database
```

### Frontend muestra error de API
```bash
# Verificar CORS en backend
# Verificar que VITE_API_URL apunte al backend correcto
```

## Mantenimiento

### Backup automatico (cron)
```bash
# Agregar a crontab -e
0 3 * * * /srv/servicios/ai-supra-agent/scripts/backup-db.sh
```

### Actualizaciones
```bash
git pull
docker compose build --no-cache
docker compose up -d
```

---

**Desarrollado para SCRAM** | Arquitectura MD070 v3.6
