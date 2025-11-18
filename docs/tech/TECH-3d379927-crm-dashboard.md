## TECHNOLOGY STACK SPECIFICATION: CRM Dashboard

**Document Version:** 1.0
**Date:** October 26, 2023
**Project:** CRM Dashboard

---

### 1. Introduction

This document specifies the technology stack for the CRM Dashboard project. It details the chosen frameworks, libraries, tools, and infrastructure components across frontend, backend, data, and deployment layers, aligning with the Architecture Design Records (ADRs) and Product Requirements Document (PRD).

### 2. Overall Principles

*   **Cloud-Native:** Leverage managed services from the chosen cloud provider for scalability, reliability, and reduced operational overhead.
*   **Microservices-Oriented:** Design backend services with clear responsibilities and communication boundaries.
*   **Component-Based Frontend:** Build UI using reusable components for maintainability and rapid development.
*   **API-First:** All services expose well-defined RESTful APIs.
*   **Security by Design:** Implement security best practices at every layer.
*   **Observability:** Integrate logging, monitoring, and tracing from the outset.
*   **Automation:** Utilize CI/CD for automated testing, building, and deployment.

### 3. Cloud Platform (PaaS/IaaS)

**Decision:** AWS (Amazon Web Services)

**Justification:**
*   Extensive suite of managed services relevant to microservices, databases, and container orchestration.
*   Mature ecosystem, robust documentation, and strong community support.
*   Offers strong compliance and security features.

**Key AWS Services:**
*   **Compute:** Amazon Elastic Kubernetes Service (EKS) for container orchestration, AWS Fargate (serverless containers) for specific services or background tasks.
*   **Networking:** Amazon VPC, ALB (Application Load Balancer), Route 53 (DNS).
*   **Databases:** Amazon RDS for PostgreSQL, Amazon ElastiCache for Redis.
*   **Storage:** Amazon S3 for static assets, EBS for persistent volumes (if needed).
*   **Messaging:** Amazon SQS/SNS for inter-service communication and event processing.
*   **Monitoring & Logging:** Amazon CloudWatch, AWS X-Ray (for distributed tracing).
*   **Security:** AWS IAM (Identity and Access Management), AWS WAF, AWS Secrets Manager.
*   **API Management:** Amazon API Gateway (if a public API gateway is needed before ALB).

### 4. Frontend Technology Stack

**Framework:** React.js (latest stable version)

**Core Libraries/Tools:**
*   **Language:** TypeScript (for type safety and improved maintainability).
*   **State Management:**
    *   **Context API + `useReducer`:** For local component state and simple shared data.
    *   **Zustand / Recoil:** For global application state, preferred for its simplicity and performance over Redux for current scope. Redux Toolkit could be considered if complexity warrants it in future phases.
*   **Routing:** React Router DOM (latest stable version).
*   **Styling:**
    *   **CSS-in-JS (e.g., Emotion / Styled Components):** For component-scoped styling.
    *   **Utility-first CSS framework (e.g., Tailwind CSS):** For rapid UI development and consistent design system adherence.
*   **UI Component Library:** Material-UI (MUI) V5+ / Ant Design
    *   **Justification:** Provides a comprehensive set of pre-built, accessible, and responsive UI components compliant with modern design principles (NFR4.2.2, NFR4.2.4). Accelerates development.
*   **Data Fetching:** React Query / SWR
    *   **Justification:** Simplifies data fetching, caching, synchronization, and error handling, reducing boilerplate.
*   **Data Visualization:** Recharts / Chart.js
    *   **Justification:** Powerful and flexible charting libraries for displaying KPIs and reports graphically (FR3, FR6).
*   **Form Management:** React Hook Form (for performant and flexible form handling).
*   **Internationalization (i18n):** React-i18next (if multi-language support is required).
*   **Testing:**
    *   **Unit/Component:** Jest, React Testing Library.
    *   **End-to-End:** Cypress.
*   **Build Tool:** Vite / Webpack (configured via Create React App or similar boilerplate).
*   **Code Quality:** ESLint, Prettier.

### 5. Backend Technology Stack

**Language:** Node.js (latest LTS version)

**Frameworks/Libraries (Per Microservice):**
*   **Auth Service:**
    *   **Framework:** Express.js (for lightweight API endpoints).
    *   **Authentication:** Passport.js (for integrating with CRM OAuth/API key validation).
    *   **JWT:** `jsonwebtoken` (for internal service authentication).
*   **CRM Integration Service:**
    *   **Framework:** Express.js.
    *   **HTTP Client:** Axios / node-fetch (for robust CRM API communication).
    *   **Message Queue Client:** AWS SDK for SQS/SNS.
    *   **Data Transformation:** Custom utility functions to map CRM data to internal models.
*   **Dashboard Service:**
    *   **Framework:** Express.js.
    *   **ORM/ODM:** TypeORM / Mongoose (if using MongoDB for user preferences).
    *   **Caching:** `ioredis` (Redis client).
*   **Metrics & Analytics Service:**
    *   **Framework:** NestJS (for structured, opinionated framework for complex logic).
    *   **Caching:** `ioredis`.
    *   **Scheduler:** Node-schedule / BullMQ (for background jobs to pre-compute metrics).
    *   **Database Client:** `pg` (PostgreSQL client) or TypeORM.
*   **Alerts & Notifications Service:**
    *   **Framework:** Express.js / NestJS.
    *   **Message Brokers:** AWS SQS for event ingestion.
    *   **Notification Gateway:** Integrations with email/SMS services (e.g., AWS SES, Twilio) for sending alerts.
