## Technology Stack Specification: CRM Dashboard

This document details the specific technologies, frameworks, and tools to be used for the CRM Dashboard project, aligning with the Architecture Design Records and PRD requirements.

### 1. Cloud Infrastructure & DevOps

*   **Cloud Provider:** AWS (Amazon Web Services)
*   **Compute:**
    *   **Backend Microservices:** Amazon ECS (Elastic Container Service) with AWS Fargate launch type (for serverless container management). This removes the need to manage EC2 instances.
    *   **Serverless Functions:** AWS Lambda (for event-driven tasks, e.g., Salesforce webhook processing).
    *   **Frontend Hosting:** AWS S3 (Static Website Hosting) for built assets.
    *   **CDN:** Amazon CloudFront for content delivery, caching, and accelerating frontend delivery.
*   **Database:** Amazon RDS for PostgreSQL (Managed relational database service)
*   **API Gateway:** Amazon API Gateway
*   **Load Balancing:** Application Load Balancer (ALB) - used implicitly by ECS or directly for specific public endpoints.
*   **Queuing:** Amazon SQS (Simple Queue Service) for asynchronous messaging between services.
*   **Monitoring & Logging:**
    *   **Logging:** Amazon CloudWatch Logs (centralized log aggregation).
    *   **Monitoring:** Amazon CloudWatch (metrics, alarms) and potentially Prometheus/Grafana deployed within ECS for advanced metrics visualization.
    *   **Tracing:** AWS X-Ray for distributed transaction tracing across microservices.
*   **Containerization:** Docker
*   **CI/CD:** AWS CodePipeline (or GitLab CI/CD, GitHub Actions with AWS integrations) for automated build, test, and deployment.
*   **Infrastructure as Code (IaC):** AWS CloudFormation or Terraform for defining and managing AWS resources.
*   **Source Code Management:** Git (e.g., GitHub, GitLab, AWS CodeCommit).

### 2. Backend Services

*   **Primary Language:** Python
*   **Framework:**
    *   **FastAPI:** For building high-performance, asynchronous RESTful APIs. Its automatic interactive API documentation (Swagger UI/Redoc) is a significant benefit.
*   **ORM:** SQLAlchemy (with Asyncio support) for database interactions.
*   **Data Serialization:** Pydantic (integrated with FastAPI) for data validation and serialization.
*   **Authentication & Authorization:**
    *   Integration with OIDC libraries (e.g., `authlib` or `python-jose`) for token validation.
    *   Custom middleware for JWT validation and RBAC enforcement based on claims.
*   **Salesforce Integration:**
    *   `simple-salesforce` Python library for Salesforce REST API interaction.
    *   Consider `beatbox` or `suds-py` if deep SOAP API features are needed, but prioritize REST.
    *   Utilize Salesforce Platform Events or Webhooks for near real-time updates.
*   **Notifications:** Python libraries for email (e.g., `smtplib`) or integration with a third-party notification service (e.g., SendGrid, SES).
*   **Task Queues:** Celery (with Redis or SQS as a broker) for background tasks (e.g., scheduled Salesforce data syncs, complex forecasting calculations).

### 3. Frontend Application

*   **JavaScript Framework:** React.js (latest stable version)
*   **Language:** TypeScript (for improved code quality, maintainability, and developer experience).
*   **State Management:** React Query (for server state management, caching, and synchronization) and/or Zustand/Jotai (for simple client-side global state). Redux Toolkit is an option for more complex global state needs.
*   **Styling:**
    *   **CSS-in-JS:** Styled Components or Emotion.
    *   **UI Component Library:** Chakra UI or Material-UI for pre-built, accessible, and themeable components.
*   **Charting & Data Visualization:**
    *   **Recharts:** For declarative, component-based charts with React.
    *   **Chart.js / Nivo:** Good alternatives for diverse chart types if Recharts lacks specific needs.
    *   **D3.js:** To be used sparingly for highly custom or complex visualizations that cannot be easily achieved with other libraries.
