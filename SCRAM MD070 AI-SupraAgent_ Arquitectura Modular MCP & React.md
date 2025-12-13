# **Documento de Arquitectura de Software (MD070) \- Enfoque MCP \+ RAG \+ React Frontend**

| Información del Proyecto | Detalles |
| :---- | :---- |
| **Nombre del Proyecto** | AI-SupraAgent: Arquitectura Modular MCP & React |
| **Versión del Documento** | 3.6 (Expansión Detallada: Infraestructura Híbrida y Flujos de Datos) |
| **Fecha** | 12 de Diciembre de 2025 |
| **Autor** | Arquitecto de Software (Gemini) |
| **Repositorio Base** | googleanalytics/google-analytics-mcp |
| **Estado** | Diseño de Experiencia de Usuario, Stack Tecnológico y Estrategia de Despliegue |

## **1\. Introducción**

### **1.1 Propósito y Visión Estratégica**

El propósito fundamental de este documento es definir la arquitectura técnica integral del sistema **AI-SupraAgent**, marcando su evolución desde un prototipo experimental hacia una solución robusta de **Pila Completa (Full Stack)** lista para producción.

La visión estratégica detrás de este sistema es transformar la interacción con los datos empresariales. En lugar de depender de dashboards estáticos o reportes manuales, buscamos crear un ecosistema donde el núcleo lógico se basa en el estándar **Model Context Protocol (MCP)**. Este protocolo garantiza la interoperabilidad y el desacoplamiento de las herramientas backend, permitiendo que el sistema crezca modularmente sin deuda técnica excesiva.

Simultáneamente, elevamos la capa de presentación definiéndola como una **Aplicación Web Progresiva (PWA) construida en React**. Esta decisión no es meramente estética; busca proporcionar una experiencia de usuario (UX) nativa, con tiempos de carga instantáneos y capacidades offline básicas. La interfaz servirá como un hub centralizado: por un lado, un chat conversacional inteligente para consultas analíticas complejas sobre Google Analytics 4 (GA4); por otro, un módulo de administración visual intuitivo para la gestión del conocimiento (RAG), democratizando la capacidad de "enseñar" al agente mediante la carga de documentación empresarial crítica.

### **1.2 Alcance del Sistema**

El sistema se estructura en tres niveles lógicos claramente diferenciados, diseñados para maximizar la cohesión y minimizar el acoplamiento:

1. **Nivel de Presentación (Frontend React):** Actúa como la interfaz humano-máquina. Es una aplicación moderna, responsiva y visualmente rica que soporta no solo el chat en tiempo real mediante WebSockets o Streaming HTTP, sino también la gestión visual de archivos y bases de conocimiento.  
2. **Nivel de Orquestación (Backend/MCP Host):** Funciona como el cerebro operativo o Middleware. Este servidor intermedio gestiona la conexión segura con el modelo Gemini, mantiene el estado de la sesión, autentica a los usuarios y coordina las peticiones hacia los servidores MCP distribuidos.  
3. **Nivel de Servicios (Servidores MCP):** Constituyen la capa de ejecución. Son conectores especializados y aislados (microservicios lógicos) encargados de tareas específicas como la extracción de datos de Analytics o la vectorización y búsqueda en la Base de Datos Vectorial.

### **1.3 Metas Arquitectónicas Clave**

* **Experiencia de Usuario (UX) Fluida y Reactiva:** Implementación de las últimas capacidades de **React 19**, incluyendo **Server Components** para reducir la carga de JavaScript en el cliente y **Streaming UI** para mostrar partes de la respuesta del agente a medida que se generan. Esto es crucial para asegurar que la interfaz nunca se sienta "congelada", incluso durante consultas analíticas pesadas.  
* **Autoservicio de Conocimiento (Democratización de la IA):** Eliminar la dependencia del equipo técnico para actualizar el conocimiento del agente. Proporcionar una interfaz gráfica "Drag & Drop" robusta permite que cualquier usuario autorizado suba PDFs, manuales o estrategias, desencadenando procesos automáticos de indexación y actualización de la base de datos vectorial.  
* **Modularidad y Extensibilidad MCP:** Mantener un desacoplamiento estricto de las herramientas en el backend. Esto significa que agregar una nueva fuente de datos (ej. un CRM o base de datos SQL) solo requiere desplegar un nuevo contenedor MCP, sin necesidad de refactorizar el núcleo del orquestador o el frontend.

## **2\. Vista Lógica de la Arquitectura (Stack Tecnológico)**

### **2.1 Nivel de Presentación: El Dashboard Inteligente (React)**

Este componente es mucho más que una ventana de chat; es un centro de comando integral para la inteligencia de negocios.