*   **Common Libraries:**
    *   **Logger:** Winston / Pino.
    *   **Validation:** Joi / class-validator.
    *   **Testing:** Jest, Supertest (for API integration tests).
    *   **ORM/ODM:** TypeORM (for PostgreSQL) or Mongoose (for MongoDB, if applicable).
    *   **Type Management:** TypeScript.

### 6. Data Layer

**6.1. Primary Database:**
*   **Decision:** PostgreSQL on Amazon RDS
*   **Justification:**
    *   Robust, open-source relational database.
    *   Excellent support for complex queries, transactions, and data integrity (NFR4.7.1).
    *   Managed service on AWS reduces operational overhead.
    *   Suitable for storing structured data like user preferences, dashboard configurations, alert rules, and potentially long-term aggregated metrics (if not directly sourced from CRM).

**6.2. Caching Layer:**
*   **Decision:** Redis on Amazon ElastiCache
*   **Justification:**
    *   In-memory data store, highly optimized for caching and real-time data access (ADR 004).
    *   Supports various data structures (strings, hashes, lists) useful for different caching needs.
    *   Managed service on AWS for high availability and scalability.

**6.3. Data Storage (for large reports/exports):**
*   **Decision:** Amazon S3
*   **Justification:**
    *   Highly durable, scalable, and cost-effective object storage for generated reports (FR6.2) or large datasets that need to be temporarily stored.

### 7. CRM Integration

*   **Methodology:**
    1.  **Direct API Integration:** Primary method for real-time data access. Authentication will be handled via OAuth 2.0 flows or API keys provided by the CRM vendor.
    2.  **Webhooks:** If the CRM supports webhooks, the CRM Integration Service will expose an endpoint to receive real-time notifications for critical events (e.g., opportunity stage change, new lead).
    3.  **Scheduled Polling:** For data that doesn't require immediate real-time updates or if webhooks are not available, a scheduled polling mechanism will fetch updates from the CRM API.
*   **CRM Specifics:** To be determined during technical discovery (e.g., Salesforce, HubSpot, Dynamics 365, etc.). This will influence specific API client libraries and data model mappings.
*   **Data Models:** Internal data models will be defined in TypeScript to standardize data from various CRM API responses into a consistent format used across microservices.

### 8. Containerization & Orchestration

*   **Containerization:** Docker
    *   **Justification:** Standardizes development, testing, and deployment environments across all microservices. Ensures consistency between local development and production.
*   **Orchestration:** Kubernetes (via AWS EKS)
    *   **Justification:** Provides a robust platform for deploying, scaling, and managing containerized applications (ADR 002, NFR4.6.2). Offers self-healing, rolling updates, and resource management.

### 9. CI/CD (Continuous Integration/Continuous Deployment)

*   **Tool:** GitHub Actions / AWS CodePipeline + CodeBuild
    *   **Justification:** Automates the build, test, and deployment process, ensuring rapid and reliable delivery of new features and fixes.
*   **Pipeline Steps (Typical):**
    1.  **Code Commit:** Trigger on push to specific branches.
    2.  **Linting & Formatting:** Enforce code quality standards.
    3.  **Unit Tests:** Run all unit and component tests.
    4.  **Integration Tests:** Run API integration tests.
    5.  **Build & Dockerize:** Build frontend assets and backend microservice Docker images.
    6.  **Image Push:** Push Docker images to Amazon Elastic Container Registry (ECR).
    7.  **Deployment:** Update Kubernetes deployments on EKS.
    8.  **E2E Tests:** Run post-deployment end-to-end tests.

### 10. Monitoring, Logging & Alerting

*   **Logging:** Centralized logs to AWS CloudWatch Log Groups.
    *   **Libraries:** Winston / Pino for structured logging in Node.js.
*   **Monitoring:** AWS CloudWatch (for infrastructure metrics), Prometheus (within EKS for application metrics).
    *   **Dashboarding:** Grafana (for visualizing metrics from CloudWatch and Prometheus).
*   **Alerting:** AWS CloudWatch Alarms, integrated with SNS for notifications (email, PagerDuty, Slack).
*   **Tracing:** AWS X-Ray (for distributed tracing across microservices).

### 11. Security

*   **Authentication:** JWT-based for inter-service communication; OAuth 2.0/API Key for CRM integration and client-to-API gateway.
*   **Authorization:** Role-Based Access Control (RBAC) implemented in the Auth Service and enforced at the API Gateway/Service level.
*   **Data Encryption:**
    *   **In Transit:** HTTPS/TLS 1.2+ for all network communication (ALB to frontend, client to API, inter-service communication).
    *   **At Rest:** Encryption enabled for RDS, S3, ElastiCache volumes and data. Secrets managed by AWS Secrets Manager.
*   **Vulnerability Scanning:** Implement static application security testing (SAST) and dynamic application security testing (DAST) in CI/CD pipeline.
*   **WAF:** AWS WAF to protect against common web vulnerabilities (OWASP Top 10).

### 12. Development Tools

*   **IDE:** Visual Studio Code (with recommended extensions for TypeScript, React, Node.js, Docker, Kubernetes).
*   **Version Control:** Git on GitHub / AWS CodeCommit.
*   **Package Manager:** Yarn / npm.
*   **Documentation:** Swagger/OpenAPI for API documentation.

### 13. Future Considerations

*   **Data Lake/Warehouse:** For advanced analytics, machine learning, and long-term historical data, a separate data lake using AWS S3, Athena, and Redshift could be implemented.
*   **Serverless Functions:** AWS Lambda could be introduced for specific event-driven tasks or background processing to further optimize costs for infrequent workloads.
*   **GraphQL:** If frontend requirements for flexible data fetching become very complex, GraphQL could be considered for the API layer.
