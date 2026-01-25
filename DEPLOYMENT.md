# Guia de Despliegue - AI-SupraAgent

Este documento sirve como instructivo para desplegar cambios al servidor de produccion usando Claude Code.

---

## Arquitectura de Despliegue

```
[Desarrollo Local]
      |
      | git push
      v
[GitHub Repository]
      |
      | git pull (via SSH)
      v
[Servidor de Produccion (GCP)]
      |
      | docker compose
      v
[Contenedores Docker]
```

---

## Pre-requisitos

### En la maquina local
- Git configurado con acceso al repositorio
- Google Cloud CLI (`gcloud`) instalado y autenticado
- Acceso SSH al servidor de produccion

### En el servidor de produccion
- Docker y Docker Compose instalados
- Repositorio clonado en `/srv/servicios/ai-supra-agent`
- Credenciales de GCP montadas en el contenedor

---

## Paso 1: Preparar Cambios Locales

### 1.1 Verificar estado de git
```bash
cd C:/AI-SupraAgent
git status
```

### 1.2 Agregar archivos al staging
```bash
# Agregar archivos especificos (recomendado)
git add backend/src/archivo.py backend/requirements.txt

# O agregar todos los cambios (cuidado con archivos sensibles)
git add -A
```

**IMPORTANTE:** Nunca agregar:
- Archivos CSV con datos de clientes
- Archivos .env con credenciales
- Archivos temporales o de cache

### 1.3 Verificar lo que se va a commitear
```bash
git diff --cached --stat
```

### 1.4 Crear commit
```bash
git commit -m "$(cat <<'EOF'
tipo: Descripcion corta del cambio

Descripcion detallada:
- Cambio 1
- Cambio 2

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

**Tipos de commit:**
- `feat:` - Nueva funcionalidad
- `fix:` - Correccion de bug
- `refactor:` - Refactorizacion sin cambio de funcionalidad
- `docs:` - Cambios en documentacion
- `style:` - Cambios de formato
- `test:` - Agregar o modificar tests

---

## Paso 2: Subir al Repositorio

```bash
git push origin main
```

Verificar que el push fue exitoso:
```bash
git log --oneline -1
# Debe coincidir con el ultimo commit en GitHub
```

---

## Paso 3: Desplegar en Servidor de Produccion

### 3.1 Opcion A: Comando completo (recomendado)
```bash
gcloud compute ssh prod-server \
  --zone=us-central1-c \
  --project=mi-infraestructura-web \
  --command="sudo -i bash -c 'cd /srv/servicios/ai-supra-agent && git pull && docker compose build backend && docker compose up -d backend'" \
  --quiet
```

### 3.2 Opcion B: Paso a paso

#### Conectar al servidor
```bash
gcloud compute ssh prod-server \
  --zone=us-central1-c \
  --project=mi-infraestructura-web
```

#### Ya en el servidor
```bash
# Cambiar a root
sudo -i

# Ir al directorio del proyecto
cd /srv/servicios/ai-supra-agent

# Obtener cambios
git pull

# Reconstruir imagen Docker
docker compose build backend

# Reiniciar contenedor
docker compose up -d backend

# Verificar logs
docker compose logs -f backend --tail=50
```

---

## Paso 4: Verificar Despliegue

### 4.1 Verificar que el contenedor esta corriendo
```bash
gcloud compute ssh prod-server \
  --zone=us-central1-c \
  --project=mi-infraestructura-web \
  --command="docker ps | grep backend"
```

### 4.2 Verificar health check
```bash
curl http://34.59.193.54:8000/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "service": "ai-supra-agent-backend",
  "version": "1.0.0"
}
```

### 4.3 Verificar logs del contenedor
```bash
gcloud compute ssh prod-server \
  --zone=us-central1-c \
  --project=mi-infraestructura-web \
  --command="docker compose -f /srv/servicios/ai-supra-agent/docker-compose.yml logs backend --tail=20"
```

---

## Comandos de Emergencia

### Rollback rapido
```bash
# Ver commits anteriores
git log --oneline -5

# Revertir al commit anterior
git revert HEAD --no-edit
git push origin main

# Desplegar la reversion
gcloud compute ssh prod-server \
  --zone=us-central1-c \
  --project=mi-infraestructura-web \
  --command="sudo -i bash -c 'cd /srv/servicios/ai-supra-agent && git pull && docker compose build backend && docker compose up -d backend'"
```

### Reiniciar contenedor sin rebuild
```bash
gcloud compute ssh prod-server \
  --zone=us-central1-c \
  --project=mi-infraestructura-web \
  --command="sudo docker compose -f /srv/servicios/ai-supra-agent/docker-compose.yml restart backend"
```

### Ver logs en tiempo real
```bash
gcloud compute ssh prod-server \
  --zone=us-central1-c \
  --project=mi-infraestructura-web \
  --command="sudo docker compose -f /srv/servicios/ai-supra-agent/docker-compose.yml logs -f backend"
```

### Ejecutar comando dentro del contenedor
```bash
gcloud compute ssh prod-server \
  --zone=us-central1-c \
  --project=mi-infraestructura-web \
  --command="sudo docker exec ai-agent-backend python -c 'print(\"Test\")'"
```

---

## Informacion del Servidor

| Parametro | Valor |
|-----------|-------|
| **Servidor** | prod-server |
| **Zona** | us-central1-c |
| **Proyecto GCP** | mi-infraestructura-web |
| **IP Publica** | 34.59.193.54 |
| **Puerto Backend** | 8000 |
| **Directorio** | /srv/servicios/ai-supra-agent |
| **Usuario Docker** | appuser (UID 1000) |

---

## Estructura de Archivos en Servidor

```
/srv/servicios/ai-supra-agent/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   ├── mcp/
│   │   ├── rag/
│   │   └── services/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
├── docker-compose.yml
└── .env
```

---

## Troubleshooting

### Error: Permission denied en git pull
```bash
# Usar sudo -i para tener permisos root
sudo -i bash -c 'cd /srv/servicios/ai-supra-agent && git pull'
```

### Error: docker-compose command not found
```bash
# Usar 'docker compose' (con espacio) en vez de 'docker-compose'
docker compose build backend
```

### Error: Container unhealthy
```bash
# Ver logs del contenedor
docker compose logs backend --tail=100

# Verificar si el proceso esta corriendo
docker exec ai-agent-backend ps aux
```

### Error: Puerto ya en uso
```bash
# Ver que usa el puerto 8000
sudo lsof -i :8000

# Matar proceso si es necesario
sudo kill -9 <PID>
```

---

## Checklist de Despliegue

- [ ] Codigo probado localmente
- [ ] Git status limpio (solo archivos necesarios)
- [ ] Commit con mensaje descriptivo
- [ ] Push exitoso a GitHub
- [ ] Build de Docker exitoso en servidor
- [ ] Contenedor corriendo (docker ps)
- [ ] Health check responde OK
- [ ] Probar funcionalidad en produccion

---

*Documento creado para AI-SupraAgent por Claude Code*