* **Tecnologías Base:**  
  * **Framework:** **React 19** implementado sobre **Next.js** o **Vite**. Esta elección garantiza un rendimiento óptimo mediante renderizado híbrido (SSR/CSR) y optimización automática de imágenes y fuentes.  
    * **Requisitos de Seguridad Críticos:**  
      * Actualización inmediata a versiones parchadas (\>= 19.0.1) para mitigar vulnerabilidades conocidas.  
      * Ejecución obligatoria de npm audit en los pipelines de CI/CD antes de cualquier despliegue.  
      * Evaluación de **Cloud Armor** (si se migra a GCP nativo) o reglas estrictas de firewall en el servidor Linux para protección contra ataques DDoS y XSS.  
  * **Estilos y Sistema de Diseño:** Adopción total de **Material Design 3 (M3)**.  
    * Implementación a través de librerías modernas compatibles con React 19, como **MUI v6+** o los nuevos **Material Web Components**.  
    * **Identidad Visual Adaptativa:** Uso de **Dynamic Color**. El sistema extraerá la semilla de color (Seed Color) del logotipo corporativo de la empresa para generar automáticamente una paleta tonal completa. Esto garantiza una consistencia de marca perfecta tanto en modo claro como oscuro, mejorando la accesibilidad y la estética.  
    * **Componentes:** Uso extensivo de superficies elevadas, tarjetas contenedoras de información y un Navigation Drawer colapsable para maximizar el espacio de trabajo en dispositivos móviles.  
  * **Gestión de Estado:**  
    * **Server State:** **TanStack Query (React Query)** para la sincronización eficiente de datos con el backend, manejo de caché, reintentos automáticos en fallos de red y paginación de historiales de chat.  
    * **Client State:** **Zustand** o **React Context** para gestionar estados globales ligeros de la interfaz, como el tema activo (claro/oscuro), el estado del menú lateral o las preferencias de usuario.  
  * **Integración de IA:** **Vercel AI SDK**. Esta librería abstrae la complejidad del manejo de streams de texto, permitiendo renderizar la respuesta del LLM carácter por carácter y gestionar las llamadas a herramientas (Tool Calls) directamente en el frontend con hooks nativos como useChat y useCompletion.  
* **Módulos de la Interfaz:**  
  * **Chat Operativo:** El núcleo de la interacción. Soporta "Generative UI", lo que significa que el agente puede responder no solo con texto, sino renderizando componentes React completos (ej. una gráfica de líneas interactiva, una tabla de datos ordenable o una tarjeta de resumen de KPI) dentro del flujo de la conversación.  
  * **Gestor de Conocimiento (Knowledge Hub):** Una vista administrativa dedicada tipo "Explorador de Archivos".  
    * Área de carga con soporte *Drag & Drop* y validación visual de tipos de archivo.  
    * Tabla de documentos indexados mostrando metadatos (fecha, tamaño) y estado de procesamiento en tiempo real (Procesando, Indexado, Error).  
    * Controles para eliminar documentos obsoletos o forzar la re-indexación de la base vectorial.

### **2.2 Nivel de Orquestación: El MCP Host (Backend)**

Dado que los navegadores web tienen limitaciones de seguridad para ejecutar procesos de servidor o sockets directos, se requiere un orquestador ligero y eficiente.

* **Tecnologías:** **Python (FastAPI)**. Se selecciona Python sobre Node.js debido a su supremacía en el ecosistema de Inteligencia Artificial, su manejo nativo de tipos de datos complejos y su excelente soporte para los SDKs de Vertex AI, LangChain y manipulación de vectores.  
* **Funciones Principales:**  
  * **Cliente MCP:** Actúa como el puente que mantiene conexiones persistentes y seguras con los servidores de herramientas subyacentes.  
  * **API Gateway:** Expone endpoints REST para operaciones CRUD y WebSockets para el streaming bidireccional del chat hacia el Frontend React.  
  * **Gestión de Identidad:** Implementa la autenticación de usuarios mediante **Firebase Authentication** o **Google Identity Platform**. Esto permite delegar la seguridad de las credenciales y facilitar el inicio de sesión con cuentas corporativas de Google Workspace, integrándose con las políticas de la organización.

### **2.3 Nivel de Servicios: Servidores MCP**

Estos son los trabajadores especializados, encapsulados en procesos independientes para garantizar estabilidad y aislamiento.

#### **A. Servidor MCP de Google Analytics (GA4)**

* **Función:** Abstraer la complejidad de la API de Datos de GA4. Traduce intenciones de negocio ("¿Cómo van las ventas?") en consultas técnicas precisas (JSON requests con métricas y dimensiones).  
* **Herramientas Clave:** run\_report para extracción de datos, Youtube para métricas de video, y Youtube para descubrimiento de esquema.

#### **B. Servidor MCP de Conocimiento (RAG Pipeline)**

