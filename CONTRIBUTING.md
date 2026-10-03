# Contributing to APEX-OS Business Platform

Thank you for your interest in contributing! This document provides guidelines for participating in our community and codebase.

## 1. Code of Conduct

### Our Pledge

We pledge to make participation in this project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes:**
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate in a professional setting

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

---

## 2. Development Setup

### Prerequisites

- **Node.js** >= 18.0.0
- **npm** >= 9.0.0 or **pnpm** >= 8.0.0
- **Git** >= 2.30.0
- **Docker** >= 24.0.0 (for local services)

### Initial Setup

```bash
git clone https://github.com/your-org/apex-os-business-platform.git
cd apex-os-business-platform
npm install
cp .env.example .env.local
docker compose up -d
npm run db:migrate
npm run db:seed
```

### Environment Variables

Create a `.env.local` file with the following required variables:

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/apex_os
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key
API_PORT=3000
```

### IDE Configuration

We recommend VS Code with the following extensions: ESLint, Prettier, TypeScript Hero, Docker.

---

## 3. Coding Standards

### General Principles

- **Readability over cleverness**: Write code that is easy to understand
- **Consistency**: Follow existing patterns in the codebase
- **Small changes**: Keep commits focused on a single concern
- **No dead code**: Remove unused code rather than commenting it out

### TypeScript Guidelines

- Enable strict mode; avoid `any` — use `unknown` when the type is truly unknown
- Prefer `interface` over `type` for object shapes
- Use explicit return types on exported functions
- Avoid optional chaining on non-nullable values

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | kebab-case | `user-service.ts` |
| Classes | PascalCase | `UserService` |
| Functions | camelCase | `getUserById()` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| CSS classes | BEM | `card__title--large` |

### Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`

Example: `feat(auth): add OAuth2 login support`

### Linting and Formatting

```bash
npm run lint          # Run linter
npm run lint:fix      # Run linter with auto-fix
npm run format        # Format code
npm run type-check    # Type-check
```

All code must pass linting, formatting, and type-checking before submission.

---

## 4. Pull Request Process

### Before You Start

1. Check existing issues and PRs to avoid duplicate work
2. For significant changes, open an issue first to discuss the approach
3. Fork the repository and create a feature branch from `main`

### Branch Naming

```
feature/<short-description>
bugfix/<short-description>
hotfix/<short-description>
docs/<short-description>
refactor/<short-description>
```

### PR Requirements

- [ ] Branch is up to date with `main`
- [ ] All CI checks pass
- [ ] Tests included for new functionality
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] PR description is complete

### PR Description Template

```markdown
## Summary
Brief description of changes

## Changes
- Change 1
- Change 2

## Testing
Describe how you tested these changes

## Related Issues
Closes #123
```

### Review Process

1. A maintainer will review your PR within 48 hours
2. Address review comments by pushing additional commits
3. Once approved, a maintainer will merge your PR
4. Squash merging is preferred for clean history

---

## 5. Testing Requirements

### Test Types

| Type | Scope | Command |
|------|-------|---------|
| Unit | Individual functions/classes | `npm run test:unit` |
| Integration | API endpoints, DB operations | `npm run test:integration` |
| E2E | Full user workflows | `npm run test:e2e` |
| All | Complete suite | `npm test` |

### Coverage Requirements

- Minimum 80% line coverage for new code
- Minimum 70% branch coverage for new code
- Critical business logic must have 90%+ coverage

### Writing Tests

```typescript
describe('UserService', () => {
  describe('createUser', () => {
    it('should create a user with valid data', async () => {
      const input = { email: 'test@example.com', name: 'Test' };
      const result = await userService.createUser(input);
      expect(result.id).toBeDefined();
      expect(result.email).toBe(input.email);
    });
  });
});
```

### Running Tests in CI

All tests must pass in CI before a PR can be merged. The CI pipeline runs: lint and type-check, unit tests, integration tests, and build verification.

---

## 6. Documentation Requirements

### When to Update Documentation

- Adding new features or APIs
- Changing existing behavior
- Modifying configuration options
- Updating dependencies with breaking changes

### Documentation Types

| Type | Location | When to Update |
|------|----------|---------------|
| API docs | `docs/api/` | API changes |
| README | `README.md` | Setup or usage changes |
| ADRs | `docs/adr/` | Architectural decisions |
| Changelog | `CHANGELOG.md` | Every user-facing change |
| Inline code | Source files | Complex logic or non-obvious behavior |

### Documentation Standards

- Use clear, concise language
- Include code examples for APIs
- Keep line length under 100 characters
- Update the changelog with every PR that affects users

### Changelog Format

```markdown
## [1.2.0] - 2026-10-03

### Added
- New feature description

### Changed
- Changed behavior description

### Fixed
- Bug fix description
```

---

## 7. Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible functionality
- **PATCH**: Backward-compatible bug fixes

### Release Checklist

- [ ] All tests pass on `main`
- [ ] Version bumped in `package.json`
- [ ] `CHANGELOG.md` updated
- [ ] Release notes drafted
- [ ] Git tag created: `git tag -a v1.2.0 -m "Release v1.2.0"`
- [ ] Tag pushed: `git push origin v1.2.0`
- [ ] CI/CD pipeline completes successfully
- [ ] npm package published
- [ ] GitHub release created

### Release Branch Strategy

1. Create a release branch: `git checkout -b release/1.2.0`
2. Bump version and update changelog
3. Merge to `main` and tag
4. Merge back to `develop` if applicable

### Hotfix Process

For critical production fixes:

1. Create hotfix branch from `main`: `git checkout -b hotfix/critical-fix`
2. Make minimal targeted changes
3. Test thoroughly
4. Merge to `main` and `develop`
5. Tag with patch version increment

Thank you for contributing to APEX-OS Business Platform!
