## Automated Testing Plan for Backend (CI/CD)

### 1. Goals:

*   Ensure backend code quality through automated tests.
*   Early detection of bugs and integration issues.
*   Ensure project constraints (Citation-First, No-Auth v1, File Upload Validation) are met.
*   Automate the testing process to accelerate development and deployment.

### 2. Testing Phases:

*   **Unit Tests:** Test the smallest units of code (functions, classes) independently.
    *   **Logic:** Use `pytest` to write unit tests for document processing functions (parsing, chunking, embedding), Milvus interaction functions, and business logic functions within FastAPI endpoints.
    *   **Scope:** Focus on computation functions, data processing, and independent components.

*   **Integration Tests:** Test the interaction between different backend components.
    *   **Logic:** Use `pytest` with `httpx` (or `requests`) to send requests to FastAPI endpoints and verify responses.
    *   **Scope:**
        *   Test `/api/upload` endpoint: Ensure it only accepts `.pdf`, `.docx`, `.txt` and returns appropriate errors for invalid formats.
        *   Test the flow from upload -> parse -> chunk -> embed -> Milvus: Ensure data is processed correctly and stored in Milvus successfully.
        *   Test the flow retrieve -> RAG -> generate: Ensure AI output has valid `citations` and the content is not too generic and can be traced back to the source data.
        *   Test interaction with Zep (Memory Layer) if applicable.

*   **End-to-End Tests (Optional but Recommended):** Test the entire user flow from frontend to backend.
    *   **Logic:** Use `Playwright` or `Selenium` (if needed).
    *   **Scope:** Test the complete process from user uploading a file on the UI, backend processing, and displaying AI results on the UI with full citations.

### 3. Tools:

*   **Pytest:** Primary testing framework for Python backend.
*   **httpx / requests:** For making HTTP requests in integration tests.
*   **pytest-cov:** For measuring code coverage.
*   **Docker Compose:** For setting up an independent and consistent test environment (FastAPI, Milvus, Zep).

### 4. CI/CD Process:

*   **CI (Continuous Integration):**
    1.  **Trigger:** On every new commit or PR creation/update to `main` or `dev` branch.
    2.  **Steps:**
        *   Clone repository.
        *   Build Docker images for backend, Milvus, Zep (if not already built or changed).
        *   Run `docker-compose up -d` to start necessary services.
        *   Install backend dependencies (using `uv` as specified in `ROOT_CONTEXT.md`).
        *   Run Unit Tests.
        *   Run Integration Tests.
        *   Collect Code Coverage.
        *   Tear down Docker environment `docker-compose down`.
        *   Report test results and code coverage.
        *   If any test fails or code coverage is below the defined threshold, the CI pipeline will fail and prevent PR merge.

*   **CD (Continuous Deployment - After successful CI and Lead Review):**
    1.  **Trigger:** After PR merge into `main` (or `dev`) branch.
    2.  **Steps:**
        *   Rebuild Docker images (if necessary).
        *   Deploy services to Staging/Production environment.
        *   Run Post-deployment tests (smoke tests) to ensure services are functional after deployment.

### 5. Quality Gates (Focus for QA Dev):

*   **Gate 1: File upload validation** — Test cases must ensure the `/api/upload` endpoint only accepts `.pdf`, `.docx`, `.txt`. (Backend & Integration Tests)
*   **Gate 2: Citation check** — Every AI response **must** contain a `citations: [{page, source}]` field, and each citation must be traceable to chunk(s) in Milvus. (Integration Tests)
*   **Gate 3: No hallucination** — Verify that generated AI content can be traced back to chunk(s) in Milvus. This is the most challenging part, potentially requiring manual review or development of heuristics to check adherence to original data. (Integration Tests & Manual Review)
*   **Gate 4: Code style** — Integrate `ruff` (replacing PEP8 linting) into CI for automated code style checks. (CI/Unit Tests & Pre-commit Hooks)

### 6. Next Steps:

1.  Discuss and receive feedback on this plan.
2.  If the plan is approved, switch to ACT MODE to begin implementation:
    *   Create directory structure for tests (e.g., `src/backend/tests/`).
    *   Install `pytest`, `httpx`, `pytest-cov`, `ruff` into the backend dev environment.
    *   Write initial unit tests for core components.
    *   Write integration tests for the `/api/upload` endpoint and citation constraints.
    *   Configure CI pipeline (e.g., GitHub Actions, GitLab CI) to run these tests.