* **Función:** Gestionar el ciclo de vida de la memoria empresarial. Conecta con Vertex AI Search o la base de datos vectorial local.  
* **Herramientas Expuestas al Agente:** search\_knowledge\_base para recuperación semántica de fragmentos relevantes durante una conversación.  
* **Endpoints de Gestión:** upload\_file y delete\_file, expuestos exclusivamente para el módulo de administración del frontend, permitiendo la gestión dinámica del corpus documental.

## **3\. Vista de Proceso (Flujos de Usuario Detallados)**

### **3.1 Flujo A: Consulta de Campañas (Operación de Chat)**

1. **Inicio (React UI):** El usuario ingresa una consulta natural: "¿Cómo van las conversiones de la campaña 'Black Friday' hoy comparado con ayer?"  
2. **Orquestación (Backend):** El backend recibe el mensaje, valida la sesión del usuario y reenvía el prompt a Gemini, adjuntando las definiciones de las herramientas disponibles (schema).  
3. **Razonamiento (Gemini):** El modelo analiza la petición. Detecta la necesidad de datos cuantitativos y decide invocar la herramienta run\_report del Servidor GA4 con parámetros de fecha específicos ("today" vs "yesterday").  
4. **Ejecución (Servidor GA4):** El servidor MCP recibe la llamada, autentica contra la API de Google usando la Service Account y ejecuta la consulta analítica.  
5. **Generación de Respuesta (Gemini \+ UI):**  
   * Gemini recibe los datos crudos (JSON).  
   * Interpreta los resultados: "Las conversiones han subido un 15% hoy, con 120 ventas registradas frente a 104 ayer."  
   * El Frontend recibe el stream de texto y, detectando la estructura de datos comparativos, renderiza automáticamente un componente de tarjeta visual ("Scorecard") con el indicador de cambio porcentual en verde (+15%).

### **3.2 Flujo B: Entrenamiento del Agente (Gestión Documental \- RAG)**

1. **Carga (React UI \- Knowledge Hub):** El usuario arrastra el archivo Estrategia\_Q4\_2025.pdf al área de carga. El frontend valida localmente el tipo MIME y el tamaño.  
2. **Transferencia (React UI):** Muestra una barra de progreso mientras el archivo se sube de forma segura al endpoint del Backend.  
3. **Procesamiento (Backend \+ Servicios):**  
   * El Backend recibe el archivo y lo almacena en el Google Cloud Storage Bucket (o volumen local seguro).  
   * Invoca al pipeline de ingestión (Servidor de Conocimiento) que:  
     1. Extrae el texto del PDF (OCR si es necesario).  
     2. Divide el texto en fragmentos (chunking) lógicos.  
     3. Genera embeddings (vectores numéricos) usando un modelo como text-embedding-004.  
     4. Inserta los vectores en la base de datos PostgreSQL (pgvector).  
4. **Feedback (Servidor de Conocimiento):** Notifica al backend que la indexación ha finalizado con éxito.  
5. **Confirmación (React UI):** Actualiza el estado del archivo en la lista a "✅ Indexado" y envía una notificación "toast" al usuario.  
6. **Uso Inmediato:** El usuario navega al chat y pregunta: "¿Qué presupuesto asignamos para Q4 según el documento que acabo de subir?". El agente realiza una búsqueda vectorial, recupera el fragmento relevante del nuevo PDF y responde con precisión.

## **4\. Requisitos de Implementación del Frontend**

### **4.1 Experiencia Visual y Feedback**

* **Estados de Carga Semánticos:** Indicadores claros de lo que está ocurriendo "bajos el capó". Mostrar "Analizando documento..." o "Consultando Analytics..." en lugar de un spinner genérico, para que el usuario entienda qué herramienta está utilizando el agente.  
* **Visualización de Datos Adaptativa:** Integración profunda con librerías de gráficas como **Recharts** o **Chart.js**. Si el agente devuelve una serie temporal de visitas, el frontend debe ser capaz de detectarlo y dibujar automáticamente una línea de tendencia interactiva, mejorando la comprensión de los datos más allá de una simple tabla o texto.

### **4.2 Seguridad en la Carga de Archivos**

* **Validación Robusta:** El frontend no debe confiar solo en la extensión del archivo. Debe implementarse una validación de "Magic Numbers" (firmas de archivo) en el cliente o servidor para asegurar que un archivo renombrado .exe como .pdf sea rechazado.  
* **Sanitización y Límites:** Limitar estrictamente el tamaño de archivo (ej. máx 25MB) para prevenir ataques de denegación de servicio (DoS). Advertir visualmente si se intentan subir archivos con nombres que contienen caracteres especiales o rutas relativas.

### **4.3 Escalabilidad del Código React**

