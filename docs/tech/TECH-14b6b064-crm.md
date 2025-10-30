# TECHNOLOGY STACK SPECIFICATION: Universal CRM

## 1. Overview

This document specifies the technology stack for the Universal CRM project, based on the Product Requirements Document (PRD) and the Architecture Design Records (ADRs). The choices prioritize scalability, reliability, maintainability, security, and developer productivity, aligning with a cloud-native, microservices-oriented approach on AWS.

## 2. Cloud Platform

*   **Provider:** Amazon Web Services (AWS)
*   **Regions:** Primary deployment in a single region (e.g., `us-east-1` or `eu-west-1` based on target market) with disaster recovery strategy to another region.
*   **Core Services:**
    *   **Compute:** AWS EKS (Elastic Kubernetes Service) for container orchestration, AWS Lambda for serverless functions (e.g., event processing, CRON jobs).
    *   **Networking:** AWS VPC (Virtual Private Cloud), ALB (Application Load Balancer), Route 53 (DNS).
    *   **Database:** AWS RDS for PostgreSQL (primary), AWS DynamoDB (for specific NoSQL needs), AWS ElastiCache for Redis (caching).
    *   **Storage:** AWS S3 (Object Storage for static assets, backups), AWS EBS (Block Storage for EKS nodes).
    *   **Messaging & Eventing:** AWS SQS (Simple Queue Service), AWS SNS (Simple Notification Service), AWS EventBridge (serverless event bus).
    *   **Identity & Access Management:** AWS IAM (for AWS resource access), AWS Cognito (for user authentication).
    *   **Monitoring & Logging:** AWS CloudWatch, AWS X-Ray (for distributed tracing), Prometheus/Grafana on EKS.
    *   **Security:** AWS WAF (Web Application Firewall), AWS KMS (Key Management Service), AWS Secrets Manager.
    *   **Developer Tools:** AWS CodePipeline, AWS CodeBuild, AWS ECR (Elastic Container Registry).

## 3. Backend Technologies

### 3.1. Core Framework & Language
*   **Language:** Python 3.9+
*   **Framework:** FastAPI (for HTTP APIs, leveraging Pydantic for data validation and serialization)
*   **ASGI Server:** Uvicorn

### 3.2. Data Access & ORM
*   **Relational ORM:** SQLAlchemy with Alembic for database migrations.
*   **NoSQL Access:** boto3 (AWS SDK for Python) for DynamoDB interaction.

### 3.3. Asynchronous Task Processing
*   **Task Queue:** Celery (with Redis as broker) for longer-running background tasks (e.g., bulk email sending, data imports, complex reporting generation).
*   **Messaging:** AWS SQS for inter-service communication and event-driven architectures.

### 3.4. Caching
*   **In-Memory/Distributed:** Redis (via AWS ElastiCache) for session management, rate limiting, and frequently accessed data.

### 3.5. Email Services
*   **Provider:** AWS SES (Simple Email Service) for sending transactional emails (e.g., password resets, notifications) and bulk marketing emails (FR.EM.1, FR.MA.2).

### 3.6. Search
*   **Engine:** Elasticsearch (managed either as a dedicated service on AWS or a self-hosted cluster on EKS) for full-text search capabilities across contacts, accounts, and knowledge base articles.

## 4. Frontend Technologies

### 4.1. Core Framework & Language
*   **Language:** TypeScript (strict mode enabled)
*   **Framework:** ReactJS (latest stable version)
*   **State Management:** React Query for server state management, and optionally Zustand or Jotai for simple client-side state.
*   **Routing:** React Router DOM

### 4.2. UI Component Library
*   **Library:** Chakra UI or Material-UI (MUI). (Decision to be made based on design team preference and specific customization needs, leaning towards Chakra UI for styling flexibility and accessibility focus).
*   **Styling:** Emotion or Styled Components when custom styling is required outside the chosen UI library.

### 4.3. Form Management
*   **Library:** React Hook Form with Zod (for schema validation)

### 4.4. Internationalization (i18n)
*   **Library:** react-i18next

### 4.5. Build Tools
*   **Bundler:** Vite
*   **Package Manager:** Yarn or npm (preference to be established by dev team).

## 5. Databases

