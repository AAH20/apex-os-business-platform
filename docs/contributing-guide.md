# Contributing Guide

Thank you for your interest in contributing to APEX-OS Business Platform. This document outlines the standards and processes we follow to maintain code quality and collaboration efficiency.

---

## 1. Code Style Guide

### General Principles

- **Readability first**: Code is read more often than it is written. Prioritize clarity over cleverness.
- **Consistency**: Follow the existing patterns in the codebase. When in doubt, match the surrounding code.
- **Small, focused changes**: Each change should do one thing. Avoid mixing refactoring with feature work.

### Language-Specific Guidelines

#### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/) with a line length of 100 characters.
- Use type hints for all function signatures and public APIs.
- Prefer `pathlib.Path` over `os.path` for filesystem operations.
- Use f-strings for string formatting (Python 3.8+).
- Imports: standard library, third-party, first-party — each group separated by a blank line, sorted alphabetically within groups.

```python
# Good
def process_order(order_id: str, *, dry_run: bool = False) -> OrderResult:
    ...

# Avoid
def processOrder(orderId, dryRun=False):
    ...
```

#### TypeScript / JavaScript

- Follow the ESLint configuration in the repository root.
- Use `const` by default; `let` when reassignment is needed. Never use `var`.
- Prefer `async/await` over raw Promises and callback chains.
- Use explicit return types on exported functions.
- Prefer named exports over default exports (except for single-component files).

#### CSS / Styling

- Use CSS custom properties (variables) for colors, spacing, and typography tokens.
- Follow BEM naming convention for class names: `block__element--modifier`.
- Avoid inline styles unless dynamically computed.

### Formatting & Linting

- Run the project's formatter and linter before committing:
  ```bash
  make lint
  make format
  ```
- All code must pass linting with zero warnings (not just zero errors).

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files (Python) | `snake_case.py` | `order_service.py` |
| Files (TS/JS) | `kebab-case.ts` | `order-service.ts` |
| Classes | `PascalCase` | `OrderProcessor` |
| Functions / Methods | `snake_case` (Python), `camelCase` (TS) | `get_order()`, `getOrder()` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Private members | Leading underscore | `_internal_cache` |
| Boolean variables | `is_`, `has_`, `should_` prefix | `is_active`, `has_permission` |

### Error Handling

- Never swallow exceptions silently. At minimum, log with context.
- Use custom exception types for domain errors; built-in exceptions for programming errors.
- Include relevant context in error messages (IDs, parameters, state).

---

## 2. Commit Message Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/) to enable automated changelog generation and semantic versioning.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation-only changes |
| `style` | Code style changes (formatting, semicolons, etc.) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `chore` | Build process, dependencies, tooling changes |
| `ci` | CI/CD configuration changes |
| `revert` | Revert a previous commit |

### Rules

- **Subject line**: 72 characters or fewer, imperative mood, no trailing period.
- **Body**: Wrap at 72 characters. Explain *what* and *why*, not *how*.
- **Scope**: Optional. Use the module or component name (e.g., `auth`, `orders`, `ui`).
- **Breaking changes**: Add `BREAKING CHANGE:` in the footer with migration notes.

### Examples

```
feat(auth): add OAuth2 support for Google Workspace

Implement the authorization code flow with PKCE for Google Workspace
integration. Users can now sign in with their Google accounts.

Closes #123
```

```
fix(orders): prevent duplicate order creation on retry

Add idempotency key validation to the order creation endpoint.
Previously, a network retry could result in duplicate orders.

BREAKING CHANGE: The `POST /api/v1/orders` endpoint now requires
an `Idempotency-Key` header. Requests without it will receive
a 400 response.
```

### Atomic Commits

- Each commit should leave the project in a working state (tests pass).
- Do not bundle unrelated changes into a single commit.
- Use `git add -p` to stage specific hunks when needed.

---

## 3. Pull Request Process

### Before You Start

1. **Fork and branch**: Create a feature branch from `main` (or the appropriate base branch).
2. **Naming**: Use descriptive branch names: `feat/oauth-login`, `fix/order-duplication`, `docs/api-reference`.
3. **Check existing PRs**: Avoid duplicating work. Comment on an existing PR if you want to contribute to it.

### Creating the PR

1. **Push your branch** to your fork.
2. **Open a pull request** against the base branch using the PR template.
3. **Fill out the PR template** completely:
   - **Summary**: What does this change do and why?
   - **Testing**: How was this tested? Include commands run and results.
   - **Screenshots**: For UI changes, include before/after screenshots.
   - **Checklist**: Complete the self-review checklist.

### PR Size

- **Keep PRs small**: Aim for under 400 lines of diff. Large PRs should be split into stacked PRs.
- If a PR exceeds 800 lines, consider breaking it into a series of smaller, independently mergeable PRs.

### PR Lifecycle

1. **Draft PR**: Open as draft while work is in progress. Mark "Ready for Review" when complete.
2. **CI must pass**: All automated checks (lint, type-check, tests, build) must pass before review.
3. **Address feedback**: Push additional commits to your branch; do not force-push after review starts.
4. **Merge**: PRs are squash-merged by the maintainer. Ensure your commit history is clean.

