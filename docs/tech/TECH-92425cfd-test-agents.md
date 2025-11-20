# TECHNOLOGY STACK SPECIFICATION

This document details the chosen technologies and implementation guidelines for the "Test Agents" project, aligning with the architectural decisions outlined in the ADRs.

## 1. Core Principles

*   **Modularity:** Emphasize clear separation of concerns within the monolithic structure.
*   **Observability:** Implement robust logging, monitoring, and tracing.
*   **Automation:** Prioritize CI/CD for consistent builds and deployments.
*   **Security:** Follow best practices for data protection, authentication, and authorization.
*   **Scalability:** Design for horizontal scaling where appropriate, even within the initial modular monolith.

## 2. Shared Infrastructure & Tooling

*   **Version Control:** Git (e.g., GitHub, GitLab, Bitbucket)
    *   **Guidelines:** Use feature branches, pull requests (PRs) for code review, conventional commits, and semver for tagging releases.
*   **Containerization:** Docker
    *   **Purpose:** For packaging all services (backend, frontend, database, message broker) for consistent development, testing, and production environments.
    *   **Guidelines:** Use official base images, multi-stage builds, minimize image size, ensure containers are stateless where possible.
*   **Container Orchestration (Future/Dev):** Docker Compose (for local development and integration testing). Kubernetes (potential future for production deployment as microservices evolve).
*   **CI/CD:** GitHub Actions / GitLab CI / Jenkins
    *   **Purpose:** Automate build, test, and deployment processes.
    *   **Guidelines:** Automatic unit/integration tests on PRs, automated builds, and deployments to staging/production environment.
*   **API Documentation:** OpenAPI/Swagger
    *   **Purpose:** Document REST APIs for internal and external consumers.
    *   **Guidelines:** Generate documentation from code (e.g., using `drf-spectacular` for Django REST Framework) or maintain manually and keep updated.
*   **Logging:** Centralized Logging (e.g., ELK stack, Grafana Loki, or cloud-specific solutions like CloudWatch Logs)
    *   **Guidelines:** Structured logging (JSON format), include request IDs for traceability, log at appropriate levels (INFO, WARN, ERROR).
*   **Monitoring & Alerting:** Prometheus + Grafana (or cloud-native alternatives)
    *   **Guidelines:** Instrument services with metrics (e.g., request rates, error rates, latency), set up dashboards and alerts for critical system health indicators.

## 3. Backend (Test Definition Service, Test Execution Engine, Reporting & Analytics Service logic)

*   **Language:** Python 3.10+
    *   **Rationale:** Strong ecosystem for testing (Pytest), data processing, and AI/ML (if agent types lean that way), widely used, and good developer productivity. Well-suited for text processing and command-line interactions (CLI agents).
*   **Framework:** Django REST Framework (DRF)
    *   **Rationale:** Provides a robust, batteries-included framework for rapid API development, strong ORM for database interaction, and built-in features like authentication, permissions, and serialization. Aligns well with the modular monolith concept by allowing clear application boundaries within one project.
    *   **Key Components:**
        *   Django ORM: For database interactions.
        *   Django Migrations: For schema evolution.
        *   DRF ViewSets & Serializers: For API endpoint creation and data serialization/deserialization.
*   **Task Queuing/Broker:** RabbitMQ (or Kafka if high throughput stream processing is anticipated for results or agent interactions)
    *   **Rationale (RabbitMQ):** Mature, flexible, and robust message broker suitable for task queueing (test execution tasks, result collection). Good support for worker reliability patterns (acknowledgements, retries). Easier to operate than Kafka for initial needs.
    *   **Rationale (Kafka - Alternative/Future Scaling):** If the volume of test executions or reported results grows to millions per day, or if real-time stream processing of agent interactions becomes a requirement, Kafka would be preferred for its high-throughput, distributed log architecture.
    *   **Python Client:** `Pika` (for RabbitMQ) / `confluent-kafka-python` (for Kafka).
*   **Asynchronous Task Processing:** Celery
    *   **Rationale:** A powerful distributed task queue for Python, seamlessly integrating with RabbitMQ. It will manage the `Execution Agents` as Celery Workers.
*   **Testing Framework:** Pytest
    *   **Guidelines:** Write comprehensive unit, integration, and end-to-end tests. Use `pytest-django` for Django integration.
*   **Linters/Formatters:** Black, Flake8, Isort
    *   **Guidelines:** Enforce consistent coding style and catch common errors. Integrate into pre-commit hooks and CI/CD.

## 4. Frontend (User Interface)

*   **Framework:** React (with TypeScript)
    *   **Rationale:** Large community, rich ecosystem, component-based architecture, and strong performance. TypeScript enhances maintainability, especially for NFR-4.4.1.
*   **State Management:** React Query / Zustand / Redux Toolkit
    *   **Rationale:** `React Query` is excellent for server-state management (fetching/caching data from the API). `Zustand` or `Redux Toolkit` can be used for client-side state where needed, but `React Query` handles most data fetching concerns.
*   **Styling:** Tailwind CSS / Styled Components
    *   **Rationale:** `Tailwind CSS` for utility-first rapid UI development, or `Styled Components` for component-scoped styling.
*   **Build Tool:** Vite (or Create React App if starting simple)
    *   **Rationale:** `Vite` for fast development server and optimized builds.
*   **Testing:** React Testing Library + Jest
    *   **Guidelines:** Focus on user-centric testing, ensuring components behave as expected from a user's perspective.
*   **Bundler:** Webpack (underlying Vite/CRA)

## 5. Database

