# Technology Stack Specification
## LLM Project Test Feature

### 1. Core Programming Language
*   **Choice:** Python 3.9+
*   **Reasoning:** Dominant language in the LLM/AI ecosystem with extensive libraries, strong community support, and excellent integration capabilities with LLM providers. Supports rapid prototyping and scripting.
*   **Guidelines:** Adhere to PEP 8 for code style. Utilize virtual environments for dependency management.

### 2. LLM Interaction Libraries
*   **Choice:** `langchain` (or similar orchestration libraries) / Direct API client libraries.
*   **Reasoning:**
    *   `langchain`: Provides a standardized interface for interacting with various LLM providers, abstracting away differences in API calls, handling retries, and providing useful utilities like prompt templating. While the ADRs state "not an orchestration platform," `langchain`'s core LLM interaction features are highly relevant without adopting its full chain/agent capabilities.
    *   Direct API clients (e.g., `openai`, `anthropic`, `google-cloud-aiplatform` SDKs): For maximum control and when specific features of a provider are not readily available through `langchain`. Initially, we might start with direct clients for simplicity and integrate `langchain` if complexity grows.
*   **Guideline:** Prioritize direct API clients for initial integration with primary LLM providers (e.g., OpenAI, Anthropic). Evaluate `langchain` for future extensibility and simplified multi-provider support. Implement a `LLMProviderInterface` abstract class to allow switching implementations easily.

### 3. Prompt Templating
*   **Choice:** Python's f-strings or Jinja2.
*   **Reasoning:**
    *   f-strings: Simple and built-in for basic variable substitution.
    *   Jinja2: More powerful for complex templating scenarios, conditional logic, and loops, which might be useful for advanced prompt engineering.
*   **Guideline:** Start with f-strings for basic variable substitution in `prompt_template`. Adopt Jinja2 if more sophisticated prompt logic is required based on `prompt_variables`. The test runner should handle the templating step before sending the prompt to the LLM.

### 4. Test Case Definition Format
*   **Choice:** JSON (JavaScript Object Notation).
*   **Reasoning:** Human-readable, widely supported, easily parsed and schema-validated in Python. Good for version control.
*   **Guideline:** Define a `TestDefinitionSchema` using `pydantic` for strict validation of test case JSON files. Store test cases in a dedicated `test_cases/` directory.

### 5. Persistent Storage for Test Results
*   **Choice:** PostgreSQL (for shared environments/CI/CD) and SQLite (for local development/simpler CI).
*   **Reasoning:**
    *   PostgreSQL: Robust, ACID-compliant, excellent for structured data, well-supported by ORMs, scalable.
    *   SQLite: File-based, zero-configuration, ideal for local development, rapid prototyping, and lightweight CI/CD scenarios where a full DB server is overkill.
*   **ORM:** SQLAlchemy 2.0+ with Alembic for migrations.
*   **Guideline:** Develop against an abstract `ResultStore` interface. Implement concrete classes for `PostgresResultStore` and `SQLiteResultStore`. Use environment variables to configure the active database. Define a clear database schema mirroring `ADR 003`'s decision.

### 6. Command Line Interface (CLI)
*   **Choice:** `Click` or `Argparse`.
*   **Reasoning:**
    *   `Click`: Modern, intuitive, and highly composable framework for building beautiful command-line interfaces.
    *   `Argparse`: Built-in Python library, suitable for simpler CLIs.
*   **Guideline:** Prioritize `Click` for a richer user experience, subcommand structure (e.g., `llm-test run`, `llm-test results view`), and easier extensibility. Implement commands for:
    *   `llm-test run [test_id_or_pattern]`: Executes specified tests.
    *   `llm-test results list`: Lists recent test runs.
    *   `llm-test results view [run_id]`: Displays detailed results for a specific run.

### 7. Evaluation & Assertions
*   **Choice:** Python's built-in `re` module for regex matching, custom Python functions for keyword/semantic checks.
*   **Reasoning:** Sufficient for initial success criteria (e.g., `expected_output_pattern`). Allows for flexible custom logic.
*   **Guideline:** The test execution framework should support adding multiple evaluators per test case. Implement basic evaluators like `RegexMatcher`, `KeywordPresentEvaluator`, `StringContainmentEvaluator`. Future enhancements could include more sophisticated semantic similarity or rule-based evaluators.

### 8. Dependency Management
*   **Choice:** `Poetry` or `pip-tools` (with `requirements.txt`).
*   **Reasoning:**
    *   `Poetry`: Provides a complete dependency management solution, including virtual environments, dependency locking, and package publishing.
    *   `pip-tools`: Generates pinned `requirements.txt` from abstract `requirements.in`.
*   **Guideline:** Use `Poetry` for managing project dependencies and virtual environments. This ensures reproducible builds and a clean development setup.

### 9. Testing the Testing Framework
*   **Choice:** `Pytest`
*   **Reasoning:** Industry-standard for Python testing, highly extensible, and easy to use for unit and integration tests.
*   **Guideline:** Write comprehensive unit tests for core components (e.g., prompt templater, database interaction, evaluators). Write integration tests to ensure the full test execution flow works correctly.

### 10. API Key Management
*   **Choice:** Environment variables for LLM provider API keys.
*   **Reasoning:** Secure and standard way to handle sensitive credentials in development and production.
*   **Guideline:** Developers should set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc., in their environment. The application should load these keys securely. Avoid hardcoding keys. For production/CI, leverage orchestrator secrets management (e.g., GitHub Actions Secrets, Kubernetes Secrets).

### 11. Coding Standards & Linting
*   **Choice:** `Black` for auto-formatting, `Flake8` for linting, `isort` for import sorting.
*   **Reasoning:** Ensures consistent code style, catches common errors, and improves code readability and maintainability.
*   **Guideline:** Integrate these tools into the development workflow (e.g., pre-commit hooks, CI/CD checks).

### 12. Version Control
*   **Choice:** Git.
*   **Reasoning:** Industry standard for source code management.
*   **Guideline:** Use Git for all code, test definitions, and documentation. Follow a branching strategy (e.g., Gitflow, GitHub Flow).

### High-Level Architecture Diagram (Conceptual)

```mermaid
graph TD
    A[Developer / CI/CD] --> B(CLI / Python API)
    B --> C{LLM Test Runner}

    C --> D[Test Case Loader]
    D -- Reads --> E[Test Case Definitions (.json)]

    C --> F[Prompt Renderer]
    F -- Uses --> E

    C --> G[LLM Provider Interface]
    G -- Calls --> H[OpenAI API]
    G -- Calls --> I[Anthropic API]
    G -- Calls --> J[Other LLM APIs]

    G -- Returns --> K[LLM Raw Response]

    C --> L[Result Evaluator]
    L -- Uses --> E
    L -- Evaluates --> K

    K -- & --> L -- Stores --> M[LLM Test Results DB]
    M((PostgreSQL / SQLite))

    B -- Views --> M
```
