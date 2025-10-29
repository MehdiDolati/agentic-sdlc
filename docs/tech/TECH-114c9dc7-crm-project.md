# RentRight CRM: Technology Stack Specification

**Project Name:** RentRight CRM
**Project ID:** 114c9dc7
**Version:** 1.0
**Date:** October 27, 2023
**Author:** AI Software Architect

---

## 1. Cloud Platform & Infrastructure

*   **Cloud Provider:** Amazon Web Services (AWS)
*   **Container Orchestration:** AWS Elastic Kubernetes Service (EKS) for managed Kubernetes. Alternatively, AWS Fargate for serverless containers if the operational overhead of EKS proves too high for initial team size.
*   **Compute:**
    *   Microservices: Docker containers running on EKS/Fargate.
    *   Serverless Functions (for specific, event-driven tasks): AWS Lambda.
*   **Networking:** Amazon VPC, AWS Load Balancers (ALB, NLB), Route 53 (DNS).
*   **Content Delivery Network (CDN):** AWS CloudFront for static assets and potentially API caching.
*   **Infrastructure as Code (IaC):** Terraform for defining and managing AWS resources.

## 2. Backend Services

*   **Primary Programming Language:** Python
*   **Web Framework:** FastAPI (for its performance, async capabilities, and Pydantic integration)
*   **ORM/Database Toolkit:** SQLAlchemy (for ORM capabilities) + Alembic (for database migrations)
*   **Authentication/Authorization Library:** `python-jose` for JWT handling, `fastapi-users` or similar for user management if not using a custom IAM service.
*   **Asynchronous Tasks/Background Jobs:** Celery (with Redis or SQS as broker)
*   **API Documentation:** Automatically generated OpenAPI/Swagger UI by FastAPI.
*   **Test Framework:** Pytest

## 3. Frontend Application

*   **JavaScript Library:** React.js
*   **State Management:** React Context API augmented with `useReducer` for simpler cases, or Redux Toolkit for more complex global state management (e.g., user session, notifications).
*   **Routing:** React Router DOM
*   **Styling:** Tailwind CSS for utility-first CSS, or Styled Components/Emotion for component-scoped styling.
*   **Component Library (Optional but Recommended):** Material UI or Ant Design for accelerating UI development and ensuring consistency.
*   **Form Management:** React Hook Form or Formik.
*   **API Client:** Axios or Fetch API.
*   **Build Tool:** Vite (for faster development builds) or Webpack (for production builds, often pre-configured with Create React App).
*   **TypeScript:** Optional but recommended for improved maintainability and type safety, especially on larger projects.
*   **Test Framework:** Jest (for unit tests), React Testing Library (for component integration tests).

## 4. Databases

*   **Primary Relational Database:** PostgreSQL (provisioned via AWS RDS)
    *   **Use Cases:** Customer profiles, rental history, lead management, user data, configurations, reporting data.
*   **NoSQL Database:** Amazon DynamoDB
    *   **Use Cases:** Customer interaction logs (non-transactional, high volume), marketing campaign event tracking, temporary data storage, preferences.
*   **In-memory Cache:** Amazon ElastiCache (Redis)
    *   **Use Cases:** Session management (if not using stateless JWT for specific components), frequently accessed read-heavy data (e.g., lookup tables, dashboard KPIs), rate limiting.

## 5. Messaging & Communication

*   **Message Queue:** AWS SQS (Simple Queue Service)
    *   **Use Cases:** Asynchronous processing, decoupling services, task queues (e.g., sending bulk emails, generating complex reports, processing rental returns in background).
*   **Publish/Subscribe Service:** AWS SNS (Simple Notification Service)
    *   **Use Cases:** Event broadcasting (e.g., "customer created" event, "rental completed" event), triggering multiple subscriber services.
*   **Email Service:** AWS SES (Simple Email Service) or SendGrid/Mailgun (third-party integration via API).
*   **SMS Gateway:** Twilio or vonage (third-party integration via API).

## 6. API Management & Security

*   **API Gateway:** Amazon API Gateway
    *   **Use Cases:** Exposing REST/WebSocket APIs for frontend and external integrations, request routing, authentication enforcement, throttling, caching, monitoring.
*   **User Identity & Access Management:** AWS Cognito User Pools (for user authentication) integrated with a dedicated IAM microservice.
*   **Secrets Management:** AWS Secrets Manager for database credentials, API keys, and other sensitive configurations.
*   **Web Application Firewall (WAF):** AWS WAF for protecting against common web exploits.
*   **SSL/TLS:** AWS Certificate Manager (ACM).

## 7. Monitoring, Logging & Tracing

*   **Logging:** AWS CloudWatch Logs (centralized structured logging, e.g., JSON logs from applications).
*   **Monitoring:** AWS CloudWatch (metrics, alarms, dashboards), Prometheus + Grafana (for deeper application-level metrics).
*   **Application Performance Monitoring (APM) & Distributed Tracing:** AWS X-Ray (integrated with API Gateway, Lambda, EC2/EKS) or Datadog/New Relic (third-party).
*   **Alerting:** AWS CloudWatch Alarms integrated with SNS for notifications (e.g., email, PagerDuty).

## 8. CI/CD & Development Tools

*   **Version Control:** Git (GitHub/GitLab/AWS CodeCommit).
*   **CI/CD Pipeline:** AWS CodePipeline, AWS CodeBuild, AWS ECR (Elastic Container Registry). Alternatively, GitHub Actions or GitLab CI/CD.
*   **Container Runtime:** Docker
*   **Local Development Environment:** Docker Compose for running dependent services locally.
*   **IDE:** VS Code, PyCharm, WebStorm.

## 9. Data Processing & Analytics

*   **Data Lake (Future consideration for advanced analytics):** AWS S3, AWS Glue.
*   **Reporting (Current):** Direct SQL queries, dedicated reporting APIs from microservices, potentially a separate read-replica database instance for reporting.

## 10. Compliance & Security (General Guidelines)

*   **Data Encryption:** All data encrypted at rest (AWS RDS encryption, S3 encryption, DynamoDB encryption) and in transit (SSL/TLS for all communication paths).
*   **Access Control:** Principle of least privilege enforced via AWS IAM roles and policies.
*   **Audit Logging:** AWS CloudTrail for API activity, CloudWatch Logs for application logs, database audit logs.
*   **Compliance:** Design will adhere to GDPR, CCPA, and relevant local data protection regulations, including mechanisms for data subject rights (access, erasure). PCI DSS considerations for payment data if directly handled (preferring payment gateway integration to offload PCI burden).

---
