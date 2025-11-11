**Technology Stack Specification: Notes Service with Auth**

This document outlines the detailed technology choices and implementation guidelines for the "Notes Service with Auth" project, aligning with the Architecture Design Records (ADRs).

---

**1. Development & Build Environment**

*   **Programming Language (Backend):** Python 3.9+
    *   **Justification:** High developer productivity, large ecosystem, good for microservices.
*   **Programming Language (Frontend):** JavaScript / TypeScript
    *   **Justification:** Standard for modern web development, type safety with TypeScript improves maintainability.
*   **Package Manager (Backend):** Poetry or Pipenv
    *   **Justification:** Better dependency management, virtual environment integration.
*   **Package Manager (Frontend):** npm or Yarn
    *   **Justification:** Standard for JavaScript ecosystem.
*   **Version Control:** Git
    *   **Platform:** GitHub/GitLab/Bitbucket (e.g., GitHub for public/private repositories)
    *   **Justification:** Industry standard, robust collaboration features.
*   **IDE:** VS Code, PyCharm, WebStorm (developer preference)

---

**2. Backend Services**

**2.1. API Gateway**

*   **Technology:** Nginx or Envoy Proxy (for more advanced features like service mesh)
    *   **Justification:** High performance, robust reverse proxy, load balancing, and SSL termination capabilities. Envoy provides more advanced traffic management if needed later.
*   **Framework (for authentication enforcement/custom logic if Python-based):** FastAPI / Starlette
    *   **Justification:** Asynchronous, high-performance, easy to define middleware for JWT validation and routing.

**2.2. Authentication Service**

*   **Framework:** FastAPI (Python)
    *   **Justification:** Fast, asynchronous, built-in OpenAPI/Swagger documentation, modern Python framework.
*   **Authentication Libraries:** `python-jose` (for JWT handling), `passlib` (for password hashing - bcrypt recommended)
*   **Database ORM:** SQLAlchemy with `asyncpg` driver
    *   **Justification:** Robust ORM for PostgreSQL, supports asynchronous operations.
*   **Database:** PostgreSQL 14+
    *   **Justification:** Relational database chosen in ADR-003, strong ACID compliance, widely supported, mature.

**2.3. Notes Service**

*   **Framework:** FastAPI (Python)
    *   **Justification:** Consistency with Authentication Service, high performance.
*   **Database ODM:** `motor` (asynchronous Python driver for MongoDB)
    *   **Justification:** Asynchronous, idiomatic Python interface for MongoDB.
*   **Database:** MongoDB 6+ (Document Database)
    *   **Justification:** NoSQL document database chosen in ADR-003, flexible schema, good for scaling note content.
*   **Search/Indexing (Future Consideration for advanced search):** Elasticsearch (external service)
    *   **Justification:** Provides powerful full-text search capabilities and complex query support. May be integrated later if basic database search is insufficient.

---

**3. Frontend / Client Application**

*   **Framework:** React (with Next.js for server-side rendering/static site generation) or Vue.js (with Nuxt.js)
    *   **Justification:** Modern, component-based frameworks, strong community support, good for building single-page applications. Next.js/Nuxt.js provide SEO benefits, better performance, and simplified routing.
*   **State Management:** Redux Toolkit (for React) or Vuex/Pinia (for Vue.js)
    *   **Justification:** Centralized state management for complex UI interactions.
*   **Styling:** Tailwind CSS or Styled Components
    *   **Justification:** Utility-first CSS framework (Tailwind) for rapid UI development or CSS-in-JS (Styled Components) for component-level styling.
*   **HTTP Client:** Axios or native `fetch` API
    *   **Justification:** Robust, promise-based HTTP client for API interactions.
*   **Rich Text Editor (Library):** React Rich Text Editor, Quill, or TinyMCE
    *   **Justification:** Provides a user-friendly interface for note content editing.
*   **Authentication (Client side):** Store JWT access token in browser memory or secure HTTP-only cookie (for refresh token). Avoid `localStorage` for access tokens due to XSS vulnerability.

---