*   **Form Management:** React Hook Form for efficient form handling and validation.
*   **Routing:** React Router v6 for client-side navigation.
*   **Build Tool:** Vite or Webpack (configured for React and TypeScript).
*   **API Client:** Axios or Fetch API (with wrappers for authentication and error handling).
*   **Drag-and-Drop:** React Beautiful DND or React DnD for customizable widget layouts.
*   **Internationalization (Optional, for future):** React-i18next.

### 4. Database Schema (PostgreSQL)

*   **Users Table:**
    *   `id (PK)`
    *   `external_id (e.g., Salesforce User ID)`
    *   `username`
    *   `email`
    *   `role_id (FK to Roles table)`
    *   `last_login_at`
    *   `created_at`
    *   `updated_at`
*   **Roles Table:**
    *   `id (PK)`
    *   `name (e.g., 'Sales Rep', 'Sales Manager')`
    *   `description`
*   **UserDashboardConfigs Table:**
    *   `id (PK)`
    *   `user_id (FK)`
    *   `layout_json (JSONB for widget positions, sizes)`
    *   `widget_settings_json (JSONB for personalized widget filters)`
    *   `created_at`
    *   `updated_at`
*   **CrmData Tables (e.g., Opportunity, Account, Contact, Activity):**
    *   Mirror relevant Salesforce object structures, but optimized for dashboard queries.
    *   Include a `salesforce_id` column for mapping back to Salesforce.
    *   Include `last_synced_at` timestamp for data freshness tracking.
    *   Consider indexing heavily used columns for filtering and sorting.

### 5. Security Practices

*   **OWASP Top 10:** Adherence to secure coding practices to mitigate common web vulnerabilities (XSS, CSRF, Injection Flaws).
*   **HTTPS:** Enforced for all communication (API Gateway, CloudFront).
*   **Data Encryption:**
    *   **In transit:** TLS 1.2+ for all data exchanged.
    *   **At rest:** AWS RDS encryption, S3 bucket encryption.
*   **Authentication:** OIDC with strong identity providers.
*   **Authorization:** JWT-based RBAC enforced at API Gateway and microservice level.
*   **Secrets Management:** AWS Secrets Manager for storing API keys, database credentials, etc.
*   **Input Validation:** Strict server-side validation on all API inputs.
*   **Rate Limiting:** Implemented at API Gateway and potentially per-service.
*   **Security Scans:** Regular static analysis (SAST) and dynamic analysis (DAST) scans during CI/CD.

### 6. Code Quality & Standards

*   **Linting:** ESLint (for JavaScript/TypeScript), Prettier (for code formatting), Flake8/Black (for Python).
*   **Testing:**
    *   **Unit Tests:** Jest/React Testing Library (Frontend), Pytest (Backend).
    *   **Integration Tests:** Postman collections, Pytest for backend service integrations.
    *   **End-to-End Tests:** Cypress or Playwright for critical user flows.
*   **Documentation:**
    *   **API Documentation:** OpenAPI/Swagger generated by FastAPI.
    *   **Code Comments:** JSDoc (TypeScript), Sphinx/Google Style Docstrings (Python).
    *   **Confluence/Wiki:** For system design, architecture diagrams, deployment guides, etc.

### 7. Deployment Strategy

*   **Containerized Microservices:** Docker images for each backend service.
*   **CI/CD Pipeline:**
    1.  Code commit triggers pipeline.
    2.  Unit tests, linting.
    3.  Docker image build and push to Amazon ECR (Elastic Container Registry).
    4.  Infrastructure deployment/updates via CloudFormation/Terraform.
    5.  Deployment to ECS Fargate (rolling updates).
    6.  Automated smoke tests post-deployment.
*   **Frontend Deployment:**
    1.  Build React application.
    2.  Upload static assets to S3 bucket.
    3.  Invalidate CloudFront cache.
    4.  A/B deployments or phased rollouts for major changes.

This comprehensive stack provides a robust foundation for building a scalable, high-performance, and maintainable CRM Dashboard as described in the PRD.