* **Arquitectura Atómica:** Organizar los componentes siguiendo principios de diseño atómico (átomos, moléculas, organismos) para maximizar la reutilización de botones, inputs y visualizadores.  
* **Abstracción mediante Hooks:** Crear Custom Hooks como useAgentChat (para lógica de streaming), useKnowledgeBase (para gestión de archivos) o useAuth para encapsular la complejidad de la conexión con el backend y facilitar el testing unitario.

## **5\. Vista de Despliegue (Infraestructura en dev-server)**

La aplicación completa se desplegará utilizando contenedores Docker orquestados en el servidor dev-server existente (IP: 34.134.14.202). Se integrará plenamente en la red traefik existente para la gestión automática de certificados SSL y enrutamiento inverso.

### **5.1 Ubicación Física y Lógica**

* **Ruta de Despliegue en Host:** /srv/servicios/ai-supra-agent/  
* **Estructura de Carpetas Sugerida:**  
  /srv/servicios/ai-supra-agent/  
  ├── docker-compose.yml       \# Orquestación de servicios  
  ├── .env                     \# Variables de entorno y secretos  
  ├── secrets/                 \# Credenciales montadas (SA Keys)  
  ├── frontend/                \# Código fuente y Dockerfile del Frontend  
  ├── backend/                 \# Código fuente y Dockerfile del Backend  
  └── database/                \# Volumen persistente para PostgreSQL Vectorial

### **5.2 Componentes de Infraestructura Detallados**

#### **A. Frontend Container (ai-agent-frontend)**

* **Imagen Base:** nginx:alpine optimizada para servir la compilación estática (build) de React.  
* **Conectividad de Red:**  
  * Conectado a la red traefik (externa) para recibir tráfico del usuario.  
  * Conectado a la red ai\_internal (interna) para comunicación (si fuese necesaria, aunque generalmente el front habla al back vía URL pública/interna).  
* **Configuración Traefik (Dominio scram2k.com):**  
  * Router: traefik.http.routers.ai-front.rule=Host('ai.scram2k.com')  
  * Servicio: traefik.http.services.ai-front.loadbalancer.server.port=80  
  * Middleware: Redirección automática HTTPS y headers de seguridad.

#### **B. Backend Container (ai-agent-backend)**

* **Imagen Base:** python:3.11-slim ejecutando **FastAPI** con servidor **Uvicorn**.  
* **Conectividad de Red:**  
  * Conectado a ai\_internal para acceso exclusivo y seguro a la base de datos vectorial.  
  * Conectado a content-management\_entersys\_net si requiere acceso a APIs legacy existentes.  
* **Configuración Traefik (Dominio scram2k.com):**  
  * Router: traefik.http.routers.ai-api.rule=Host('api.ai.scram2k.com')  
  * CORS: Configurado para aceptar peticiones únicamente desde ai.scram2k.com.  
* **Gestión de Recursos y Performance:**  
  * Límite de Memoria: 512MB (Ajuste conservador considerando la RAM total de 7.8GB del host).  
  * Workers: Configuración de 2 workers Uvicorn para balancear concurrencia sin saturar la CPU.

#### **C. Base de Datos Dedicada (ai-agent-db)**

* **Imagen Base:** pgvector/pgvector:pg16. Una imagen oficial de PostgreSQL que ya incluye la extensión vectorial preinstalada y configurada.  
* **Persistencia:** Volumen local mapeado a /srv/servicios/ai-supra-agent/database/ en el host para garantizar que los datos sobrevivan a reinicios de contenedores.  
* **Aislamiento de Red:** Conectado **exclusivamente** a la red ai\_internal. No tiene exposición al host (127.0.0.1) ni a la red pública, garantizando que solo el Backend pueda leer/escribir vectores.  
* **Configuración Interna:**  
  * DB: vector\_store  
  * Usuario: ai\_user  
  * Puerto: 5432 (Interno del contenedor).  
* **Recursos:** Límite dinámico de memoria entre 256MB y 512MB, optimizado para el tamaño esperado del dataset documental local.

### **5.3 Seguridad, Red y Secretos**

* **Proxy Inverso (Traefik):** Todo el tráfico entrante es gestionado por el contenedor traefik existente (v2.10) en los puertos estándar 80/443. Esto centraliza la terminación SSL y simplifica la gestión de certificados.  
* **SSL/TLS:** Uso de certificados Wildcard o específicos generados y renovados automáticamente por Traefik mediante Let's Encrypt para el dominio \*.scram2k.com.  
* **Gestión de Secretos:**  
  * Las credenciales sensibles, como el JSON de la Service Account de Google Cloud (necesario para Vertex AI y GA4), **no se integran en la imagen Docker**.  
  * Se montan como volúmenes de solo lectura en tiempo de ejecución: \- ./secrets/gcp-sa-key.json:/app/secrets/key.json:ro.  
  * Las variables de entorno (DB Password, API Keys) se inyectan mediante un archivo .env restringido.

*Fin del Documento MD070*