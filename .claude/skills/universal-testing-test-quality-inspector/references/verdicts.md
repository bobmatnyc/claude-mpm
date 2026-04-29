# Verdicts and Report Templates

## Verdict Criteria

### CORRECT

**Issue:** All five checks pass.

**Criteria:**
- Test name accurately describes the behavior verified
- Assertions check specific, meaningful values
- At least one mutation would cause the test to fail
- Edge cases named in the test are present in the arrange phase
- Mocks are limited to external I/O and do not hollow out logic

**Report format:**
```
Verdict: CORRECT

Test: test_should_return_discounted_price_when_coupon_is_valid

Evidence:
- Name matches assertions: checks that price == original * 0.9 when coupon code 'SAVE10' applied
- Assertion is specific: assertEqual(90.0, result) not just assertLess(result, 100)
- Mutation check: changing multiplier from 0.9 to 0.8 in implementation would fail this test
- Edge case coverage: coupon 'SAVE10' is explicitly set up in arrange
- Mock hygiene: only database read is mocked; discount calculation runs real code
```

---

### MISLEADING

**Issue:** Check 1 (Name-to-Assertion Alignment) fails. The test passes but the name or description does not match what is actually tested.

**Criteria (any one sufficient):**
- Test name describes behavior X but assertions only verify Y
- Test name references a condition that is not set up in the arrange phase
- Test name implies a negative case but the test only checks the positive path
- Test docstring contradicts what the assertions verify

**Report format:**
```
Verdict: MISLEADING

Test: test_should_reject_expired_tokens

Issue: The test name claims to verify that expired tokens are rejected, but the
token created in the arrange phase never has an expiry date set. The assertion
checks that `result.user_id == 1`, which would pass for any valid token.

Evidence:
  Line 12: token = Token(user_id=1, value="abc123")
    → No expiry field set; this is a valid, non-expired token

  Line 18: assert result.user_id == 1
    → This assertion passes for valid tokens; it does not test rejection

Suggested fix:
  token = Token(user_id=1, value="abc123", expires_at=datetime.now() - timedelta(hours=1))
  with pytest.raises(TokenExpiredError):
      validate_token(token)
```

---

### INCOMPLETE

**Issue:** Checks 1, 4, or a combination are partially satisfied. The test covers some behavior but misses important assertions or edge cases.

**Criteria (any one sufficient):**
- Test verifies the happy path but does not assert error conditions named in the test
- Test checks return value but not documented side effects
- Edge cases in the test name are missing from the arrange phase
- Assertions cover some fields but leave critical fields unchecked

**Report format:**
```
Verdict: INCOMPLETE

Test: test_should_send_welcome_email_when_user_registers

Issue: The test verifies that user registration returns a success response but does
not verify that a welcome email was sent. The test name explicitly promises email
verification.

Evidence:
  Assertions present:
    assert result.status == 'created'
    assert result.user.id is not None

  Missing assertion:
    No check that email service was called with the new user's address

Suggested fix:
  mock_email_service.send_welcome.assert_called_once_with(
      to="alice@example.com",
      name="Alice"
  )
```

---

### BROKEN

**Issue:** Check 3 (Mutation Failure) fails. An obvious bug in the implementation would not be caught by this test.

**Criteria (any one sufficient):**
- Test asserts only type or existence, not value
- All assertions match mock return values exactly (no real logic verified)
- The function under test is itself mocked
- Test passes with a stub implementation that returns a hardcoded value
- Assertion is tautological (always true)

**Report format:**
```
Verdict: BROKEN

Test: test_calculate_order_total

Issue: The test would pass even if calculate_order_total() returned 0 or any positive
number. The assertion only checks that the result is a float, not that it equals the
correct total.

Evidence:
  Line 24: assert isinstance(result, float)
    → Passes for result = 0.0, result = 999.99, result = correct_value

  Mutation that would NOT be caught:
    Changing `return sum(item.price for item in items)` to `return 0.0`
    → Test still passes

Suggested fix:
  items = [Item(price=10.00), Item(price=5.50)]
  result = calculate_order_total(items)
  assert result == 15.50  # Specific expected value
```

---

## Reporting Multiple Tests

When inspecting a test suite or file, produce a summary table followed by individual reports for non-CORRECT tests only.

### Summary table format

```
Test Quality Inspection Report
File: tests/test_billing.py
Inspected: 8 tests

| Test Name                                    | Verdict    | Primary Issue         |
|----------------------------------------------|------------|-----------------------|
| test_charge_card_success                     | CORRECT    |                       |
| test_charge_card_declined                    | CORRECT    |                       |
| test_refund_full_amount                      | INCOMPLETE | Missing DB side effect|
| test_refund_partial_amount                   | MISLEADING | Name/assertion mismatch|
| test_calculate_tax_standard_rate             | BROKEN     | Always-true assertion |
| test_calculate_tax_exempt_items              | CORRECT    |                       |
| test_invoice_generation                      | INCOMPLETE | Missing format check  |
| test_invoice_attachment_email                | BROKEN     | Function under test mocked|

Summary: 3 CORRECT, 2 INCOMPLETE, 1 MISLEADING, 2 BROKEN
Confidence in test suite: LOW — 5 of 8 tests would not catch bugs they claim to cover
```

Then individual reports for the 5 non-CORRECT tests.

---

## Confidence Rating

After inspecting a suite, provide a confidence rating:

**HIGH**: 90%+ of tests are CORRECT. Mutations in the implementation would reliably be caught.

**MEDIUM**: 70-89% CORRECT. Most bugs would be caught. Some edge cases could slip through.

**LOW**: 50-69% CORRECT. Significant gaps. A developer could introduce bugs without tests failing.

**CRITICAL**: <50% CORRECT. Test suite provides false confidence. Do not rely on it for refactoring or regression detection.
