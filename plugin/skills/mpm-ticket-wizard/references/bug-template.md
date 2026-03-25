# Bug Report Template

Complete Q&A flow and output format for bug reports.

## Q&A Sequence

### Q1: Brief Description
```
Describe the bug in one sentence:
> [User provides: "Login button doesn't work on mobile"]
```

**Smart Prompt if vague:**
```
"Login doesn't work" is a good start. Can you tell me:
- What error do you see (if any)?
- Does it fail silently or show a message?
- When did this start happening?
```

### Q2: Expected vs Actual Behavior
```
What did you expect to happen?
> [User provides expected behavior]

What actually happened?
> [User provides actual behavior]
```

**Smart Prompt if unclear:**
```
Can you be more specific about the difference?
- What was the exact error message?
- Did you see any visual change?
- Did anything happen at all?
```

### Q3: Reproduction Steps
```
How can we reproduce this bug? Please list numbered steps:
1. [Step 1]
2. [Step 2]
3. [Step 3]
```

**Smart Prompt if incomplete:**
```
Help me reproduce this exactly:
- What was the starting state? (logged in? specific page?)
- What specific actions did you take?
- What data or inputs were involved?
- Did you try it more than once?
```

### Q4: Environment Details
```
Where does this occur? Please provide:
- Browser and version (e.g., Chrome 120):
- Device type: desktop / mobile / tablet
- Operating system (e.g., macOS 14.2, Windows 11):
- Any other context (VPN, incognito mode, etc.):
```

**Smart Prompt if missing:**
```
Environment matters for debugging:
- Which browser are you using?
- Desktop or mobile?
- What operating system?
- Any special conditions (VPN, ad blocker, incognito)?
```

### Q5: Severity Assessment
```
How severe is this bug?

- Critical: System down, data loss, security issue, affects all users
- High: Major feature broken, no workaround, affects many users
- Medium: Feature broken but workaround exists, affects some users
- Low: Minor issue, cosmetic, edge case, affects few users
```

**Severity Guidelines:**
| Scenario | Severity |
|----------|----------|
| Production down | Critical |
| Data corruption/loss | Critical |
| Security vulnerability | Critical |
| Payment processing broken | Critical |
| Login completely broken | High |
| Core feature unusable | High |
| Feature broken, workaround exists | Medium |
| UI glitch, no functional impact | Low |
| Edge case, rare occurrence | Low |

### Q6: Additional Context (Optional)
```
Any additional information?
- Screenshots or screen recordings?
- Error messages from console?
- Related tickets?
- When did this start happening?
```

## Output Template

```markdown
## Bug: [Brief Description]

### Summary
[One-line summary of the issue]

### Expected Behavior
[What should happen when the user performs the action]

### Actual Behavior
[What actually happens - include error messages if applicable]

### Reproduction Steps
1. [Specific step 1 - include starting state]
2. [Specific step 2]
3. [Specific step 3]
4. [Continue as needed]

### Environment
- Browser: [browser name and version]
- Device: [desktop/mobile/tablet]
- OS: [operating system and version]
- Other: [VPN, incognito, extensions, etc.]

### Severity
[Critical/High/Medium/Low] - [Brief justification]

### Additional Context
[Screenshots, logs, related tickets, when it started, etc.]

### Suggested Labels
[Auto-suggested based on content]
```

## Complete Example

### Input Q&A

```
PM: "Describe the bug in one sentence:"
User: "The checkout button is unclickable on Safari"

PM: "What did you expect to happen?"
User: "Clicking the button should submit my order"

PM: "What actually happened?"
User: "Nothing - the button doesn't respond to clicks at all"

PM: "How can we reproduce this?"
User: "1. Add item to cart 2. Go to checkout 3. Try to click 'Complete Order'"

PM: "Environment details?"
User: "Safari 17.2 on macOS Sonoma, desktop"

PM: "How severe is this?"
User: "High - customers can't complete orders in Safari"
```

### Output Ticket

```markdown
## Bug: Checkout button unclickable on Safari

### Summary
The 'Complete Order' button on the checkout page does not respond to clicks in Safari browser.

### Expected Behavior
Clicking the checkout button should submit the order and proceed to payment confirmation.

### Actual Behavior
The button does not respond to clicks at all. No error message, no visual feedback, no console errors.

### Reproduction Steps
1. Add any item to the shopping cart
2. Navigate to the checkout page
3. Fill in required shipping/payment information
4. Attempt to click the 'Complete Order' button
5. Observe that nothing happens

### Environment
- Browser: Safari 17.2
- Device: Desktop
- OS: macOS Sonoma 14.2
- Other: Tested without extensions

### Severity
High - Prevents customers from completing orders, directly impacts revenue. No workaround for Safari users.

### Additional Context
- Works correctly in Chrome and Firefox
- May be related to Safari's stricter event handling
- Customer reports started after last Friday's deployment

### Suggested Labels
`bug`, `frontend`, `safari`, `checkout`, `priority:high`
```

## Label Suggestions for Bugs

| Content Pattern | Suggested Labels |
|-----------------|------------------|
| Safari, Firefox, Chrome, browser | `browser-compat` |
| Mobile, iOS, Android | `mobile` |
| Authentication, login, logout | `auth` |
| Payment, checkout, order | `checkout`, `payments` |
| API error, 500, 404 | `backend`, `api` |
| UI broken, not displaying | `frontend`, `ui` |
| Slow, timeout, performance | `performance` |
| Data missing, wrong data | `data-integrity` |
| Security, XSS, injection | `security`, `priority:critical` |
