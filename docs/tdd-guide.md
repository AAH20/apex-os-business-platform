# TDD Guide — APEX-OS Business Platform

## 1. TDD Principles

- **Write the test first.** Define expected behavior before implementation exists.
- **One assertion per test.** Each test verifies a single behavior or scenario.
- **Tests are documentation.** A well-named test suite explains what the system does.
- **Fast feedback.** Tests should run in seconds, not minutes.
- **Deterministic.** Same input → same output. No hidden state, no time dependence.
- **Isolated.** Tests do not depend on each other or on execution order.
- **Refactor with confidence.** A green suite lets you improve design safely.

## 2. RED-GREEN-REFACTOR Cycle

### RED
Write a failing test that describes the desired behavior. Run it and confirm it fails for the right reason (missing feature, not broken test).

### GREEN
Write the minimal production code to make the test pass. Do not over-engineer. Hard-code if necessary; generalize later.

### REFACTOR
Clean up both test and production code while keeping the suite green. Remove duplication, improve names, extract helpers.

Repeat. Each cycle should be minutes, not hours.

## 3. Test Naming Conventions

Use the pattern: `test_<subject>_<condition>_<expected>`

```
test_calculateTotal_withEmptyCart_returnsZero
test_validateEmail_withInvalidFormat_throwsError
test_fetchUser_whenNotFound_returnsNull
```

- Use `test_` prefix (or framework equivalent).
- Describe the scenario, not the implementation.
- Avoid generic names like `test1`, `testMethod`.
- Use underscores to separate subject, condition, and expectation.

## 4. Test Organization Patterns

### By Layer
```
tests/
  unit/           # Pure functions, domain logic
  integration/    # API endpoints, database queries
  e2e/            # Full user flows
```

### By Feature
```
tests/
  orders/
    order.test.ts
    order-utils.test.ts
  users/
    user.test.ts
```

### Structure Within a File
1. **Arrange** — set up inputs and dependencies.
2. **Act** — invoke the code under test.
3. **Assert** — verify the outcome.

```typescript
test('calculateTotal_withEmptyCart_returnsZero', () => {
  // Arrange
  const cart = createEmptyCart();

  // Act
  const total = calculateTotal(cart);

  // Assert
  expect(total).toBe(0);
});
```

## 5. Mocking Strategies

### What to Mock
- External services (HTTP, database, message queues)
- Time-dependent code (Date.now, setTimeout)
- Randomness (UUID generators, crypto)
- File system and I/O

### What NOT to Mock
- Pure functions in the same module
- Value objects and DTOs
- The unit under test itself

### Guidelines
- **Prefer fakes over mocks** when possible (in-memory implementations).
- **Mock at the boundary.** Mock the HTTP client, not every internal function.
- **Verify behavior, not implementation.** Assert that the right calls were made with the right arguments.
- **Keep mocks close to the test.** Avoid shared mock setups that obscure intent.
- **Use dependency injection** to make mocking natural.

```typescript
// Good: inject the dependency
class OrderService {
  constructor(private paymentGateway: PaymentGateway) {}

  async placeOrder(order: Order) {
    return this.paymentGateway.charge(order.total);
  }
}

// Test: mock at the boundary
const mockGateway = { charge: jest.fn().mockResolvedValue({ id: 'pay_123' }) };
const service = new OrderService(mockGateway);
```

## 6. Coverage Targets

| Layer        | Line | Branch | Function |
|--------------|------|--------|----------|
| Unit tests   | 80%  | 70%    | 80%      |
| Integration  | 60%  | 50%    | 60%      |
| E2E          | 40%  | 30%    | 40%      |

- **Aim for 80%+ line coverage on domain/business logic.**
- **100% coverage is not the goal** — meaningful tests are.
- **Track coverage trends**, not absolute numbers. A drop signals risk.
- **Use coverage to find untested paths**, not to pad metrics.
- **Critical paths** (payments, auth, data integrity) should approach 100% branch coverage.

---

## Quick Checklist

- [ ] Test written before implementation
- [ ] Test fails for the right reason
- [ ] Minimal code to pass
- [ ] Refactor while green
- [ ] One assertion per test
- [ ] Deterministic and isolated
- [ ] Mocks at boundaries only
- [ ] Coverage tracked and trending up
