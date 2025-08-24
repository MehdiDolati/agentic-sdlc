# Product Requirements Document — Build a notes service with auth

    ## Problem
    Build a notes service with auth

    ## Goals / Non-goals
    - **Goals**: Deliver the requested functionality with tests and docs.
    - **Non-goals**: Features not explicitly requested; large-scale infra changes.

    ## Personas & Scenarios
    - Primary Persona: End-user
    - Scenario: A user interacts with the system to accomplish: "Build a notes service with auth"

    ## Requirements (Must / Should / Could)
    **Must**
    - Implement the primary endpoint(s) described by the request
- Write unit tests with coverage above the gate
- Add authentication flow (basic token or session)

    **Should**
    - Add basic error handling and input validation

    **Could**
    - Add OpenAPI docs and a simple UI stub

    ## Acceptance Criteria
    - Given the service is running, When I call the primary endpoint, Then I receive a 200 response.
- Given invalid input, When I call the endpoint, Then I receive a 4xx response with an error body.

    ## Stack Summary (Selected)
    - Language: **python**
    - Backend Framework: **fastapi**
    - Frontend: **nextjs**
    - Database: **postgres**
    - Deployment: **kubernetes**

    ## Quality & Policy Gates
    - Coverage gate: **0.8**
    - Risk threshold: **medium**
    - Approvals: **{'prod_deploy': 'auto'}**

    ## Risks & Assumptions
    - Assumes default adapters and templates for the chosen stack are available.
    - Security scanning and policy checks run in CI before deploy.