*   **Primary Relational Database:** PostgreSQL (AWS RDS for PostgreSQL)
    *   **Use Cases:** Contacts, Accounts, Leads, Opportunities, Activities, User/Role data, Core business logic.
    *   **Features:** Multi-AZ for high availability, read replicas for scaling read-heavy workloads, automated backups.
*   **NoSQL Database:** AWS DynamoDB
    *   **Use Cases:** High-volume activity logs, audit trails, user preferences, caching less critical data.
    *   **Features:** On-demand capacity, global tables for multi-region resilience if needed.
*   **Data Warehousing (Future/Advanced Reporting):** AWS Redshift (if standard PostgreSQL reporting becomes a bottleneck).
*   **Caching Database:** AWS ElastiCache for Redis.

## 6. Development & Operations (DevOps)

### 6.1. Version Control System (VCS)
*   **Platform:** GitHub
*   **Strategy:** Gitflow or Trunk-based development (to be decided, leaning towards Trunk-based for microservices with feature flags).

### 6.2. CI/CD Pipeline
*   **Tool:** GitHub Actions
    *   **Stages:** Build, Test (unit, integration), Lint, Security Scan, Containerize, Deploy to EKS/Lambda.
    *   **Deployment:** Argo CD (GitOps for Kubernetes deployments) for continuous delivery.

### 6.3. Containerization & Orchestration
*   **Container Runtime:** Docker
*   **Orchestration:** Kubernetes (AWS EKS)
*   **Container Registry:** AWS ECR

### 6.4. Monitoring, Logging & Tracing
*   **Logging:** Centralized structured logging to AWS CloudWatch Logs, streamed to an ELK stack (Elasticsearch, Logstash, Kibana) or Sumo Logic if advanced log analysis is required.
*   **Metrics:** Prometheus (on EKS) for infrastructure and application metrics, AWS CloudWatch for AWS service metrics.
*   **Dashboarding:** Grafana (on EKS) for consolidating metrics and creating dashboards, AWS CloudWatch Dashboards.
*   **Distributed Tracing:** AWS X-Ray (integrated with Lambda and EKS services) for visualizing request flows across microservices.
*   **Alerting:** PagerDuty/Opsgenie integrated with CloudWatch Alarms and Prometheus Alertmanager.

### 6.5. Security Scanning
*   **Static Application Security Testing (SAST):** SonarQube or GitHub Advanced Security.
*   **Container Image Scanning:** AWS ECR built-in scanning, Clair, or Trivy.
*   **Dependency Scanning:** Renovatebot and Snyk for identifying vulnerable dependencies.

### 6.6. Infrastructure as Code (IaC)
*   **Tool:** Terraform for managing AWS resources (VPC, EKS cluster, RDS, DynamoDB, S3, IAM, etc.).

### 6.7. API Gateway & Management
*   **Internal/External:** AWS API Gateway (REST APIs) for acting as the single entry point, handling routing, authentication, rate limiting, and caching.

## 7. Communication & Collaboration Tools

*   **Project Management:** Jira/Confluence (for requirements, backlog, documentation).
*   **Team Communication:** Slack/Microsoft Teams.
*   **Code Review:** GitHub Pull Requests.
*   **Design Tool:** Figma (for UI/UX design collaboration).

## 8. Integration Technologies

*   **API Standard:** RESTful APIs (following OpenAPI Specification for documentation).
*   **Authentication:** OAuth 2.0 (for third-party integrations), JWT (for internal microservice communication and user authentication via Cognito).
*   **Webhooks:** Outgoing webhooks implemented via SNS/EventBridge for notifying external systems of events.
*   **SDKs/Libraries:** Official SDKs for integrating with third-party services like email clients (e.g., Google OAuth for Gmail, Microsoft Graph for Outlook).

## 9. Local Development Environment

*   **Docker Compose:** For running local instances of microservices and dependencies (database, Redis, etc.).
*   **IDE:** VS Code with relevant extensions (Python, Pylance, Prettier, ESLint, Docker, Kubernetes).
*   **Linters/Formatters:** Black, Flake8 (Python); ESLint, Prettier (TypeScript/React).

This comprehensive technology stack provides a robust foundation for building the Universal CRM, allowing for an iterative development process that can adapt to evolving requirements and scale alongside business growth.