**4. Infrastructure & Operations**

*   **Containerization:** Docker
    *   **Justification:** Standard for packaging applications and their dependencies, ensuring consistency across environments. Each microservice will be containerized.
*   **Container Orchestration:** Docker Compose (local development) / Kubernetes (production)
    *   **Justification:** Docker Compose for multi-container local setups; Kubernetes for production-grade scaling, self-healing, and management of microservices.
*   **Cloud Provider:** AWS / Google Cloud Platform (GCP) / Azure
    *   **Justification:** Industry-leading cloud providers offering a wide range of services (compute, managed databases, networking). Specific choice depends on budget, team expertise, and existing infrastructure.
    *   **Recommended Managed Services:**
        *   **AWS:** RDS PostgreSQL, DocumentDB (for MongoDB compatibility), EKS (Kubernetes), EC2, Lambda, API Gateway
        *   **GCP:** Cloud SQL for PostgreSQL, Firestore/MongoDB Atlas (for MongoDB), GKE (Kubernetes), Compute Engine, Cloud Functions, Cloud Load Balancing
*   **CI/CD:** GitHub Actions / GitLab CI / Jenkins
    *   **Justification:** Automate testing, building, and deployment of services.
*   **Monitoring & Logging:** Prometheus & Grafana (observability), ELK Stack (Elasticsearch, Logstash, Kibana) or cloud-native logging services (CloudWatch, Stackdriver Logging)
    *   **Justification:** Essential for tracking system health, performance, and troubleshooting.
*   **DNS & Load Balancing:** Cloud Provider's native services (AWS Route 53, GCP Cloud DNS, AWS/GCP Load Balancers)

---

**5. Security Considerations**

*   **Data Encryption:**
    *   **Data in Transit:** HTTPS/TLS 1.2+ for all communication (client-server, inter-service).
    *   **Data at Rest:** Database encryption (enable native features in PostgreSQL, MongoDB). File system encryption for any stored attachments.
*   **Password Hashing:** `bcrypt` with a strong work factor. Never store plain passwords.
*   **Input Validation:** Strict validation on all API inputs to prevent injection attacks (SQL injection, XSS).
*   **Rate Limiting:** Implement rate limiting on API Gateway and authentication endpoints to prevent brute-force attacks.
*   **CORS:** Properly configure Cross-Origin Resource Sharing (CORS) policies.
*   **Dependency Scanning:** Regularly scan for known vulnerabilities in third-party libraries (e.g., Snyk, Dependabot).
*   **Secrets Management:** Use environment variables, Kubernetes Secrets, or dedicated secrets management services (e.g., AWS Secrets Manager, GCP Secret Manager) for sensitive credentials.
*   **Service Accounts/IAM:** Implement least privilege principle for all service accounts and user roles.

---

**6. Future Considerations / Scalability**

*   **Asynchronous Processing/Queue:** Kafka or RabbitMQ for tasks like sending notifications, processing attachments, or audit logging.
*   **Caching:** Redis for frequently accessed data, to reduce database load.
*   **Real-time Features:** WebSockets (e.g., via Socket.IO) for collaborative editing or real-time presence.
*   **Full-Text Search:** Elasticsearch for advanced, fast search capabilities across notes.
*   **File Storage:** AWS S3, GCP Cloud Storage, or similar object storage for note attachments.

---

**7. Coding Standards & Best Practices**

*   **Linting:** Black (Python formatter), ESLint (JavaScript/TypeScript).
*   **Type Hinting:** Extensive use of Python type hints and TypeScript for improved code clarity and error detection.
*   **Unit & Integration Testing:** Comprehensive test coverage for all services.
*   **API Documentation:** OpenAPI/Swagger for backend APIs (FastAPI generates this automatically), Storybook for frontend components.
*   **Code Reviews:** Mandatory code reviews for all changes.
*   **READMEs & Documentation:** Clear project structure, setup instructions, and deployment guides.

This technology stack provides a robust, scalable, and maintainable foundation for the Notes Service with Auth, allowing for future expansion and feature development.
