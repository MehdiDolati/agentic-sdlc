## TECHNOLOGY STACK SPECIFICATION: AI-Powered Feedback Dashboard (AIFD)

This document details the specific technologies and tools chosen for the AI-Powered Feedback Dashboard (AIFD) project, aligning with the architectural decisions outlined in the ADRs.

### 1. Cloud Platform

*   **Provider:** AWS (Amazon Web Services)
    *   **Rationale:** Leading cloud provider with comprehensive services, strong security features, extensive NLP/AI offerings, and highly scalable infrastructure.

### 2. Core Programming Languages & Frameworks

*   **Backend Services:**
    *   **Language:** Python 3.9+ (primary for AI/ML and data processing), Go (for high-performance, low-latency services like API Gateway or specific connectors)
    *   **Frameworks:**
        *   **Python:** FastAPI (for REST APIs, microservices), Pydantic (data validation), Orchestration Libraries (e.g., Apache Airflow for batch processing/model training pipelines, though initial focus is on real-time stream processing).
        *   **Go:** Gin or Echo (for lightweight, performant microservices where Go is used)
    *   **Rationale:** Python's rich ecosystem for AI/ML, data science, and rapid development. Go for performance-critical components and systems programming aspects.

*   **Frontend (Dashboard):**
    *   **Language:** TypeScript
    *   **Framework:** React v18+
    *   **State Management:** React Query / Zustand
    *   **Styling:** Tailwind CSS / Material-UI
    *   **Charting/Visualization:** Recharts / Nivo / ECharts (for complex data visualizations)
    *   **Rationale:** React for highly interactive UIs, large developer community, and component-based structure. TypeScript for type safety and maintainability.

### 3. Data Ingestion & Messaging

*   **Message Broker:** Apache Kafka (managed service preferred, e.g., AWS MSK)
    *   **Rationale:** High-throughput, fault-tolerant, durable messaging system suitable for event streaming. Scales exceptionally well to handle spikes in feedback volume.
*   **API Gateways:** AWS API Gateway
    *   **Rationale:** Managed service for handling API requests, authentication, throttling, routing for external-facing APIs.
*   **Object Storage (for raw data/large files):** AWS S3
    *   **Rationale:** Highly durable, scalable, cost-effective object storage for raw feedback backups, large CSV uploads, and model artifacts.

### 4. NLP & AI Services

*   **Managed NLP (Initial Baseline):**
    *   **Sentiment Analysis, Keyphrase Extraction, Entity Recognition:** AWS Comprehend
    *   **Rationale:** Leverage managed services for quick wins, lower operational overhead, and robust performance for general-purpose NLP tasks.
*   **Custom NLP/ML Models:**
    *   **Libraries:** Hugging Face Transformers, SpaCy, scikit-learn, PyTorch / TensorFlow
    *   **Model Serving:** FastAPI + ONNX Runtime (for optimized inference) / TorchServe / TensorFlow Serving (depending on model framework)
    *   **Rationale:** Flexibility to build domain-specific models, fine-tune existing models, and address unique customer categorization needs. Containerized for scalable deployment.
*   **Model Training & Experiment Tracking:**
    *   **Platform:** AWS SageMaker (for managed notebook instances, training jobs)
    *   **Experiment Tracking:** MLflow
    *   **Rationale:** Managed services accelerate ML lifecycle, MLflow for reproducibility and tracking experiments.

### 5. Databases

*   **Primary Processed Feedback Storage & Analytics:** Elasticsearch (managed service, e.g., AWS OpenSearch Service)
    *   **Rationale:** Provides full-text search, powerful aggregation capabilities, and distributed nature for scalability, ideal for dashboard visualizations and complex analytical queries over high-volume data.
*   **Metadata & Configuration Database:** PostgreSQL (managed service, e.g., AWS RDS PostgreSQL)
    *   **Rationale:** Offers ACID compliance, strong consistency, and reliability for structured data like user accounts, roles, channel configurations, custom categories, alerts, and audit logs.
*   **Cache:** Redis (managed service, e.g., AWS ElastiCache for Redis)
    *   **Rationale:** For session management, frequently accessed configuration data, and API rate limiting to improve performance and reduce database load.

### 6. Containerization & Orchestration

*   **Container Runtime:** Docker
*   **Container Orchestration:** Kubernetes (managed service, e.g., AWS EKS)
    *   **Rationale:** Standard for containerization and microservices orchestration. Provides automated deployment, scaling, and management of containerized applications, aligning with the microservices architecture.

### 7. CI/CD & DevOps

*   **Version Control:** Git (GitHub/GitLab)
*   **CI/CD Pipeline:** GitHub Actions / GitLab CI / AWS CodePipeline + CodeBuild
    *   **Rationale:** Automate builds, tests, and deployments to Kubernetes clusters.
*   **Infrastructure as Code (IaC):** Terraform
    *   **Rationale:** Define and provision cloud infrastructure programmatically, ensuring consistency and reproducibility.
*   **Monitoring & Logging:**
    *   **Logging:** AWS CloudWatch Logs + Loki / Fluentd (for centralized log aggregation from Kubernetes)
    *   **Metrics:** Prometheus + Grafana (for application and infrastructure metrics, custom dashboards)
    *   **Tracing:** AWS X-Ray / Jaeger (for distributed tracing across microservices)
    *   **Alerting:** PagerDuty / Opsgenie (integrated with Prometheus/CloudWatch)
    *   **Rationale:** Essential for observing system health, performance, debugging, and proactively identifying issues in a microservices environment.

### 8. Authentication & Authorization

*   **User Management:** AWS Cognito / Auth0 (for external identity providers and user pools)
    *   **Rationale:** Managed service for user authentication, potentially integrating with enterprise identity providers.
*   **Authorization:** JSON Web Tokens (JWT) for inter-service communication and API authorization. RBAC implemented at the application level.

### 9. Development Tools

*   **IDE:** VS Code, PyCharm
*   **API Testing:** Postman, Insomnia
*   **Local Development:** Docker Compose
*   **Code Quality:** Linters (ESLint, Pylint), Formatters (Prettier, Black), Unit/Integration Testing Frameworks (Jest, Pytest)

### 10. Network & Security

*   **Virtual Private Cloud (VPC):** AWS VPC
    *   **Rationale:** Isolated and secure network environment for all resources.
*   **Web Application Firewall (WAF):** AWS WAF
    *   **Rationale:** Protect against common web exploits and bots.
*   **Secrets Management:** AWS Secrets Manager / HashiCorp Vault
    *   **Rationale:** Securely store and manage API keys, database credentials, and other sensitive configuration.
*   **Identity and Access Management (IAM):** AWS IAM
    *   **Rationale:** Granular control over AWS resource access for services and personnel.

---
