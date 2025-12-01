# Ticket Completeness Protocol Examples

## ✅ COMPLETE TICKET (Passes Zero PM Context Test)

```
Ticket: PROJ-123 "Implement OAuth2 authentication"

Description:
Add OAuth2 authentication flow to user login system.

ACCEPTANCE CRITERIA:
- Users can log in via OAuth2 with Google and GitHub providers
- Existing username/password login continues to work
- OAuth2 tokens stored securely in database
- Token refresh implemented for expired tokens
- All existing tests pass + new OAuth2 tests added
- Performance: OAuth2 login completes in < 2 seconds

TECHNICAL CONTEXT (Comment):
Code Patterns:
- Follow existing auth patterns in src/auth/strategies/
- Use passport-oauth2 library (already in dependencies)
- Token storage follows pattern in src/models/auth_token.py

Files to Modify:
- src/auth/strategies/oauth2.py (create new)
- src/auth/router.py (add OAuth2 routes)
- src/models/user.py (add oauth_provider field)
- tests/test_auth_oauth2.py (create new)

Dependencies:
- passport-oauth2>=1.7.0 (already installed)
- No new dependencies required

RESEARCH FINDINGS (Comment):
OAuth2 Flow Analysis:
1. Authorization Code Flow recommended (most secure)
2. Google OAuth2: Requires client_id/secret (get from admin)
3. GitHub OAuth2: Requires app registration (get from admin)
4. Token refresh: Implement background job (runs every 24h)

Security Considerations:
- Store tokens encrypted at rest (use existing encryption service)
- Implement PKCE for mobile clients (future enhancement)
- Rate limit OAuth2 endpoints (5 attempts per minute)

Reference: https://oauth.net/2/ (see "Authorization Code Flow" section)

SUCCESS CRITERIA (Comment):
Verification Steps:
1. User clicks "Login with Google" → redirected to Google consent
2. User approves → redirected back with code → token exchange succeeds
3. User profile populated from Google API
4. Token stored in database (encrypted)
5. User can access protected resources
6. Token refresh runs automatically

Performance:
- OAuth2 login: < 2 seconds (measured with pytest-benchmark)
- Token refresh: < 500ms per token

DISCOVERED WORK SUMMARY (Comment):
In-Scope (Created Subtasks):
- PROJ-124: Add OAuth2 provider configuration UI
- PROJ-125: Implement token refresh background job

Out-of-Scope (Separate Tickets):
- PROJ-126: Add OAuth2 support for Facebook (separate feature request)
- PROJ-127: Migrate existing users to OAuth2 (data migration project)

Deferred (Documented but not ticketed):
- PKCE for mobile clients (not needed for web app yet)
- Multi-factor auth (separate initiative)

Scope Decision: We focused ONLY on Google/GitHub OAuth2 for web app.
Mobile and Facebook support deferred to separate initiatives per user confirmation.
```

**Engineer Assessment**: ✅ COMPLETE
- Can understand what to build? YES (acceptance criteria clear)
- Has research findings? YES (OAuth2 flow, security considerations)
- Has technical context? YES (code patterns, files to modify, dependencies)
- Knows success criteria? YES (verification steps, performance targets)
- Knows about discovered work? YES (subtasks created, scope documented)

## ❌ INCOMPLETE TICKET (Fails Zero PM Context Test)

```
Ticket: PROJ-123 "Implement OAuth2 authentication"

Description:
Add OAuth2 authentication flow to user login system.

(No comments, no attachments)
```

**Engineer Assessment**: ❌ INCOMPLETE
- Can understand what to build? PARTIALLY (vague description)
- Has research findings? NO (which providers? what flow?)
- Has technical context? NO (which files? which libraries?)
- Knows success criteria? NO (how to verify? performance targets?)
- Knows about discovered work? NO (are there dependencies? follow-ups?)

**Engineer Questions for PM**:
1. Which OAuth2 providers should I support?
2. Which OAuth2 flow should I use?
3. How do I store tokens? What encryption?
4. Which files do I need to modify?
5. What libraries should I use?
6. How do I test this?
7. Are there any follow-up tickets I should know about?

**PM Violation**: Ticket lacks ALL context. Engineer cannot proceed independently.

## Attachment Decision Tree Examples

### 📊 RESEARCH FINDINGS:
- Summary (< 500 words) → Attach as ticket comment
- Detailed analysis (> 500 words) → Save to docs/research/, link from ticket
- Architecture diagrams → Attach as comment (markdown or image link)
- Third-party docs → Reference URL in ticket comment with key excerpts

### 💻 CODE ANALYSIS:
- Code patterns → Attach key examples as comment (code blocks)
- File locations → List in comment ("Files to modify: src/foo.py, tests/test_foo.py")
- Dependencies → List in comment with versions ("Requires: requests>=2.28.0")
- Integration points → Describe in comment with code examples

### 🧪 QA/TEST RESULTS:
- Test output → Attach as comment (use code blocks)
- Bug reports → Create separate tickets, reference from original
- Performance benchmarks → Attach as comment with numbers
- Edge cases → List in comment with reproduction steps

### ⚠️ DO NOT ATTACH (Reference Only):
- CLAUDE.md patterns → Reference only ("Follow auth patterns in CLAUDE.md")
- Project-wide conventions → Reference only ("See CONTRIBUTING.md")
- Existing documentation → Link, don't duplicate
- Common knowledge → Don't attach obvious information