### After Merge

- Delete your feature branch.
- Update any related issues or project boards.

---

## 4. Review Process

### For Authors

- **Self-review first**: Read your own diff before requesting review. Catch obvious issues early.
- **Respond promptly**: Aim to address review comments within 48 hours.
- **Be open to feedback**: Reviews are about the code, not the person. Ask questions if feedback is unclear.
- **Resolve conversations**: Only resolve a conversation when you've addressed the concern. Do not resolve your own reviews.

### For Reviewers

- **Be respectful and constructive**: Critique the code, not the author. Suggest alternatives rather than just pointing out problems.
- **Prioritize**: Focus on correctness, security, and maintainability. Nitpicks should be clearly marked as optional.
- **Approve when ready**: Do not withhold approval for stylistic preferences that are not enforced by the linter.
- **Use the standard labels**:
  - `LGTM` — Looks good to me, approved.
  - `Request changes` — Issues must be addressed before merging.
  - `Comment` — Feedback without blocking approval.

### Review Turnaround

- **Initial review**: Within 2 business days.
- **Re-review after changes**: Within 1 business day.
- **Stale PRs**: PRs with no activity for 14 days will be marked stale and may be closed after 30 days.

### What Reviewers Check

- [ ] Code correctness and edge cases
- [ ] Security implications (input validation, auth, data exposure)
- [ ] Performance implications (N+1 queries, unnecessary re-renders)
- [ ] Test coverage for new logic
- [ ] Documentation updates (API docs, README, inline comments)
- [ ] Backward compatibility and migration paths

---

## 5. Testing Requirements

### Minimum Coverage

- **New code**: All new functions, classes, and modules must have corresponding tests.
- **Bug fixes**: Every bug fix must include a regression test that would have caught the bug.
- **Coverage threshold**: The project maintains a minimum line coverage of 80%. PRs that decrease coverage will not be merged.

### Test Types

| Type | Scope | Speed | Required For |
|------|-------|-------|-------------|
| Unit tests | Individual functions/classes | Fast | All new logic |
| Integration tests | API endpoints, DB interactions | Medium | API changes, data layer changes |
| E2E tests | Full user workflows | Slow | Critical user flows (checkout, auth) |

### Writing Tests

- **Python**: Use `pytest`. Name test files `test_*.py` and test functions `test_*`.
- **TypeScript**: Use `vitest` or `jest`. Name test files `*.test.ts` or `*.spec.ts`.
- **Structure tests** using the Arrange-Act-Assert pattern.
- **One assertion per test** (or one logical concept). Avoid testing multiple unrelated things in a single test.
- **Use factories/fixtures** for test data, not inline object literals.
- **Mock external services** (APIs, email, payment processors). Never make real external calls in tests.

### Running Tests

```bash
# Run all tests
make test

# Run tests for a specific module
pytest tests/orders/
vitest run src/services/orders/

# Run with coverage
make test-coverage
```

### Before Submitting a PR

- [ ] All tests pass locally (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make typecheck`)
- [ ] New tests cover the added/modified code
- [ ] No test is skipped or marked `xfail` without a linked issue

---

## 6. Documentation Requirements

### When to Update Documentation

- **API changes**: Update OpenAPI/Swagger specs and any API reference docs.
- **New features**: Add a section to the relevant user guide or README.
- **Configuration changes**: Update `.env.example`, config reference, and deployment docs.
- **Breaking changes**: Add a migration guide entry and update the changelog.
- **Bug fixes**: Update docs if the fix changes documented behavior.

### Documentation Standards

- **Markdown**: All documentation is written in Markdown and rendered via MkDocs.
- **Code examples**: Every code example must be tested or verified to work.
- **Screenshots**: Update screenshots for UI changes. Use consistent browser size and theme.
- **Keep it current**: Outdated documentation is worse than no documentation. If you change behavior, change the docs in the same PR.

### Docstrings and Inline Comments

- **Python**: Use Google-style docstrings for all public modules, classes, and functions.
- **TypeScript**: Use TSDoc for exported types, interfaces, and functions.
- **Inline comments**: Explain *why*, not *what*. The code should be self-documenting for the "what".
- **TODO comments**: Format as `TODO(username): description` and link to a tracking issue.

### Changelog

- All user-facing changes must be noted in `CHANGELOG.md` under the appropriate version heading.
- Use the format: `- <description> ([#PR](link))`

---

## Getting Help

- **Questions**: Open a [GitHub Discussion](https://github.com/your-org/apex-os-business-platform/discussions) for general questions.
- **Bugs**: Open a [GitHub Issue](https://github.com/your-org/apex-os-business-platform/issues) with the bug report template.
- **Security vulnerabilities**: Do NOT open a public issue. Email `security@your-org.com` with details.

---

By contributing to this project, you agree to abide by this guide and the [Code of Conduct](CODE_OF_CONDUCT.md). Thank you for helping make APEX-OS better!
