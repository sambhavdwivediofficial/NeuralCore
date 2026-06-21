<div align="center">
  
# Security Policy
</div>
NeuralCore is a production-grade AI infrastructure platform designed for enterprise deployment. Security is not a feature layer in NeuralCore — it is a foundational architectural constraint that runs through every subsystem. This document defines the security architecture of the platform, the vulnerability disclosure process, and the responsibilities of operators who deploy NeuralCore in production.

---

## Table of Contents

- [Supported Versions](#supported-versions)
- [Reporting a Vulnerability](#reporting-a-vulnerability)
- [Disclosure Policy](#disclosure-policy)
- [Security Architecture](#security-architecture)
  - [Authentication](#authentication)
  - [Authorization and RBAC](#authorization-and-rbac)
  - [Tenant Isolation](#tenant-isolation)
  - [Data Security](#data-security)
  - [Transport Security](#transport-security)
  - [Secret Management](#secret-management)
  - [API Key Security](#api-key-security)
  - [Audit Logging](#audit-logging)
  - [Input Validation](#input-validation)
  - [Dependency Security](#dependency-security)
  - [Infrastructure Security](#infrastructure-security)
- [Security Configuration for Production Operators](#security-configuration-for-production-operators)
- [Known Limitations and Accepted Risks](#known-limitations-and-accepted-risks)
- [Security Changelog](#security-changelog)

---

## Supported Versions

Security fixes are applied to the current release only. Previous versions do not receive security patches. If you are running an older version and a vulnerability is disclosed, you must upgrade to the current release to receive the fix.

| Version | Security Support |
|---|---|
| Latest release | Active |
| Previous releases | None |

We strongly recommend always running the current release in production environments.

---

## Reporting a Vulnerability

If you have discovered a security vulnerability in NeuralCore, please report it responsibly through private disclosure. Do not open a public GitHub issue for security vulnerabilities.

**Contact:**

Report vulnerabilities directly to the project author:

- **Sambhav Dwivedi**
- Website: [Sambhav Dwivedi](https://www.sambhavdwivedi.in)
- LinkedIn: [Sambhav Dwivedi](https://www.linkedin.com/in/sambhavdwivedi)
- Email: [sambhavdwivedi@outlook.com](mailto:sambhavdwivedi@outlook.com)

**What to include in your report:**

A complete vulnerability report includes:

- A clear description of the vulnerability — what it is, what component it affects, and what the security impact is
- Step-by-step reproduction instructions — the exact steps to trigger the vulnerability
- Proof of concept code or payload, if applicable
- The affected version of NeuralCore
- Your assessment of severity using the CVSS v3.1 framework if possible
- Any suggested remediation, if you have one

Incomplete reports slow down the response process. The more detail you provide, the faster we can validate and address the issue.

**What you should not include:**

Do not include actual customer data, real credentials, or sensitive information from production systems in your report.

---

## Disclosure Policy

**Acknowledgment:** We will acknowledge receipt of your vulnerability report within 72 hours of receiving it.

**Validation:** We will validate the vulnerability and assess its severity. We will provide an initial assessment within 10 business days.

**Remediation:** The timeline for remediation depends on severity. Critical vulnerabilities affecting authentication, tenant isolation, or remote code execution are treated as the highest priority. We will keep you informed of progress.

**Coordinated disclosure:** We ask that you give us a reasonable period — typically 90 days from your initial report — to release a fix before any public disclosure. We will work with you to agree on a disclosure timeline. We will credit you for the discovery in the security changelog unless you request otherwise.

**No legal action:** We will not pursue legal action against security researchers who report vulnerabilities responsibly and in good faith, following this policy. Responsible disclosure means private notification, no exploitation, and no public disclosure before a fix is available.

---

## Security Architecture

### Authentication

**JWT-based authentication** — All API access requires a valid JWT access token. Tokens are signed with RS256 (RSA + SHA-256). The signing key is a 2048-bit RSA private key stored outside the application. The public key is used for verification only and can be safely distributed.

**Token lifecycle:**
- Access tokens expire after 15 minutes. Short expiry limits the window of exposure if a token is compromised.
- Refresh tokens expire after 30 days. Refresh tokens are rotated on every use — using a refresh token invalidates the current refresh token and issues a new one.
- Refresh tokens are stored server-side as bcrypt hashes. The plaintext refresh token is never stored.
- All active sessions for a user can be invalidated by revoking all refresh tokens associated with that user.

**OAuth 2.0 social login** — Google, GitHub, and Microsoft identity providers are supported for social login. OAuth tokens from providers are exchanged for NeuralCore-issued JWTs. NeuralCore never stores the OAuth provider token beyond the initial exchange.

**Brute force protection** — Login endpoints implement rate limiting and account lockout after repeated failed authentication attempts.

---

### Authorization and RBAC

**Role-based access control (RBAC)** is enforced at the API route handler level through a declarative permission system. Every protected route specifies the required permission. The permission check runs before any business logic executes.

**Permission evaluation** is performed at request time against the user's current role assignment. Role changes take effect immediately — there is no token reissuance required for permission changes to take effect.

**Default roles:**

| Role | Scope | Capabilities |
|---|---|---|
| Owner | Organization | Full access to all resources and organization management |
| Admin | Organization | Full access to resources; cannot delete the organization or manage billing |
| Developer | Project | Create, read, update, and delete project resources |
| Viewer | Project | Read-only access to project resources |

**Custom roles** with granular permission sets can be defined per organization, enabling fine-grained access control for enterprise deployments.

**Principle of least privilege** — Default role assignments are as restrictive as possible. Users receive only the permissions they need for their function.

---

### Tenant Isolation

Tenant isolation is the most critical security property of the NeuralCore multi-tenancy system. A breach of tenant isolation — where one tenant can access another tenant's data — is treated as a critical security vulnerability.

**Isolation layers:**

**Database isolation** — Every tenant-scoped table includes a `tenant_id` column. All repository base classes apply a mandatory tenant filter to every query. The tenant filter is applied at the ORM level before query execution — it cannot be bypassed through application-level logic. A query that attempts to return data without a tenant filter will fail at the repository validation layer.

**Vector store isolation** — Every knowledge base collection in every vector store backend is namespaced with the tenant ID. The collection namespace is applied at the vector store abstraction layer. Application code never constructs collection names directly — collection names are always generated by the abstraction layer, guaranteeing correct namespacing.

**Cache isolation** — All Redis keys for tenant-scoped data are prefixed with the tenant ID. Cache lookups without a tenant prefix are not possible through the cache abstraction layer.

**Agent runtime isolation** — Agent runtime instances are scoped to a single tenant. The agent communication routing layer enforces that messages cannot be routed across tenant boundaries.

**Memory isolation** — All five memory layers (short-term, long-term, semantic, episodic, session) store data with tenant scope. Memory retrieval queries always include the tenant filter.

**Tenant context propagation** — The `TenantResolver` middleware extracts and validates the tenant identity from every authenticated request and injects it into the request context. All downstream services receive the tenant context through FastAPI dependency injection. It is not possible to call a service function that accesses tenant-scoped data without providing a tenant context — the function signatures enforce this at the type level.

---

### Data Security

**Data at rest** — Sensitive fields in the database (user passwords, API key hashes, refresh token hashes) are stored using bcrypt with a work factor appropriate to the hardware. Bcrypt hashes are not reversible.

**PII handling** — The preprocessing pipeline includes a configurable PII detection and redaction module. PII detection uses pattern matching and NLP-based entity recognition to identify personal information before it is indexed into the knowledge base. Redaction policies are configurable per tenant and per data source.

**Data minimization** — NeuralCore does not collect or store data beyond what is operationally required. Logs do not contain sensitive user data. Traces do not contain request payloads or response bodies by default.

**Data retention** — Tenant data is retained for the period defined by the tenant's configuration and compliance requirements. Data deletion is complete — soft-deleted records are purged on schedule to ensure data is not retained beyond its intended lifetime.

---

### Transport Security

**TLS everywhere** — All external communication must be over TLS 1.3. TLS 1.1 and TLS 1.2 are not acceptable for new deployments. TLS termination is handled at the ingress / load balancer layer.

**Internal communication** — Service-to-service communication within the Kubernetes cluster uses TLS through a service mesh where the deployment environment supports it.

**Certificate management** — TLS certificates for public endpoints should be managed with automated renewal (Let's Encrypt via cert-manager in Kubernetes deployments is the recommended approach).

**HTTP security headers** — The API middleware injects the following security headers on all responses:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`

**CORS** — Cross-Origin Resource Sharing is configured with an explicit allowlist of permitted origins. The wildcard `*` origin is not permitted in production configurations.

---

### Secret Management

**Environment variables** — Secrets (database credentials, API keys for external providers, JWT signing keys, encryption keys) are passed to the application through environment variables. Secrets are never committed to source control. The `.gitignore` excludes `.env` files.

**Secret managers** — Production deployments should use a dedicated secret manager for secret storage and rotation:
- AWS Secrets Manager
- GCP Secret Manager
- HashiCorp Vault
- Kubernetes Secrets (with encryption at rest enabled)

**Secret rotation** — JWT signing keys, database credentials, and external API keys should be rotated on a regular schedule. NeuralCore supports zero-downtime JWT key rotation through a key rotation endpoint that accepts the new signing key and invalidates tokens signed with the old key after a grace period.

**No secrets in logs** — Logging middleware strips known secret patterns from log output. Developers must never log secrets intentionally, and code review actively checks for accidental secret logging.

---

### API Key Security

**Key generation** — API keys are generated using a cryptographically secure random number generator with sufficient entropy (256 bits).

**Key storage** — The plaintext API key is returned exactly once at creation time and is never stored in the database. The database stores only a bcrypt hash of the key. If a key is lost, it must be revoked and regenerated — there is no recovery path.

**Key scoping** — API keys are scoped to a specific project and a specific role. A key cannot be used to access resources outside its project scope or to perform operations beyond its assigned role.

**Key revocation** — Keys can be revoked instantly. Revoked keys are rejected at the authentication middleware layer — revocation takes effect on the next request after revocation, with no grace period.

---

### Audit Logging

Every security-significant action in the platform is recorded in the audit log with full context.

**Audit events include:**
- Authentication attempts (success and failure) — user identity, IP address, timestamp, outcome
- Authorization failures — user identity, requested resource, required permission, timestamp
- Tenant context switches — who performed the switch, from which tenant, to which tenant
- Data access events — for sensitive operations, which data was accessed, by whom, when
- Configuration changes — what was changed, by whom, when, and the previous and new values
- User management operations — creation, modification, role assignment, deactivation
- API key management — creation, use, and revocation
- Admin operations — any operation performed through the admin API

**Audit log properties:**
- Append-only — audit log records cannot be modified or deleted through application interfaces
- Tamper-evident — audit log integrity can be verified through hash chaining
- Non-repudiable — every event is associated with a verified user identity
- Searchable — audit logs are queryable by user, tenant, event type, resource, and time range

---

### Input Validation

**Request validation** — All API request inputs are validated against Pydantic models before any business logic executes. Schema violations are rejected with a structured error response before the input reaches application code.

**SQL injection** — SQLAlchemy ORM parameterized queries are used exclusively. Raw SQL strings are not used in application code. Stored procedures do not accept dynamic SQL.

**Path traversal** — File system operations validate that resolved paths are within the expected directory boundary.

**SSRF prevention** — Outbound HTTP requests made by loaders (website, sitemap, GitHub) are validated against a configurable allowlist. Private network ranges (RFC 1918), localhost, and metadata service addresses are blocked by default in production configurations.

**Prompt injection** — User-supplied content that enters the prompt construction pipeline is sandboxed from the system prompt through explicit structural separation. The platform does not construct prompts by string concatenation that could allow user content to inject system instructions.

---

### Dependency Security

**Dependency pinning** — All dependencies are pinned to exact versions in `requirements.txt` and package lock files. Unpinned dependencies are not acceptable.

**Vulnerability scanning** — Automated dependency vulnerability scanning is run in the CI pipeline on every pull request and on a daily schedule against the main branch. Known vulnerabilities are tracked and addressed promptly.

**Minimal dependencies** — Dependencies are added only when they provide significant value that cannot be achieved reasonably with existing dependencies or the standard library. Every new dependency adds attack surface — the decision to add a dependency is made deliberately.

**Rust dependencies** — Rust crates are reviewed for security advisories through `cargo-audit` as part of the build process.

---

### Infrastructure Security

**Network segmentation** — In Kubernetes deployments, network policies restrict pod-to-pod communication to defined service interfaces. The database and Redis are not accessible from outside the cluster.

**Container security** — Docker images run as non-root users. Images are built on minimal base images. Images are scanned for CVEs as part of the build pipeline.

**Kubernetes security:**
- RBAC is configured with least-privilege service account permissions
- Pod security standards are enforced at the namespace level
- Secrets are mounted as environment variables or volume mounts, never embedded in ConfigMaps
- The Kubernetes API server is not exposed publicly

**Database security:**
- The database listens only on internal network interfaces
- Database credentials are unique per service and per environment
- Database connections use TLS
- Superuser credentials are not used by application services

---

## Security Configuration for Production Operators

Operators deploying NeuralCore in production are responsible for the following security configuration:

**TLS** — Configure TLS termination at the ingress. Do not run the API over plain HTTP in any environment that handles real data.

**Secret management** — Use a dedicated secret manager. Do not store secrets in environment files in production. Rotate secrets regularly.

**Database** — Run PostgreSQL with TLS enabled. Create a dedicated database user for the application with only the required privileges. Do not use the PostgreSQL superuser for application connections.

**Redis** — Configure Redis with authentication. Do not expose Redis publicly. Use Redis ACLs if running Redis 6+.

**Firewalls** — Restrict inbound traffic to only the required ports (typically 443 for HTTPS and 80 for HTTP redirect). Block all inbound access to internal services (PostgreSQL, Redis, Qdrant, Milvus) from external networks.

**Authentication settings** — Review the default JWT key expiry settings and adjust for your threat model. Enable account lockout policies.

**Audit logging** — Ensure audit logs are shipped to external storage before the application's local log rotation discards them. Audit logs must be retained for a period appropriate to your compliance requirements.

**PII and data handling** — If your deployment processes personal data, review and configure the PII detection and redaction settings in the preprocessing pipeline. Ensure your data retention policies are configured and enforced.

**Network policies** — If deploying on Kubernetes, apply the network policy manifests in `infrastructure/kubernetes/`. Review and tighten the policies for your specific deployment.

**Updates** — Monitor this repository and apply security patches promptly. There is no long-term support for previous versions.

---

## Known Limitations and Accepted Risks

The following are known security limitations that operators should be aware of:

**FAISS vector store** — The FAISS backend does not support collection-level access control. Tenant isolation for FAISS is enforced at the application layer only. FAISS is not recommended for multi-tenant production deployments where tenant data has different security classifications.

**Local Ollama / Llama deployments** — When using locally hosted models, the security of the model serving infrastructure is outside the scope of NeuralCore's security model. Operators are responsible for securing local inference servers.

**Webhook signature validation** — Payment provider webhook validation requires correct configuration of the webhook signing secrets in the environment. Misconfiguration could allow unsigned webhooks to be processed. Verify webhook secret configuration in all payment provider integrations.

**Agent tool use** — Agents with access to tools that perform outbound network requests (web search, website loader) can be directed by malicious prompt content to make requests to attacker-controlled destinations. SSRF mitigations are applied at the infrastructure layer, but prompt injection attacks against agentic workflows are an active area of research and defense is not absolute.

---
<div align="center">

## Security Changelog

Security-significant changes are documented here in addition to the main CHANGELOG.

| Version | Date | Change |
|---|---|---|
| Initial | 2026 | Security architecture established |

---

*NeuralCore Security Policy — Copyright (c) 2026 Sambhav Dwivedi. All Rights Reserved.*
</div>
