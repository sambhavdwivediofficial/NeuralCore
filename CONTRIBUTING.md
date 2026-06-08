<div align="center">
  
# Contributing to NeuralCore
</div>
NeuralCore is a large-scale, production-grade AI infrastructure platform. Contributing to this project is a serious technical undertaking. This document defines the exact process, standards, and expectations for anyone who wishes to contribute.

Read this document in full before opening an issue or submitting a pull request. Contributions that do not follow this process will be closed without review.

---

## Table of Contents

- [Who Should Contribute](#who-should-contribute)
- [Before You Start](#before-you-start)
- [Types of Contributions](#types-of-contributions)
- [Development Environment](#development-environment)
- [Architecture Orientation](#architecture-orientation)
- [Contribution Process](#contribution-process)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Documentation Requirements](#documentation-requirements)
- [Commit Standards](#commit-standards)
- [Pull Request Standards](#pull-request-standards)
- [Review Process](#review-process)
- [Subsystem-Specific Guidelines](#subsystem-specific-guidelines)
- [What Will Not Be Accepted](#what-will-not-be-accepted)
- [License Agreement](#license-agreement)

---

## Who Should Contribute

NeuralCore welcomes contributions from engineers who:

- Have read and understood the architecture documentation in full
- Have working knowledge of the relevant subsystem they intend to modify
- Can write production-quality Python and are comfortable with async Python patterns
- Understand the scale and deployment context this platform is designed for
- Can engage with the review process professionally and substantively

This is not a beginner-friendly project. There is no easy-issues tag. Every part of the system is interconnected and consequential. Contributing requires genuine expertise.

---

## Before You Start

**Read the architecture documentation.** `ARCHITECTURE.md` describes the system design, subsystem boundaries, data flows, and extension points in detail. Contributing without understanding the architecture results in work that cannot be accepted.

**Understand the relevant subsystem.** Find the subsystem you intend to work on in the architecture document. Understand its interfaces, its dependencies, and its position in the overall system before making changes.

**Check the issue tracker first.** Before doing any work, verify that no one else is already working on the same problem and that the change is within the scope of what the project needs. Unsolicited changes to stable subsystems may not be accepted regardless of quality.

**Open a discussion for large changes.** Any contribution that adds a new subsystem, changes a core interface, or significantly alters existing behavior requires a prior discussion. Open an issue describing the problem, the proposed solution, and the design approach before writing code.

---

## Types of Contributions

### Bug Reports

A valid bug report includes:

- The version of NeuralCore being used
- A precise description of the expected behavior
- A precise description of the actual behavior
- A minimal reproduction case — the smallest possible code that demonstrates the bug
- Relevant log output, stack traces, or error messages
- The environment: OS, Python version, Docker version, relevant configuration

Bug reports without a reproduction case will be closed. "It doesn't work" is not a bug report.

### Bug Fixes

Bug fixes are the most straightforward type of contribution. A good bug fix:

- Fixes exactly the reported issue and nothing more
- Includes a regression test that fails before the fix and passes after
- Does not introduce any collateral changes to unrelated code
- Preserves all existing test coverage

### Feature Additions

New features are only accepted when:

- The feature fits within the established architecture and does not require architectural changes
- The feature has been discussed and agreed upon before implementation begins
- The feature extends an existing extension point (new provider, new loader, new tool) rather than modifying core logic
- Full test coverage and documentation are included

### Performance Improvements

Performance improvements require:

- Benchmark data demonstrating the improvement with realistic workloads
- No regression in correctness (demonstrated by passing the full test suite)
- Clear explanation of the approach in the pull request description

### Documentation Improvements

Documentation contributions are welcome for:

- Correcting factual errors in existing documentation
- Adding missing documentation for existing, undocumented behavior
- Improving clarity of technical explanations

Do not add documentation for features that do not yet exist, speculative future behavior, or personal preferences.

---

## Development Environment

**Requirements:**

- Python 3.11 or higher
- Rust toolchain (stable channel, 2021 edition or higher)
- Docker and Docker Compose
- PostgreSQL 16 (or use the Docker Compose configuration)
- Redis 7 (or use the Docker Compose configuration)
- Node.js 20 or higher (for frontend development)

**Environment setup:**

Clone the repository and create a Python virtual environment. Install the development dependencies. Copy the example environment file and configure the required values for your local environment. Start the dependent services using Docker Compose.

Verify the setup is correct by running the full test suite before making any changes.

**Configuration:**

All configuration is managed through environment variables and YAML configuration files in the `configs/` directory. Never hardcode configuration values in application code. Never commit real credentials or secrets.

---

## Architecture Orientation

Before writing a single line of code, understand the following:

**Subsystem boundaries are strict.** Code in the retrieval subsystem must not import from the agent subsystem. Code in the billing subsystem must not import from the memory subsystem. Dependencies must flow in the correct direction as defined by the architecture.

**All database access goes through repositories.** Route handlers and services never use the SQLAlchemy session directly. If the operation you need does not exist on the relevant repository, add it to the repository — do not bypass the repository pattern.

**Tenant context is mandatory.** Every operation that touches tenant-scoped data must receive and apply the tenant context. There is no exception to this rule.

**Async everywhere.** All I/O-bound operations must be async. Synchronous database calls, synchronous HTTP calls, and synchronous file operations are not acceptable in the application layer.

**Provider implementations are isolated.** A provider implementation for a specific LLM, vector store, or embedding model belongs in its dedicated module and communicates with the rest of the system exclusively through its base interface. Provider-specific logic must never leak into the calling layer.

---

## Contribution Process

1. **Open an issue** describing the bug or proposed feature. For bug fixes, link the issue in your pull request. For features, get explicit acknowledgment before beginning work.

2. **Fork the repository** and create a branch from the current `main` branch.

3. **Name your branch** according to the convention: `fix/short-description` for bug fixes, `feature/short-description` for features, `docs/short-description` for documentation, `perf/short-description` for performance improvements.

4. **Make focused changes.** Each pull request should address exactly one issue or one coherent feature. Do not bundle unrelated changes.

5. **Write tests** for all new code and for any existing code paths affected by your change.

6. **Update documentation** for any behavior that is visible to users or operators.

7. **Verify the test suite passes** in full before opening a pull request.

8. **Open a pull request** against the `main` branch with a complete description following the pull request standards below.

---

## Code Standards

### Python

- Python 3.11+ syntax and features are expected
- All code must pass `ruff` linting with the project configuration
- All code must pass `mypy` type checking — type annotations are required on all function signatures
- Line length: 100 characters maximum
- String formatting: f-strings for all string interpolation
- Import organization: standard library, third-party, local — each group separated by a blank line
- Class design: prefer composition over inheritance; use abstract base classes at subsystem boundaries
- Error handling: define domain-specific exceptions; never raise bare `Exception`; never silently swallow exceptions
- Logging: use structured logging with the project logger; never use `print` for diagnostic output
- Secrets: never log sensitive values; never include sensitive values in exception messages

### Async Python

- All functions that perform I/O must be `async def`
- Never call `asyncio.run()` inside an async context
- Never use `time.sleep()` — use `asyncio.sleep()` instead
- Database sessions must be used as async context managers
- HTTP clients must be initialized once and reused — never create a new `httpx.AsyncClient` per request

### Rust

- Follow the Rust API guidelines
- All public functions must be documented with doc comments
- Error handling must use `Result` — no panics in library code
- FFI boundary functions must validate all inputs before use
- Memory-unsafe operations must be contained in isolated, clearly documented `unsafe` blocks with an explicit safety invariant comment

### Frontend (TypeScript / Next.js)

- TypeScript strict mode — no `any` types
- Components must be functional components with typed props
- Server components by default; client components only when interactivity is required
- No inline styles — Tailwind utility classes only
- Accessibility: all interactive elements must have appropriate ARIA labels

---

## Testing Requirements

All contributions must include tests. There are no exceptions.

**Unit tests** must cover all new functions, methods, and classes. Tests must be independent — no test may depend on the state left by another test. Tests must be fast — unit tests must not make network calls or access the database.

**Integration tests** are required for any change that involves interaction between subsystems, database operations, or external service integration. Integration tests use the test database and real service dependencies started by Docker Compose.

**Test naming:** Test functions must be named `test_<what_is_being_tested>_<expected_outcome>` — for example, `test_tenant_isolation_prevents_cross_tenant_query`.

**Coverage:** New code must be covered at 90% or above. Coverage must not decrease from the baseline for any existing module you modify.

**Test location:** Tests live in `backend/tests/`. Test files mirror the structure of the source they test: `backend/retrieval/hybrid_retriever.py` is tested in `backend/tests/test_hybrid_retriever.py`.

---

## Documentation Requirements

Code without documentation is incomplete. The following documentation is required for every contribution:

**Inline documentation:** Every public class, every public method, and every public function must have a docstring. Docstrings describe what the code does, what its parameters mean, what it returns, and what exceptions it may raise. Docstrings do not describe how the code works internally — that belongs in inline comments.

**Architecture documentation:** If your contribution adds a new subsystem, a new extension point, or a new integration, update `ARCHITECTURE.md` to reflect the addition.

**Configuration documentation:** If your contribution introduces new configuration options, document them in the relevant YAML configuration file and in the deployment guide.

**Changelog:** Add an entry to `CHANGELOG.md` describing the change. Follow the existing format.

---

## Commit Standards

This project uses Conventional Commits.

**Format:** `<type>(<scope>): <description>`

**Types:**
- `feat` — a new feature
- `fix` — a bug fix
- `docs` — documentation changes only
- `test` — adding or modifying tests only
- `refactor` — code change that neither fixes a bug nor adds a feature
- `perf` — a performance improvement
- `chore` — maintenance tasks, dependency updates, tooling changes

**Scope:** The subsystem being modified — for example, `retrieval`, `agents`, `billing`, `frontend`, `rust_engine`.

**Description:** Present tense, lowercase, no trailing period. Describe what the commit does, not what you did.

**Examples:**
```
feat(retrieval): add federated search result deduplication
fix(billing): correct metering event aggregation window calculation
docs(architecture): document A2A protocol routing table update behavior
test(agents): add integration tests for checkpoint recovery
perf(rust_engine): use SIMD intrinsics for batch cosine similarity
```

**Breaking changes:** If a commit introduces a breaking change, append `!` after the scope and add a `BREAKING CHANGE:` footer describing the change and migration path.

**Commit size:** Each commit should represent one coherent, logical change. Do not bundle multiple unrelated changes into a single commit. Do not make one hundred tiny commits for a single feature — squash your work into meaningful, coherent units.

---

## Pull Request Standards

Every pull request must include:

**A clear title** following the Conventional Commits format.

**A complete description** covering:
- What problem does this change solve, or what behavior does it add?
- What was the root cause of the bug (for bug fixes)?
- What approach was chosen, and why?
- What alternatives were considered and rejected?
- Are there any known limitations or follow-up issues?

**A testing summary** describing what tests were added, what edge cases were covered, and how the change was verified.

**Links** to the related issue.

**Checklist confirmation:**
- [ ] I have read ARCHITECTURE.md and my change is consistent with the architecture
- [ ] My code passes all linting and type checking
- [ ] I have written tests for all new code
- [ ] The full test suite passes
- [ ] I have updated relevant documentation
- [ ] I have added a CHANGELOG.md entry
- [ ] I have not introduced any new dependencies without discussion

---

## Review Process

Every pull request is reviewed before merging. The review process is thorough and may take time. Large pull requests take longer to review — keep pull requests small and focused to accelerate the process.

**What reviewers look at:**
- Correctness — does the code do what it claims to do?
- Architecture consistency — does the change fit within the established architecture?
- Test quality — are the tests meaningful, and do they cover the important cases?
- Code quality — is the code clear, efficient, and maintainable?
- Security — are there any security implications?
- Performance — are there any performance implications?

**Responding to review feedback:**
Address all reviewer comments. For comments where you disagree, explain your reasoning. Do not simply push changes without acknowledging feedback. If a reviewer asks a question, answer it in the pull request comments — do not assume that a code change makes the reasoning self-evident.

**Merging:**
Pull requests are merged by maintainers only, after all review comments are resolved and all checks pass.

---

## Subsystem-Specific Guidelines

### Ingestion and Loaders

New loaders must extend `BaseLoader` and implement the `load()` method. Every loader must:
- Handle the source-specific authentication and connection lifecycle
- Return documents conforming to the `Document` schema
- Handle and log errors gracefully without crashing the ingestion pipeline
- Include a test that verifies the output schema of the loader

### Embedding Providers

New embedding providers must extend `BaseEmbedding`. The `embed()` method must support batch inputs and return a list of vectors with length equal to the input list length. The `dimension()` method must return the correct dimension for the configured model.

### Vector Store Backends

New vector store backends must extend `BaseVectorStore` and implement all five interface methods. Tenant isolation through collection namespacing is mandatory. The implementation must handle the case where a collection does not yet exist when `search()` is called.

### Model Gateway Providers

New LLM providers must extend `BaseProvider`. Streaming implementations must use async generators. Token usage information must be extracted from the provider response and returned in a standardized format.

### Agent Types

New agent types must extend the base agent interface and register with the `AgentManager`. Agents must not maintain external state outside of the memory system. Agent implementations must be fully serializable for checkpoint support.

### Rust Engine Modules

New Rust modules must be documented with Rust doc comments. Public functions exported via FFI must include input validation and must not panic on invalid input. All `unsafe` blocks must include a safety invariant comment.

---

## What Will Not Be Accepted

The following types of contributions will be closed without review:

- Changes that are not grounded in an accepted issue or prior discussion
- Contributions that violate the architectural principles documented in ARCHITECTURE.md
- Code without tests
- Code without documentation
- Pull requests that mix unrelated changes
- Contributions that introduce new external dependencies without prior discussion
- Changes that decrease test coverage
- Code that does not pass linting and type checking
- Refactoring-only changes to stable, well-covered code without clear justification
- Contributions that violate the Code of Conduct

---

## License Agreement

By submitting a contribution to NeuralCore, you agree that:

1. Your contribution is your original work or you have the right to submit it
2. You grant the project owner (Sambhav Dwivedi) a perpetual, worldwide, non-exclusive, royalty-free license to use, modify, and distribute your contribution as part of the NeuralCore project
3. Your contribution does not introduce any code that is incompatible with the project's proprietary license

NeuralCore is proprietary software. All Rights Reserved. Contributing to the project does not grant you any ownership, usage rights, or license to the project beyond the act of contributing itself.

---

Thank you for taking the time to read this document in full. Thoughtful, well-prepared contributions are what make serious engineering projects sustainable. We look forward to working with contributors who share that standard.

---
<div align="center">
  
*NeuralCore Contributing Guide — Copyright (c) 2026 Sambhav Dwivedi. All Rights Reserved.*
</div>
