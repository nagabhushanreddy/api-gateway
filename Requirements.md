# Multi-Finance User Application
## API Gateway - Requirements Document (OpenAPI-Compliant)

---

## 1. Overview

This document defines the functional and non-functional requirements for the **API Gateway** - a thin, stateless request routing and orchestration layer for the Multi-Finance User Web Application built using a **microservices REST architecture**.

The API Gateway acts as the single entry point (Backend-for-Frontend) for all client requests (web, mobile, third-party), handling authentication, authorization, rate limiting, service routing, correlation ID propagation, and OpenAPI specification aggregation. All exposed APIs must be OpenAPI 3.x compliant.

### Core Responsibility
- **Single Entry Point**: Unified API endpoint for all client requests
- **Authentication Gateway**: JWT validation from auth-service
- **Request Routing**: Route to appropriate microservices based on path
- **Rate Limiting**: Per-user, per-tenant, per-endpoint limits
- **Cross-Cutting Concerns**: Correlation IDs, logging, error standardization
- **OpenAPI Aggregation**: Unified OpenAPI specification from all services
- **Service Discovery**: Route to services via Kubernetes DNS or configuration
- **Resilience**: Health checks, circuit breakers, fallback handling
- **Request Enrichment**: Add user context to requests for downstream services
- **API Documentation**: Interactive API documentation for AI agents and developers

---

## 2. Architecture Principles