*   **Type:** Relational Database
*   **Specific Choice:** PostgreSQL
    *   **Rationale:** Robust, open-source, highly reliable, and feature-rich. Excellent support for structured data (test definitions, user accounts, agent configurations), transactional integrity, and complex queries for reporting (FR-3.3.5). Supports JSONB columns for flexible storage of `input_data` and `expected_output_assertions` within the structured schema.
*   **Database Management Tool:** DBeaver / PgAdmin

## 6. Agent Integration Adapters

*   **Implementation Language:** Python
    *   **Rationale:** Consistency with the backend, allowing adapters to be loaded and run by the Python-based `Test Execution Engine`. Python's rich libraries simplify interactions with various protocols.
*   **Key Libraries:**
    *   **API-based Agents:** `requests`, `httpx` (for HTTP/HTTPS), `grpcio` (for gRPC).
    *   **Message Queue-based Agents:** `Pika` (RabbitMQ), `confluent-kafka-python` (Kafka), `boto3` (AWS SQS/SNS). Specific adapters will wrap these.
    *   **CLI-based Agents:** `subprocess` module for executing shell commands and parsing output.
*   **Customization:** Each adapter will implement a common Python interface (`AgentAdapter` abstract class) with methods like `send_input(agent_config, input_data)` and `get_output(agent_config, timeout)`.

## 7. Security

*   **Authentication:** JWT (JSON Web Tokens) or OAuth2
    *   **Rationale:** JWT for stateless authentication if multiple microservices are eventually deployed, or `Django-powered session authentication` combined with OAuth2 for user login and authorization with external identity providers.
*   **Authorization:** Role-Based Access Control (RBAC) via Django's permissions system.
*   **Data Encryption:**
    *   **At Rest:** Database encryption (handled by cloud provider or OS/filesystem level).
    *   **In Transit:** TLS/SSL for all network communication (HTTPs, AMQPS for RabbitMQ).
*   **Secrets Management:** Environment variables for development, external secrets management service (e.g., AWS Secrets Manager, HashiCorp Vault, Kubernetes Secrets) for production.
*   **Input Validation:** Strict validation of all user inputs on both frontend and backend to prevent common vulnerabilities (e.g., Injection attacks).

## 8. Deployment Strategy (MVP)

*   **Target Environment:** Cloud Platform (e.g., AWS, GCP, Azure)
*   **Service Hosting:**
    *   **Backend (Modular Monolith):** Containerized on a managed service (e.g., AWS ECS/Fargate, Azure Container Instances, GCP Cloud Run) or a PaaS (e.g., Heroku, Render) for initial ease of deployment.
    *   **Frontend:** Served statically from a CDN (e.g., AWS S3 + CloudFront, GCP Cloud Storage + Cloud CDN).
    *   **Database:** Managed Database Service (e.g., AWS RDS PostgreSQL, Azure Database for PostgreSQL, GCP Cloud SQL for PostgreSQL).
    *   **Message Broker (RabbitMQ):** Managed service (e.g., CloudAMQP) or self-hosted in a container.
*   **Infrastructure as Code (IaC):** Terraform (future consideration for managing cloud resources effectively).

## 9. Data Storage Schema (Conceptual)

### `AgentConfiguration` Model

*   `id` (UUID AutoField)
*   `name` (CharField)
*   `type` (CharField, e.g., 'API', 'Kafka', 'CLI')
*   `base_url` (URLField, for API agents, nullable)
*   `topic_name` (CharField, for Kafka agents, nullable)
*   `cli_path` (CharField, for CLI agents, nullable)
*   `credentials` (JSONField, encrypted, for API keys, tokens, etc.)
*   `owner` (ForeignKey to User)
*   `created_at`, `updated_at` (DateTimeFields)

### `TestCase` Model

*   `id` (UUID AutoField)
*   `name` (CharField)
*   `description` (TextField)
*   `agent_config` (ForeignKey to `AgentConfiguration`)
*   `input_data` (JSONField) - stores flexible input parameters/payload for the agent.
*   `assertions` (JSONField) - list of assertion objects, e.g., `[{"type": "status_code_eq", "expected": 200}, {"type": "json_path_contains", "path": "$.message", "expected": "success"}]`
*   `timeout_seconds` (IntegerField, default 30)
*   `owner` (ForeignKey to User)
*   `created_at`, `updated_at` (DateTimeFields)

### `TestSuite` Model

*   `id` (UUID AutoField)
*   `name` (CharField)
*   `description` (TextField)
*   `test_cases` (ManyToManyField to `TestCase`)
*   `owner` (ForeignKey to User)
*   `created_at`, `updated_at` (DateTimeFields)

### `TestRun` Model

*   `id` (UUID AutoField)
*   `test_suite` (ForeignKey to `TestSuite`, nullable if single test case run)
*   `status` (CharField, e.g., 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED')
*   `started_at`, `finished_at` (DateTimeFields, nullable)
*   `triggered_by` (ForeignKey to User)
*   `total_tests`, `passed_tests`, `failed_tests` (IntegerFields)

### `TestResult` Model

*   `id` (UUID AutoField)
*   `test_run` (ForeignKey to `TestRun`)
*   `test_case` (ForeignKey to `TestCase`)
*   `status` (CharField, 'PASS', 'FAIL', 'ERROR', 'SKIPPED')
*   `actual_output` (JSONField or TextField, depending on agent type output)
*   `error_message` (TextField, nullable)
*   `duration_ms` (IntegerField)
*   `assertion_details` (JSONField, granular pass/fail per assertion)
*   `executed_at` (DateTimeField)

This detailed specification provides a solid foundation for implementing the "Test Agents" project, integrating the architectural decisions with concrete technology choices and best practices.