- Stateless, horizontally scalable service nodes
- **Thin gateway** (routing, auth, rate limiting only; business logic in services)
- **Service agnostic**: minimal knowledge of service internals
- REST APIs with **OpenAPI 3.0+**
- JWT-based security with token validation
- Asynchronous request handling (async/await)
- Layered architecture: Routes → Middleware → Service Clients
- Request enrichment: add user context without modifying service contracts
- Default **DENY** authorization model (authenticated users only, then service-level authz)
- Fail open for non-critical features (e.g., log aggregation failures don't block requests)
- Reuse shared utilities via utils-service

---

## 3. Features

- **Request Routing**: Path-based routing to microservices (/api/v1/auth → auth-service, etc.)
- **JWT Validation**: Validate access tokens from auth-service on all requests
- **Token Claims Extraction**: Extract user_id, tenant_id, roles from JWT; enrich requests
- **Rate Limiting**: Multi-level (per-user, per-tenant, per-endpoint, per-IP)
- **Correlation IDs**: Generate and propagate X-Correlation-Id to all downstream calls
- **Request Logging**: Log all inbound requests with method, path, status, latency
- **Error Standardization**: Translate service errors to consistent response envelope
- **Service Discovery**: Kubernetes DNS-based or configuration-file-based discovery
- **Health Checks**: Monitor downstream service availability; health endpoint
- **Readiness Checks**: Verify all critical services are reachable
- **CORS Handling**: Support cross-origin requests from web clients
- **Security Headers**: Add X-Frame-Options, CSP, X-Content-Type-Options, etc.
- **Request Validation**: Basic validation (content-type, required headers)
- **Response Compression**: Optional gzip compression for responses
- **OpenAPI Aggregation**: Fetch and merge OpenAPI specs from all services
- **Service Isolation**: Prevent information leakage between tenants
- **Circuit Breaker**: Detect service failures; return 503 instead of timing out
- **Retry Logic**: Automatic retry for transient failures (configurable)
- **Request Timeout**: Configurable per-service timeout to prevent hanging requests
- **Async Processing**: Native async/await for high concurrency
- **Type Safety**: Full Pydantic schema validation for requests/responses
- **OpenAPI Documentation**: Auto-generated interactive documentation with aggregated specs
- **AI Agent Discovery**: Clean, OpenAPI-compliant specs for AI agent consumption

---

## 4. Technology Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI (async, OpenAPI-native, lightweight)
- **HTTP Client**: httpx (async HTTP client for service routing)
- **Rate Limiting**: Custom Redis-backed rate limiter or slowapi
- **JWT Validation**: python-jose or PyJWT
- **Service Discovery**: Kubernetes DNS (built-in) or configuration file
- **Circuit Breaker**: Tenacity (retry library with circuit breaker support)
- **Caching**: Redis for rate limit state and response caching (optional)
- **Logging**: Structured JSON logs via utils-service
- **Metrics**: Prometheus client for metrics export
- **Server**: Uvicorn ASGI

---

## 5. Core APIs / Endpoints

### 5.1 Health & Status Endpoints (Unauthenticated)

#### Health Check
**Endpoint**: `GET /health`

**Request Requirements:**
- No authentication required
- No request body

**Response Requirements:**
- Success Status: 200 OK
- Must return status: "healthy" or "degraded"
- Must return timestamp (ISO 8601)
- Must return uptime seconds

**Business Logic:**
- Return healthy if gateway is running
- Return degraded if any critical service is unhealthy
- Lightweight check; used by load balancers

---

#### Kubernetes Liveness Probe
**Endpoint**: `GET /healthz`

**Response Requirements:**
- Success Status: 200 OK
- Simple text response: "OK"

**Business Logic:**
- Minimal check; just verify gateway process is alive
- Used by Kubernetes liveness probes

---

#### Kubernetes Readiness Probe
**Endpoint**: `GET /ready`

**Response Requirements:**
- Success Status: 200 OK (if all critical services reachable) or 503 Service Unavailable
- Must return service_status object with per-service health:
  - service_name: status (healthy, unhealthy)
  - service_name: last_check_at (timestamp)
  - service_name: error (optional, if unhealthy)

**Business Logic:**
- Check connectivity to all downstream services
- Return 503 if any critical service unreachable
- Critical services: auth-service, entity-service, authz-service
- Optional services: notification-service, document-service
- Used by Kubernetes readiness probes to determine if node should receive traffic

---

### 5.2 Proxied Endpoints (Authenticated, Routed to Services)

All endpoints under `/api/v1` are authenticated and routed as follows:

#### Authentication Service Routes
**Prefix**: `/api/v1/auth`
**Routes to**: auth-service:8001
**Example endpoints**:
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/verify-otp`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`

---

#### Authorization Service Routes
**Prefix**: `/api/v1/authz`
**Routes to**: authz-service:8002
**Example endpoints**:
- `POST /api/v1/authz/check`
- `POST /api/v1/authz/check:batch`
- `GET /api/v1/authz/roles`
- `GET /api/v1/authz/permissions`

---

#### Profile Service Routes
**Prefix**: `/api/v1/profiles`
**Routes to**: profile-service:8006
**Example endpoints**:
- `GET /api/v1/profiles/me`
- `PATCH /api/v1/profiles/me`
- `GET /api/v1/profiles/me/addresses`
- `POST /api/v1/profiles/me/kyc/initiate`

---

#### Loan Service Routes
**Prefix**: `/api/v1/loans`
**Routes to**: loan-service:8005
**Example endpoints**:
- `GET /api/v1/loans/products`
- `POST /api/v1/loans/applications`
- `GET /api/v1/loans`
- `POST /api/v1/loans/{id}/submit`

---

#### Document Service Routes
**Prefix**: `/api/v1/documents`
**Routes to**: document-service:8003
**Example endpoints**:
- `POST /api/v1/documents`
- `GET /api/v1/documents/{id}`
- `GET /api/v1/documents/{id}/download`

---

#### Notification Service Routes
**Prefix**: `/api/v1/notifications`
**Routes to**: notification-service:8007
**Example endpoints**:
- `POST /api/v1/notifications/send`
- `GET /api/v1/notifications/{id}`
- `GET /api/v1/notifications`

---

#### Audit Service Routes (Admin Only)
**Prefix**: `/api/v1/audit`
**Routes to**: audit-service:8008
**Example endpoints**:
- `GET /api/v1/audit/events`
- `POST /api/v1/audit/events/search`

---

### 5.3 API Documentation Endpoints (Unauthenticated)

#### OpenAPI Specification
**Endpoint**: `GET /openapi.json` or `GET /v3/api-docs`

**Response Requirements:**
- Success Status: 200 OK
- Must return complete OpenAPI 3.0.3 specification
- Must include aggregated specs from all downstream services
- Must include security schemes (Bearer JWT, API Key)
- Must include per-service endpoint definitions with descriptions
- Must include request/response schemas for each endpoint

**Business Logic:**
- Aggregate OpenAPI specs from all services
- Merge/consolidate common definitions
- Update base path, servers, security schemes
- Cache aggregated spec (update on-demand or scheduled)
- Expose clean, discoverable API for AI agents

---

#### Interactive Swagger UI
**Endpoint**: `GET /docs`

**Response Requirements:**
- Success Status: 200 OK
- Must render interactive Swagger UI with aggregated OpenAPI spec
- Must allow trying out endpoints directly (if authenticated)

---

#### ReDoc Documentation
**Endpoint**: `GET /redoc`

**Response Requirements:**
- Success Status: 200 OK
- Must render ReDoc documentation with aggregated OpenAPI spec

---

#### Service Discovery (For AI Agents)
**Endpoint**: `GET /api/v1/discovery`

**Response Requirements:**
- Success Status: 200 OK
- Must return service catalog: name, description, base_path, status
- Must return endpoint summary: path, method, summary, tags
- Must return authentication requirements
- Must return rate limit policies

**Business Logic:**
- Provide machine-readable service discovery
- Help AI agents understand available APIs
- Include service status (healthy/degraded)
- Include rate limits per endpoint

---

### 5.4 Gateway Management Endpoints (Admin Only)

#### Get Gateway Status
**Endpoint**: `GET /api/v1/admin/gateway/status`

**Request Requirements:**
- Must include JWT token with admin role
- Must verify role via authz-service

**Response Requirements:**
- Success Status: 200 OK
- Must return: uptime, request_count (total, last hour), error_rate
- Must return: active_connections, queue_depth
- Must return: per-service latency (P50, P95, P99)
- Must return: per-endpoint request count

---

#### Get Rate Limit Status
**Endpoint**: `GET /api/v1/admin/rate-limits`

**Request Requirements:**
- Must include JWT token with admin role

**Query Parameters:**
- user_id (optional, check specific user)
- tenant_id (optional, check specific tenant)

**Response Requirements:**
- Success Status: 200 OK
- Must return: user_limits, tenant_limits, endpoint_limits
- Must return: current_usage and reset_time for each

---

#### Update Rate Limit Configuration
**Endpoint**: `POST /api/v1/admin/rate-limits/config`

**Request Requirements:**
- Must include JWT token with admin role
- Must accept per_user_per_minute (integer)
- Must accept per_tenant_per_minute (integer)
- Must accept per_ip_per_minute (integer)
- Must accept per_endpoint_overrides (object)

**Response Requirements:**
- Success Status: 200 OK (if updated) or 201 Created
- Must return updated configuration

**Business Logic:**
- Allow hot-reload of rate limit config
- Apply immediately to new requests
- Log configuration changes

---

#### Update Service Routes
**Endpoint**: `POST /api/v1/admin/services/{service_name}/route`

**Request Requirements:**
- Must include JWT token with admin role
- Must accept service_name (enum)
- Must accept host, port (or service_url)
- Must accept health_check_path (optional)

**Response Requirements:**
- Success Status: 200 OK
- Must return updated service route

**Business Logic:**
- Allow dynamic service route configuration
- Test connectivity before updating
- Apply immediately (zero downtime)

---

## 6. Data Model Requirements (Descriptive)

**Gateway Request Context:**
- correlation_id (UUID, generated)
- user_id (from JWT claims)
- tenant_id (from JWT claims)
- roles (from JWT claims)
- ip_address (client IP)
- user_agent (client user agent)
- request_path (original request path)
- request_method (HTTP method)
- timestamp (request received at)
- trace_context (for distributed tracing)

**Service Registration Schema:**
- service_name (string, unique)
- service_host (hostname or IP)
- service_port (integer)
- service_path_prefix (e.g., /api/v1/auth)
- health_check_path (e.g., /health)
- health_check_interval (seconds)
- timeout (milliseconds for requests)
- retry_policy: max_retries, backoff_strategy
- circuit_breaker_threshold (number of failures before opening)
- critical (boolean, if 503 if service down)

**Rate Limit State Schema:**
- key (user_id | tenant_id | ip_address | endpoint)
- request_count (current window)
- window_start_at (timestamp)
- limit (max requests in window)
- reset_at (timestamp when window resets)

**OpenAPI Aggregate Spec:**
- openapi (version)
- info (title, version, description)
- servers (list of server URLs)
- paths (aggregated from all services)
- components: schemas, securitySchemes
- security (default requirements)

**Service Health Status Schema:**
- service_name (string)
- status (healthy, degraded, unhealthy)
- last_check_at (timestamp)
- response_time_ms (latency)
- error (optional, if unhealthy)
- consecutive_failures (for circuit breaker)

**Audit Log Schema:**
- request_id (correlation_id)
- user_id (from JWT)
- tenant_id (from JWT)
- method (HTTP method)
- path (request path)
- status_code (HTTP response)
- latency_ms (request duration)
- downstream_service (routed to)
- error_code (if failed)
- timestamp

---

## 7. Business Logic & Rules

### 7.1 Request Processing Flow
1. Accept incoming HTTP request
2. Extract and validate JWT from Authorization header
3. Generate correlation_id if not present
4. Extract user_id, tenant_id, roles from JWT claims
5. Determine target service from request path
6. Check rate limits for user/tenant/IP/endpoint
7. Verify service is healthy (ready)
8. Enrich request headers with correlation_id, user context
9. Forward request to service (with timeout)
10. Log request and response (latency, status, error)
11. Return response to client (standardized error format if applicable)

### 7.2 Rate Limiting
- Per-user limits: e.g., 1000 requests/minute per user
- Per-tenant limits: e.g., 100,000 requests/minute per tenant
- Per-IP limits: e.g., 10,000 requests/minute from single IP (prevent DDoS)
- Per-endpoint limits: e.g., POST /loans slower, allow 100/min; GET /profiles faster, allow 1000/min
- Rate limit hierarchy: strictest applies (e.g., user limit stricter than tenant)
- Return 429 Too Many Requests when exceeded
- X-Rate-Limit-Remaining header in response for client awareness

### 7.3 Service Discovery
- Configuration-driven (services defined in config or environment)
- Kubernetes DNS fallback (service-name.namespace.svc.cluster.local)
- Support dynamic routing updates (admin endpoint)
- Health check periodically (configurable interval)
- Mark service unhealthy after N consecutive failures
- Circuit breaker opens (return 503) after threshold

### 7.4 JWT Validation
- Validate signature using auth-service public key (fetch on startup, cache)
- Validate token not expired
- Validate token claims (user_id, tenant_id, roles present)
- Extract claims and enrich downstream requests
- Refresh token if near expiry (optional, or let client refresh)

### 7.5 Error Handling
- Standardize all error responses across services
- Map service errors to common error codes
- Mask sensitive details (don't expose service internals)
- Include correlation_id for tracing
- Log errors with full context for debugging

### 7.6 Correlation ID Management
- Generate UUID correlation_id on entry if not present
- Extract and propagate X-Correlation-Id header in requests to services
- Include in all logs
- Return in response headers for client tracing
- Enable end-to-end tracing across microservices

### 7.7 Health Checks
- /health: basic gateway health (always 200)
- /ready: check critical services (400 if any down)
- /healthz: liveness probe (always 200)
- Health check interval: configurable per service (default: 30s)
- After 3 consecutive failures, mark service unhealthy
- After recovery, mark service healthy again

### 7.8 Circuit Breaker
- Track consecutive failures per service
- Open circuit (return 503 Service Unavailable) after threshold (default: 5 failures)
- Allow periodic test requests (half-open state) to check recovery
- Close circuit when service recovers
- Reset failure count when service healthy for period

### 7.9 Request Timeout
- Configurable per service (default: 30 seconds)
- Abort request if service doesn't respond in time
- Return 504 Gateway Timeout
- Log timeout with service name

### 7.10 Multi-Tenancy
- Extract tenant_id from JWT claims
- Ensure user can only access own tenant's data (services enforce)
- Prevent cross-tenant data leakage
- Rate limits per-tenant for fairness

---

## 8. Security Requirements

### 8.1 Authentication
- **JWT Validation**: All requests (except /health, /healthz, /docs, /redoc, /openapi.json) require Bearer token
- **Token Source**: Authorization header (Bearer <token>)
- **Signature Verification**: Validate JWT signature using auth-service public key
- **Expiry Check**: Reject expired tokens (401 Unauthorized)
- **Claims Validation**: Ensure user_id, tenant_id, roles present

### 8.2 Authorization
- **Coarse-grained at Gateway**: Authenticated users only
- **Fine-grained Authorization**: Delegated to authz-service via downstream services
- **Default Deny**: Unauthenticated requests rejected at gateway
- **Admin Endpoints**: Require admin role verified via authz-service

### 8.3 Data Protection
- **No Sensitive Data in Logs**: Don't log full JWT, passwords, PII
- **Mask Response Sensitive Data**: Services responsible, but gateway shouldn't add
- **HTTPS/TLS**: All external traffic must be TLS encrypted
- **Internal mTLS**: Between gateway and services (optional, Kubernetes network policy)

### 8.4 Input Validation
- Validate request format before routing (valid JSON if applicable)
- Validate content-type header matches body
- Prevent oversized requests (max body size: 10MB configurable)
- Sanitize URL paths to prevent traversal attacks

### 8.5 Security Headers
- X-Frame-Options: DENY (prevent clickjacking)
- X-Content-Type-Options: nosniff (prevent MIME sniffing)
- Strict-Transport-Security: max-age=31536000 (enforce HTTPS)
- Content-Security-Policy: restrict resource loading
- X-Permitted-Cross-Domain-Policies: none

### 8.6 Rate Limiting (Security)
- Prevent brute force attacks via rate limiting
- Prevent DDoS via per-IP limits
- Prevent resource exhaustion via per-tenant limits
- Return 429 Too Many Requests when exceeded

### 8.7 Service-to-Service Security
- Use API keys or mTLS for internal service communication (optional)
- Validate service responses (basic sanity checks)
- Don't blindly forward sensitive data from services

### 8.8 Audit & Monitoring
- Log all requests with correlation IDs
- Log authentication/authorization decisions
- Monitor for suspicious patterns (high error rates, rate limit violations)
- Alert on security events (too many 401/403, circuit breaker trips)

---

## 9. Performance Requirements

### 9.1 Latency
- P50 gateway latency (request received to response sent): <50ms
- P95 gateway latency: <100ms
- P99 gateway latency: <200ms
- Gateway latency should be <10% of downstream service latency

### 9.2 Throughput
- Support 10,000 concurrent connections (HTTP keep-alive)
- Support 50,000+ requests per second (across all connections)
- Queue processing: process request and route in <100ms average

### 9.3 Scalability
- Horizontally scalable (stateless; can add nodes)
- Rate limit state in Redis (shared across nodes)
- Service discovery centralized (Kubernetes DNS or config)

### 9.4 Resource Usage
- Memory: ~100MB per instance (minimal overhead)
- CPU: Scale with request volume (async keeps CPU low)
- Network: No unnecessary buffering or compression overhead

---

## 10. Error Handling

### 10.1 Standard Error Response
All errors returned in standardized envelope:
- success: false (boolean)
- error object: code (ERROR_CODE), message (human-readable), details (optional)
- data: null
- metadata: timestamp (ISO 8601), correlation_id (UUID)

### 10.2 HTTP Status Codes & Error Codes
- **400 Bad Request**: INVALID_REQUEST (malformed request, missing required header)
- **401 Unauthorized**: UNAUTHORIZED (missing/invalid JWT token)
- **403 Forbidden**: FORBIDDEN (authenticated but insufficient permissions)
- **404 Not Found**: NOT_FOUND (service/endpoint not found)
- **429 Too Many Requests**: RATE_LIMITED (rate limit exceeded)
- **500 Internal Server Error**: INTERNAL_SERVER_ERROR (gateway error, not service error)
- **502 Bad Gateway**: SERVICE_UNAVAILABLE (downstream service returned error)
- **503 Service Unavailable**: SERVICE_UNAVAILABLE (circuit breaker open, service down)
- **504 Gateway Timeout**: REQUEST_TIMEOUT (downstream service didn't respond in time)

### 10.3 Error Translation
- Gateway translates service errors to consistent format
- Hides service-specific error details from clients
- Includes correlation_id for debugging

---

## 11. External Service Integration

### 11.1 Auth Service
**Purpose**: Token validation and JWT verification

**Operations:**
- Fetch public key for JWT validation
- Validate JWT signature and expiry
- Extract user_id, tenant_id, roles from claims

**Error Handling:**
- Cache public key; periodically refresh
- If auth-service down, use cached key
- Return 503 if must validate and auth-service unreachable

### 11.2 AuthZ Service
**Purpose**: Authorization decisions for admin endpoints

**Operations:**
- Check if user has admin role
- Check if user can access specific endpoint (optional, could push to services)

**Error Handling:**
- Cache authorization decisions (short TTL)
- Fail closed (deny access) if authz-service unavailable

### 11.3 Service Instances
**Purpose**: Route requests to appropriate service

**Operations:**
- Discover service locations (Kubernetes DNS)
- Forward HTTP requests to service
- Track service health
- Implement circuit breaker

**Error Handling:**
- Retry transient failures
- Open circuit on repeated failures
- Return 503 if critical service unavailable

### 11.4 Utils Service
**Purpose**: Shared logging and configuration

**Operations:**
- Initialize structured logging
- Use pre-configured logger instance
- Get configuration from environment

---

## 12. Testing Requirements

### 12.1 Unit Tests
- JWT validation logic
- Rate limit calculations and enforcement
- Correlation ID generation and propagation
- Error code mapping
- Service route matching (path-based)
- Request header enrichment
- Minimum 80% code coverage

### 12.2 Integration Tests
- End-to-end request routing (request → gateway → service → response)
- JWT validation with auth-service (mocked)
- Rate limiting across multiple users/tenants
- Service health checks and circuit breaker
- Error handling and standardization
- OpenAPI spec aggregation
- Failure scenarios (service down, timeout, error)

### 12.3 Performance Tests
- Load test: 1000 concurrent requests
- Throughput test: measure requests per second
- Latency test: measure P50, P95, P99
- Service routing overhead

### 12.4 Security Tests
- JWT validation (expired, invalid signature, missing)
- Rate limit enforcement
- Cross-tenant isolation
- Input validation (oversized requests, invalid JSON)
- Security header presence
- Sensitive data not in logs

---

## 13. Configuration Requirements

### 13.1 Application Settings
- Service name: api-gateway
- Version and environment tracking
- Server host, port (default: 8000, standard HTTP)
- Worker count (for uvicorn)
- Keep-alive timeout (for long connections)

### 13.2 Security Configuration
- JWT settings: public key endpoint (auth-service), algorithm (HS256)
- AuthZ-service endpoint, timeout (5s), retry attempts (2)
- Public key cache TTL (default: 1 hour)
- HTTPS/TLS: certificate path (if terminating TLS)

### 13.3 Rate Limiting Configuration
- Per-user limit: default 1000 requests/minute (configurable)
- Per-tenant limit: default 100,000 requests/minute (configurable)
- Per-IP limit: default 10,000 requests/minute (configurable)
- Per-endpoint overrides: specific paths with custom limits
- Rate limit window: default 60 seconds
- Rate limit storage: Redis host, port, credentials

### 13.4 Service Configuration
- Service registry: list of downstream services with:
  - service_name, host, port, path_prefix
  - health_check_path, health_check_interval (default: 30s)
  - timeout (default: 30s)
  - retry_policy (max_retries, backoff)
  - circuit_breaker_threshold (default: 5 failures)
  - critical (mark 503 if down)

### 13.5 Gateway Behavior Configuration
- Request timeout: default 30 seconds (per service override)
- Max request body size: default 10MB
- Max response body size: default 100MB
- Response compression: enable/disable, min size
- CORS: allowed origins, methods, headers
- Circuit breaker: failure threshold, half-open test period

### 13.6 OpenAPI Configuration
- Aggregate OpenAPI specs on startup (or schedule refresh)
- Exclude internal endpoints from aggregated spec
- Custom info (title, version, description)
- Servers (base URLs for clients)

### 13.7 Logging Configuration
- Log level (INFO default), JSON format, stdout output
- Log sensitive field masking (JWT, passwords, PII)
- Log request/response details (method, path, status)
- Log latency and errors

---

## 14. Deployment

### 14.1 Container
- Docker image with Python 3.10+ and all dependencies
- Health check endpoint: `/healthz`
- Readiness probe: `/ready`
- Liveness probe: `/healthz`

### 14.2 Kubernetes
- Minimum 2 replicas for HA
- Resource limits: CPU 1 core, Memory 512MB
- Resource requests: CPU 500m, Memory 256MB
- HPA based on CPU > 70% or request latency > 300ms
- Ingress: route external traffic to gateway
- Network policy: allow gateway to services, deny service-to-internet

### 14.3 Service Discovery
- Kubernetes DNS: service-name.namespace.svc.cluster.local
- Alternative: Consul, Eureka (if not using Kubernetes)

### 14.4 Load Balancing
- External load balancer (AWS ELB, nginx) in front of gateway
- TLS termination at load balancer (or in gateway)
- Health checks from load balancer to `/health` endpoint

---

## 15. OpenAPI Requirements

### 15.1 OpenAPI Specification
- Version: OpenAPI 3.0.3
- Title: Multi-Finance API Gateway
- Version: 1.0.0
- Base Path: `/api/v1`
- Aggregate specs from all downstream services

### 15.2 Security Schemes
- **BearerAuth**: HTTP bearer token authentication with JWT format
- **ApiKeyAuth**: API key passed in X-API-Key header for service-to-service (optional)

### 15.3 Response Headers
- **X-Correlation-Id**: Request correlation ID for tracing
- **X-Rate-Limit-Remaining**: Remaining requests in current window
- **X-Rate-Limit-Reset**: Timestamp when rate limit resets

### 15.4 Documentation
- Interactive Swagger UI at `/docs`
- ReDoc documentation at `/redoc`
- OpenAPI JSON at `/openapi.json`
- Service discovery endpoint at `/api/v1/discovery`

---

## 16. Monitoring & Observability

### 16.1 Metrics
- Request rate (requests per second, per endpoint)
- Latency (P50, P95, P99 per endpoint)
- Error rate (per error code, per service)
- Rate limit violations (per user, per tenant)
- Service health status (healthy, degraded, unhealthy)
- Circuit breaker state (closed, open, half-open)
- Queue depth (pending requests)
- JWT validation failures
- Correlation ID propagation success rate

### 16.2 Logs
- Structured JSON logs with correlation_id, user_id, tenant_id
- Log all requests: method, path, status_code, latency_ms, downstream_service
- Log authentication decisions: JWT validated, user_id extracted
- Log rate limit violations: user/tenant/IP that exceeded limit
- Log service health changes: service down/up
- Log errors: error_code, error_message
- Mask sensitive data: full JWT, passwords, PII

### 16.3 Tracing
- Propagate correlation IDs to all downstream services
- Trace request flow: gateway entry → service selection → downstream call → response
- Include latency per hop (gateway + service)
- Support distributed tracing systems (Jaeger, Zipkin)

### 16.4 Alerts
- Service unavailable (circuit breaker open)
- High error rate (> 5% of requests)
- High latency (P95 > 500ms)
- Rate limit violations (possible attack)
- JWT validation failures (possible compromise)
- Service health check failures

---

## 17. Project Structure (Logical, No Code)

Root entrypoint main.py with FastAPI app initialization, lifespan events (service discovery on startup), middleware setup.

app/ package containing:
- config.py: Configuration loading from environment and YAML
- middleware.py: JWT validation, correlation ID generation, request enrichment, error handling
- cache.py: Rate limit state, JWT public key, service health status caching
- models/: Pydantic schemas for requests, responses, error envelopes
- routes/: API endpoint handlers organized by feature (health, proxy, admin, discovery, docs)
- services/: Business logic layer
  - gateway_service: Request routing coordination
  - jwt_service: JWT validation and claims extraction
  - rate_limit_service: Per-user/tenant/IP rate limiting
  - service_discovery: Service registration and health checking
  - circuit_breaker_service: Circuit breaker logic per service
  - error_service: Error translation and standardization
  - openapi_service: OpenAPI spec aggregation from downstream services
- clients/: External service HTTP clients
  - service_client: Generic HTTP client for routing requests to services
  - auth_service: Auth service client (fetch public key)
  - authz_service: AuthZ service client (check admin role)
  - service_registry: Manage service locations and health

tests/: Unit and integration tests with conftest.py, mocked services, reports directory

config/: YAML files for app and logging configuration

requirements.txt and requirements-dev.txt: Dependencies

Standards:
- Each directory with Python code MUST have __init__.py
- Use absolute imports: from app.services import GatewayService
- Export commonly used classes in __init__.py files
- Thin gateway: routes and validates; services implement business logic
- Keep routes thin (validation + delegation only)
- Business logic in services layer
- External integrations in clients layer
- Use from utils import logger for logging
- Use from utils import init_app_logging for initialization
- Async/await throughout (httpx for async HTTP, asyncio for concurrency)

---

## 18. API Versioning Strategy

### 18.1 Multi-Version Support (v1, v2, v3+)

**URL Path Versioning:**
- All endpoints versioned in URL path: `/api/v{number}/*`
- Examples: `/api/v1/auth/login`, `/api/v2/loans/applications`, `/api/v3/profiles/me`
- Clear, discoverable version in URL
- Enables easy routing and versioning per endpoint

**Version Numbering:**
- Semantic versioning: v1, v2, v3, etc. (integer version, not semantic MAJOR.MINOR.PATCH)
- Major breaking changes trigger new version
- v1 baseline from release; increment on incompatible changes
- Example progression: v1 (initial) → v2 (breaking changes) → v3 (new breaking changes)

**Service Routing by Version:**
- Gateway routes `/api/v1/*` requests to service expecting v1 API
- Gateway routes `/api/v2/*` requests to service expecting v2 API
- Services should support multiple API versions in single codebase
- Each version has separate route handlers sharing business logic where possible

**Example Routing:**
```
GET /api/v1/loans → loan-service (v1 endpoint handler)
GET /api/v2/loans → loan-service (v2 endpoint handler, enhanced schema)
GET /api/v3/loans → loan-service (v3 endpoint handler, new features)
```

### 18.2 Service-Level Versioning

**Multiple Versions in Single Service:**
- Service handles multiple API versions from single codebase
- Version-specific route handlers in `/routes/v1.py`, `/routes/v2.py`, etc.
- Shared business logic in `/services/` (not version-specific)
- Version-specific models in `/models/v1/`, `/models/v2/` if schemas differ

**Service Structure Example:**
```
app/
  ├── routes/
  │   ├── __init__.py
  │   ├── v1/
  │   │   ├── __init__.py
  │   │   ├── loans.py      (v1 endpoints)
  │   │   ├── profiles.py   (v1 endpoints)
  │   │   └── documents.py
  │   ├── v2/
  │   │   ├── __init__.py
  │   │   ├── loans.py      (v2 endpoints, different schema)
  │   │   └── profiles.py   (v2 endpoints)
  │   └── v3/
  │       ├── __init__.py
  │       └── loans.py      (v3 endpoints)
  ├── services/             (shared, version-agnostic business logic)
  │   ├── loan_service.py
  │   ├── profile_service.py
  │   └── document_service.py
  ├── models/
  │   ├── v1/
  │   │   ├── loan.py       (v1 schemas)
  │   │   └── profile.py
  │   ├── v2/
  │   │   ├── loan.py       (v2 schemas, different fields)
  │   │   └── profile.py
  │   └── shared/           (shared DTOs, internal models)
  │       └── loan_internal.py
```

### 18.3 Backward Compatibility Within Version

**API Contract Guarantees:**
- Within a version (e.g., v1), API contract remains stable
- v1.0 → v1.1 → v1.2: Add fields, add optional params, add new endpoints (backward-compatible)
- v1.x changes must NOT: Remove fields, rename fields, change field types, remove endpoints
- Consumers of v1 can upgrade within v1.x without code changes

**Patch vs. Breaking Changes:**
- Patch version (v1.1 → v1.2): Bug fixes, new optional fields, new endpoints
- Major version (v1 → v2): Breaking changes (remove fields, change types, remove endpoints)

### 18.4 Deprecation Policy

**Version Lifecycle:**
- New version released (v1)
- Active support: 2 years of bug fixes and security patches
- Deprecation window: 1 year of warning (before removal)
- End-of-life: Version no longer supported, removed from service

**Example Timeline:**
- v1 released: Jan 2024
- v2 released: Jan 2026 (v1 still active)
- v1 deprecation notice: Jan 2027 (warning for 1 year)
- v1 sunset: Jan 2028 (v1 routes removed)

**Deprecation Communication:**
- Announce deprecation date in API response headers (Sunset header, Deprecation header)
- Include migration guide in documentation
- Provide tool/script to help migrate from v1 to v2 (if applicable)
- Email notification to API consumers 6 months before sunset

**Headers for Deprecated Endpoints:**
```
Deprecation: true
Sunset: Wed, 31 Dec 2027 23:59:59 GMT
Link: </api/v2/loans>; rel="successor-version"
```

### 18.5 Coexistence of Multiple Versions

**Running Multiple Versions in Production:**
- API Gateway routes to correct service handler per version
- Gateway accepts: `/api/v1/auth`, `/api/v2/profiles`, `/api/v3/loans` simultaneously
- Services support multiple versions in parallel (separate code paths)
- Clients can choose which version to use

**Traffic Analysis by Version:**
- Monitor request volume per version
- Identify when version usage drops below threshold (for sunsetting)
- Support gradual migration (customers move at own pace)

**OpenAPI Documentation by Version:**
- Separate OpenAPI spec per version: `/v1/openapi.json`, `/v2/openapi.json`, `/v3/openapi.json`
- Gateway aggregates all version specs
- Clients can view spec for version they use
- Documentation portal lists all versions with deprecation notices

### 18.6 Gateway's Role in Versioning

**API Gateway Responsibilities:**
1. Route to correct version handler based on URL path
2. Document all versions in aggregated OpenAPI spec
3. Include deprecation information in documentation
4. Monitor per-version traffic and errors
5. Alert on unusual version usage patterns
6. Block deprecated version requests (after sunset date)

**Example Gateway Routing Logic:**
```
Request: GET /api/v1/profiles/me
→ Extract version: v1
→ Extract resource: profiles
→ Route to: profile-service with handler for v1
→ Validate request against v1 schema
→ Validate response against v1 schema
→ Return to client

Request: GET /api/v2/profiles/me
→ Extract version: v2
→ Extract resource: profiles
→ Route to: profile-service with handler for v2
→ Validate request against v2 schema
→ Validate response against v2 schema
→ Return to client
```

### 18.7 Breaking Changes & Migration Path

**What Triggers Version Bump:**
- Remove or rename a required field: v1 → v2
- Change field type (string → integer): v1 → v2
- Remove endpoint: v1 → v2
- Change behavior of endpoint (different logic): v1 → v2
- Change authentication method: v1 → v2

**What Does NOT Trigger Version Bump:**
- Add new optional field
- Add new optional query parameter
- Add new endpoint
- Add new status code to response
- Fix bug that changed response structure (requires backward compat first)

**Migration Path for Breaking Changes:**
1. Introduce v2 with breaking changes
2. Keep v1 running for 2+ years
3. Deprecate v1 (announce 1 year in advance)
4. Sunset v1 (remove routes and handlers)
5. All traffic shifted to v2

### 18.8 Request/Response Validation by Version

**Version-Specific Schemas:**
- Each version has distinct Pydantic models for requests/responses
- Model fields differ between versions (field additions, removals, type changes)
- Gateway validates request/response against correct version schema
- Prevents version mismatch errors

**Example Schema Difference:**
```
# v1 Profile Response
{
  "id": "uuid",
  "name": "string",
  "email": "string"
}

# v2 Profile Response (breaking change: added required field)
{
  "id": "uuid",
  "name": "string",
  "email": "string",
  "phone": "string"  # NEW REQUIRED FIELD
}

# v3 Profile Response (breaking change: removed field, renamed)
{
  "id": "uuid",
  "full_name": "string",        # RENAMED from name
  "primary_email": "string",    # RENAMED from email
  "contact_phone": "string"     # RENAMED from phone
}
```

### 18.9 Rate Limiting by Version

**Version-Specific Rate Limits:**
- Can enforce different rate limits per version
- Example: v1 (older, slower) → 500 req/min; v2 (optimized) → 1000 req/min
- Encourage migration to newer, more efficient versions
- Prevent old version from consuming excess resources

**Configuration:**
```yaml
rate_limits:
  per_version:
    v1:
      per_user_per_minute: 500
      per_tenant_per_minute: 50000
    v2:
      per_user_per_minute: 1000
      per_tenant_per_minute: 100000
    v3:
      per_user_per_minute: 2000
      per_tenant_per_minute: 200000
```

### 18.10 Testing Multiple Versions

**Test Coverage Requirement:**
- Unit tests for each version's route handlers
- Integration tests for each version (end-to-end)
- Backward compatibility tests (v1 requests still work, response unchanged)
- Forward compatibility tests (v2 features not present in v1)
- Migration tests (data from v1 → v2 works correctly)

---

## 19. Future Enhancements

### 19.1 Advanced Routing (Phase 2)
- Content negotiation (format per Accept header)
- Request aggregation (combine multiple service calls into single client request)
- GraphQL gateway (optional, for complex queries)
- Request transformation (modify request before forwarding)

### 18.2 Caching (Phase 2)
- Response caching for read-only endpoints (GET requests)
- TTL-based cache invalidation
- Cache warming on startup
- Conditional requests (ETag, Last-Modified)

### 18.3 Analytics & Insights (Phase 2)
- API usage analytics (per endpoint, per user, per tenant)
- Error trend analysis
- Latency trend analysis
- Most popular endpoints
- User engagement metrics

### 18.4 API Management (Phase 2)
- API versioning (support multiple API versions simultaneously)
- Deprecated endpoint warnings
- API contract enforcement (request/response validation)
- Webhook support for events
- API quota enforcement (different from rate limiting)

### 18.5 Advanced Security (Phase 2)
- mTLS between gateway and services
- API key management (alternative to JWT)
- OAuth 2.0 flows (authorization code, client credentials)
- RBAC enforcement at gateway (prevent unnecessary service calls)
- Bot/fraud detection (ML-based)

### 18.6 Resilience Enhancements (Phase 2)
- Request deduplication (idempotency)
- Bulkhead pattern (limit concurrent requests per service)
- Fallback responses (cached or default)
- Service mesh integration (Istio, Linkerd)
- Chaos engineering (test failure scenarios)

---

## 20. Git Repository Standards

### 19.1 Repository Structure
Repository structure must follow consistent patterns across all microservices:

**Root Level Files:**
- `.gitignore`: Exclude Python artifacts, environment files, IDE settings, build outputs
- `.gitattributes`: Ensure consistent line endings (LF for source files)
- `LICENSE`: Project license file
- `README.md`: Service overview, setup instructions, running locally
- `requirements.txt`: Production dependencies (pinned versions)
- `requirements-dev.txt`: Development dependencies (pinned versions)
- `pytest.ini`: Test configuration
- `Makefile` or `pyproject.toml`: Build/test commands
- `.env.example`: Example environment variables (no actual secrets)

**Directory Structure:**
- `app/`: Main application package (core logic, routes, services)
- `tests/`: Test files (unit, integration, e2e)
- `config/`: Configuration files (YAML for app config, logging)
- `logs/`: Log directory (created at runtime, not versioned)
- `reports/`: Test reports (junit.xml, coverage.xml, htmlcov/) - created at test runtime
- `docs/`: Additional documentation (ADRs, architecture diagrams, API guides)

### 19.2 .gitignore Requirements
Must exclude the following patterns:

**Python Artifacts:**
- `__pycache__/`, `*.py[cod]`, `*$py.class`
- `.Python`, `*.so`, `*.egg`, `*.egg-info/`, `dist/`, `build/`
- `.eggs/`, `*.egg-info/`, `dist/`, `build/`

**Virtual Environments:**
- `venv/`, `env/`, `.venv/`, `ENV/`, `env.bak/`, `venv.bak/`

**IDE & Editor:**
- `.vscode/`, `.idea/`, `*.swp`, `*.swo`, `*~`, `.DS_Store`
- `.sublime-project`, `.sublime-workspace`
- `*.iml`, `.gradle/`, `.classpath`

**Environment & Secrets:**
- `.env`, `.env.local`, `.env.*.local` (but include `.env.example`)
- `*.key`, `*.pem`, `*.crt`, `secrets.yaml`

**Build & Cache:**
- `.tox/`, `.coverage`, `.coverage.*`, `htmlcov/`, `*.cover`
- `.cache/`, `*.cache`
- `node_modules/` (if using frontend build)

**Runtime Generated:**
- `logs/*.log`, `logs/`
- `reports/` (except keep config; exclude xml/html output)
- Storage directories created at runtime (e.g., `/storage/` for local file storage)
- Database files (`.db`, `.sqlite`)

**OS Specific:**
- `Thumbs.db` (Windows)
- `.AppleDouble`, `.LSOverride` (macOS)

### 19.3 Branch Naming Conventions
Enforce consistent branch naming to maintain organization:

**Main Branches:**
- `main`: Production-ready code (stable, released versions)
- `develop`: Development integration branch (pre-release, tested features)

**Feature Branches:**
- `feature/<feature-name>`: New features or enhancements
- Pattern: `feature/user-profile-update`, `feature/rate-limit-config`
- Kebab-case, lowercase

**Bug Fix Branches:**
- `bugfix/<bug-name>`: Bug fixes (non-critical)
- Pattern: `bugfix/jwt-validation-error`

**Hotfix Branches:**
- `hotfix/<issue-name>`: Critical production fixes (from main)
- Pattern: `hotfix/payment-gateway-timeout`
- Merge back to both main and develop after release

**Chore/Refactor Branches:**
- `chore/<task-name>`: Infrastructure, dependencies, refactoring
- `refactor/<task-name>`: Code refactoring
- Pattern: `chore/upgrade-fastapi`, `refactor/service-discovery`

**Documentation Branches:**
- `docs/<topic>`: Documentation updates
- Pattern: `docs/api-gateway-guide`

**Testing Branches:**
- `test/<description>`: Test coverage improvements
- Pattern: `test/add-integration-tests`

### 19.4 Commit Message Standards
Follow conventional commits format for clarity and automation:

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Infrastructure, build, dependency updates
- `ci`: CI/CD configuration changes

**Scope** (optional but recommended):
- Service area affected: `auth`, `routing`, `rate-limit`, `health-check`, etc.

**Subject:**
- Imperative mood: "add feature" not "added feature"
- Lowercase, no period at end
- Max 50 characters

**Body** (optional, for non-trivial changes):
- Explain why, not what
- Wrap at 72 characters
- Separate from subject with blank line

**Footer** (optional):
- Reference issues: `Closes #123`, `Fixes #456`
- Breaking changes: `BREAKING CHANGE: description`

**Examples:**
- `feat(jwt): add token refresh mechanism`
- `fix(routing): resolve service discovery timeout issue`
- `docs(api): update OpenAPI aggregation guide`
- `chore(deps): upgrade fastapi to 0.104.0`
- `test(rate-limit): add concurrent user test cases`

### 19.5 Code Review Process
Enforce code quality and knowledge sharing:

**Pull Request Requirements:**
- Every change requires pull request (no direct commits to main/develop)
- Minimum 2 approvals before merging to main
- Minimum 1 approval for develop branches
- All CI checks must pass (tests, linting, coverage)
- No merge with unresolved conversations

**PR Description Template:**
- What: Brief description of changes
- Why: Motivation and business context
- How: Technical approach and design decisions
- Testing: How changes were tested
- Breaking Changes: Any backward-incompatible changes
- Issue Links: Reference related issues

**Code Review Checklist:**
- Code follows project standards (imports, naming, structure)
- Tests added for new functionality (minimum 80% coverage)
- No hardcoded secrets, credentials, or PII
- Error handling appropriate
- Performance implications considered
- Documentation updated
- No breaking changes without consensus

### 19.6 CI/CD Pipeline Requirements
Automated quality gates on every commit:

**On Every Push:**
- Syntax validation (Python AST check)
- Code style check (flake8, black formatting)
- Import organization (isort)
- Type checking (mypy or Pylance)
- Security scanning (bandit for secrets, vulnerabilities)
- Unit tests (pytest with coverage)
- Minimum 80% code coverage required

**Before Merge to Develop:**
- All unit tests pass
- Integration tests pass (with mocked external services)
- Code coverage at 80%+
- No high-severity linting issues

**Before Merge to Main:**
- All above checks pass
- Performance benchmarks (latency, throughput benchmarks if applicable)
- Security audit (OWASP check, dependency scanning)
- Documentation review (README, API docs up-to-date)
- Version bump and changelog update

**Continuous Deployment:**
- Merge to main triggers automatic build and deploy to staging
- Manual approval for production deployment
- Rollback plan documented and tested

### 19.7 Version Control Standards

**Semantic Versioning:**
- Format: MAJOR.MINOR.PATCH (e.g., 1.2.3)
- MAJOR: Breaking API changes, incompatible changes
- MINOR: New features, backward-compatible
- PATCH: Bug fixes, no new features
- Pre-release versions: 1.0.0-alpha, 1.0.0-beta.1, 1.0.0-rc.1

**Version File:**
- Single source of truth: `app/version.py` or `setup.py` with version constant
- Update on every release
- Referenced in `__init__.py` and API responses

**Tagging:**
- Tag every release: `v1.2.3` (git tag)
- Annotated tags: `git tag -a v1.2.3 -m "Release version 1.2.3"`
- Push tags to remote: `git push origin --tags`

**CHANGELOG:**
- Maintain `CHANGELOG.md` documenting all releases
- Format per Keep a Changelog standard (https://keepachangelog.com)
- Sections: Added, Changed, Deprecated, Removed, Fixed, Security
- Update before release; never on main branch directly

### 19.8 Release Management

**Release Process:**
1. Create release branch: `release/v1.2.3` from develop
2. Update version in code
3. Update CHANGELOG.md with release notes
4. Run full test suite and performance benchmarks
5. Create pull request to main (code review)
6. After approval, merge to main with fast-forward merge
7. Tag release: `git tag -a v1.2.3 -m "Release version 1.2.3"`
8. Merge release branch back to develop
9. Push to remote with tags
10. Build and deploy to production
11. Announce release in team channels

**Hotfix Process:**
1. Create hotfix branch: `hotfix/issue-description` from main
2. Fix critical issue
3. Update version (patch bump)
4. Update CHANGELOG.md
5. Create pull request to main (expedited review)
6. Merge and tag
7. Merge back to develop immediately

### 19.9 Documentation Requirements

**README.md Must Include:**
- Service description and purpose
- Quick start (installation, running locally)
- Project structure (directory layout)
- Configuration (environment variables, config files)
- Running tests (test command and coverage)
- API overview (link to OpenAPI docs)
- Contributing guidelines (for external contributors)
- License information
- Links to architecture/ADR documentation

**Inline Code Documentation:**
- Docstrings on all public functions (Google or NumPy style)
- Type hints on all functions (return type and parameters)
- Comments for complex logic (why, not what)
- No commented-out code (remove or use version control)

**Architecture Documentation:**
- Keep ADRs (Architecture Decision Records) in `docs/adr/`
- Document major design decisions and tradeoffs
- Include decision context, alternatives considered, consequences

**API Documentation:**
- Keep OpenAPI/Swagger docs updated in service code
- Ensure all endpoints have descriptions and schemas
- Document error responses and rate limits
- Keep example requests/responses current

### 19.10 Dependency Management

**Pinning Policy:**
- Pin all dependencies to specific versions in requirements files
- Use compatible releases (~= operator) for safe updates
- Pin development dependencies to same version for consistency
- Update dependencies monthly, review breaking changes
- Use `pip-audit` to check for known vulnerabilities

**Requirements Files:**
- `requirements.txt`: Production dependencies only
- `requirements-dev.txt`: Include requirements.txt + dev tools (pytest, black, mypy, etc.)
- Use constraints: `package==1.2.3` for exact versions

**Dependency Updates:**
- Create dependency update branches: `chore/update-dependencies-2024-01`
- Include changelog from each updated package
- Run full test suite before merging
- Update security vulnerabilities immediately (hotfix process)

### 19.11 Secrets Management

**Never Commit Secrets:**
- No API keys, passwords, credentials in code
- No `.env` files (only `.env.example`)
- No encrypted secrets in repository (use secret management system)
- Use tools to scan commits: `git-secrets`, `detect-secrets`

**Environment Variables:**
- Document all required variables in `.env.example`
- Mark sensitive variables with `# SECRET` comment
- Use strong naming: `DB_PASSWORD` not `DB_PASS`
- Provide defaults for non-sensitive values

**CI/CD Secrets:**
- Store in CI/CD platform (GitHub Secrets, GitLab CI variables)
- Rotate periodically
- Use service accounts (not personal credentials)
- Audit access logs

### 19.12 File Naming & Organization Standards

**Python Files:**
- All lowercase with underscores: `user_service.py`, `auth_routes.py`
- No spaces or hyphens in filenames
- Related files grouped in directories: `services/`, `routes/`, `clients/`

**Test Files:**
- Match source file name with `test_` prefix: `test_user_service.py`
- Group tests in `tests/` directory matching app structure
- Keep test files alongside source for easy discovery

**Configuration Files:**
- YAML format preferred: `app.yaml`, `logging.yaml`
- Separate per environment: `app.dev.yaml`, `app.prod.yaml`
- Use `.example` suffix for templates: `config.example.yaml`

**Documentation Files:**
- Markdown format: `README.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`
- Capitalize file names for major docs: `API_GUIDE.md`
- ADRs numbered: `adr/0001-use-fastapi.md`, `adr/0002-async-processing.md`

### 19.13 Code Quality Tooling

**Required Tools:**
- **black**: Code formatter (enforce consistent style)
- **flake8**: Linter (style and error checking)
- **isort**: Import sorter (organize imports consistently)
- **mypy**: Type checker (static type analysis)
- **pytest**: Test framework with coverage
- **bandit**: Security linter (detect common security issues)

**Pre-commit Hooks:**
- Install `pre-commit` framework
- Run linters and formatters before commit
- Prevent commits with failures (configurable bypass for urgent fixes)
- Hooks include: black, flake8, isort, mypy, bandit, trailing whitespace check

**Configuration Files:**
- `setup.cfg` or `pyproject.toml`: Centralize tool config (black line length, isort profile, mypy settings)
- `.pre-commit-config.yaml`: Pre-commit hook definitions
- `.flake8`: Flake8-specific configuration (exclude patterns, max-line-length)

---

## 21. Non-Functional Requirements - Artifact Management

### 21.1 Test Reporting

**Test Report Location:**
- All test execution reports must be generated in `reports/` folder at project root
- Reports should be organized by test type and timestamp

**Required Test Reports:**
- **Coverage Reports:**
  - `reports/coverage/index.html` - Interactive HTML coverage report (generated by `pytest-cov`)
  - `reports/coverage/.coverage` - Raw coverage database
  - Coverage summary in terminal output during CI/CD

- **JUnit Reports:**
  - `reports/junit.xml` - JUnit-format test results for CI/CD integration
  - Machine-readable format for Jenkins, GitLab CI, GitHub Actions, etc.

- **Test Output:**
  - `reports/test_output.txt` - Verbose test execution log with timestamps
  - Include both passed and failed test details
  - Include any warnings or deprecation notices

**Test Report Lifecycle:**
- Reports cleared before each test run (use `--cov-report=html --cov-report=xml` flags)
- Reports retained for post-execution analysis and CI/CD archival
- Git-ignore reports folder to prevent tracking of local/CI artifacts

**Report Generation Commands:**
```bash
pytest tests/ \
  -v \
  --cov=app \
  --cov-report=html:reports/coverage \
  --cov-report=xml:reports/coverage.xml \
  --cov-report=term-missing \
  --junit-xml=reports/junit.xml \
  --tb=short \
  | tee reports/test_output.txt
```

### 21.2 Dependency Management

**Dependency Segregation:**
- `requirements.txt`: Production dependencies only (FastAPI, httpx, pydantic, python-jose, redis, tenacity, prometheus-client, slowapi, PyYAML)
- `requirements-dev.txt`: Development and testing dependencies (black, flake8, isort, mypy, bandit, pytest, pytest-asyncio, pytest-cov, pre-commit)

**Dependency Best Practices:**
- Pin exact versions in `requirements.txt` for reproducible production builds
- Allow minor version flexibility in `requirements-dev.txt` (e.g., `pytest>=7.0,<8.0`)
- Document purpose of each dependency in comments
- Keep dev dependencies separate to minimize container image size
- Run `pip freeze > requirements.txt.lock` for verified dependency trees

**Container Image Considerations:**
- Only install `requirements.txt` in production Dockerfile
- Install both in development/CI containers
- Remove dev tools from production image (use multi-stage builds)

### 21.3 Version Control & Gitignore

**Comprehensive .gitignore Requirements:**

**Python-Related:**
- `__pycache__/` - Python bytecode
- `*.pyc`, `*.pyo`, `*.pyd` - Compiled Python files
- `.Python` - Virtual environment markers
- `env/`, `venv/`, `.venv/` - Virtual environments
- `.tox/` - Tox test environments
- `.pytest_cache/` - Pytest cache
- `.mypy_cache/` - Mypy cache
- `*.egg-info/`, `*.egg`, `.eggs/` - Setuptools artifacts
- `dist/`, `build/` - Build artifacts

**IDE & Editor:**
- `.vscode/` - VS Code settings (workspace-specific)
- `.idea/` - PyCharm/IntelliJ settings
- `.sublime-workspace` - Sublime Text
- `*.swp`, `*.swo`, `*~` - Vim swap files
- `.DS_Store` - macOS files

**Testing & Coverage:**
- `reports/` - Test reports (html, xml, txt)
- `.coverage` - Coverage database
- `htmlcov/` - Coverage HTML output
- `coverage.xml` - Coverage XML output
- `.pytest_cache/` - Pytest cache

**Dependencies:**
- `requirements.txt.lock` - Frozen dependency tree (optional - for reference only)

**Environment & Configuration:**
- `.env` - Local environment variables (use `.env.example` for template)
- `.env.local` - Local environment overrides
- `*.local.yaml` - Local config overrides

**IDE Ignore Patterns (Optional - for team consistency):**
- Add `.vscode/` to team .gitignore if standardizing on VS Code
- Keep `.idea/` local-only for PyCharm users

**Commit Strategy:**
- Track `requirements.txt` and `requirements-dev.txt` (use exact versions)
- DO NOT track `reports/` folder or `.coverage` files
- DO NOT track virtual environments or `.venv/` folders
- DO NOT track `.env` files (use `.env.example` template)

---

**End of Document**
