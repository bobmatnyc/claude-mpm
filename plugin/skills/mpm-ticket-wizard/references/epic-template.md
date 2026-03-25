# Epic Template

Complete Q&A flow and output format for epics.

## Q&A Sequence

### Q1: Epic Title
```
What is this epic about? (Short, descriptive title)
> [User provides: "User Authentication Overhaul"]
```

**Smart Prompt if vague:**
```
A good epic title should:
- Be descriptive but concise
- Indicate the scope of work
- Be understandable to stakeholders
Example: "Payment System Modernization" vs "Fix payments"
```

### Q2: Vision
```
What is the high-level goal of this epic? What does success look like?
> [User describes the big picture]
```

**Smart Prompt for clarity:**
```
Paint the picture of success:
- What will be different when this is done?
- How will users benefit?
- What business outcome does this achieve?
```

### Q3: Problem Space
```
What problems or opportunities does this address?
> [User lists problems being solved]
```

**Smart Prompt if incomplete:**
```
Help me understand the "why":
- What pain points exist today?
- What opportunities are we missing?
- What risks are we mitigating?
```

### Q4: Success Metrics
```
How will we measure success? Be specific.
- [Metric 1: e.g., "Reduce login failures by 50%"]
- [Metric 2: e.g., "Support 2FA for all users"]
```

**Smart Prompt for measurability:**
```
Good metrics are measurable:
- What numbers will change?
- What can we track before/after?
- What's the target improvement?
```

### Q5: Scope - Included
```
What's included in this epic? List major deliverables:
1. [Deliverable 1]
2. [Deliverable 2]
3. [Deliverable 3]
```

**Smart Prompt for completeness:**
```
Think through the full scope:
- What features/changes are needed?
- What integrations are required?
- What documentation/training is included?
```

### Q6: Scope - Excluded
```
What's explicitly NOT included? (Prevents scope creep)
- [Exclusion 1]
- [Exclusion 2]
```

**Smart Prompt for boundaries:**
```
Clear boundaries prevent scope creep:
- What related work is out of scope?
- What's being deferred to future work?
- What won't change as part of this?
```

### Q7: Stakeholders
```
Who are the key stakeholders?
- Owner: [person responsible for epic success]
- Technical Lead: [person leading implementation]
- Stakeholders: [other interested parties]
```

### Q8: Target Timeline (Optional)
```
When should this be completed?
> [User provides target or "No specific deadline"]
```

**Timeline Guidance:**
| Epic Size | Typical Duration |
|-----------|------------------|
| Small | 1-2 sprints |
| Medium | 3-4 sprints |
| Large | 1-2 quarters |
| X-Large | 2+ quarters |

### Q9: Risks and Dependencies
```
What are the key risks or dependencies?
- Risks: [things that could go wrong]
- Dependencies: [what this depends on]
```

### Q10: Initial Issues (Optional)
```
What are the first issues to create under this epic?
1. [Issue 1]
2. [Issue 2]
3. [Issue 3]
```

## Output Template

```markdown
## Epic: [Epic Title]

### Vision
[High-level goal and what success looks like - 2-3 sentences]

### Problem Statement
[Problems or opportunities being addressed]
- [Problem 1]
- [Problem 2]
- [Problem 3]

### Success Metrics
| Metric | Current | Target |
|--------|---------|--------|
| [Metric 1] | [Baseline] | [Goal] |
| [Metric 2] | [Baseline] | [Goal] |

### Scope

**Included:**
1. [Deliverable 1]
2. [Deliverable 2]
3. [Deliverable 3]
4. [Deliverable 4]

**Excluded (Out of Scope):**
- [Exclusion 1] - [reason/future epic]
- [Exclusion 2] - [reason]

### Stakeholders
- **Owner:** [Name]
- **Technical Lead:** [Name]
- **Stakeholders:** [Names]

### Target Timeline
[Timeline, milestone, or quarter]

### Risks and Dependencies

**Risks:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk 1] | [High/Med/Low] | [Mitigation strategy] |
| [Risk 2] | [High/Med/Low] | [Mitigation strategy] |

**Dependencies:**
- [Dependency 1]
- [Dependency 2]

### Initial Child Issues
[To be created after epic is established]
1. [Issue 1]
2. [Issue 2]
3. [Issue 3]

### Suggested Labels
[Auto-suggested based on content]
```

## Complete Example

### Input Q&A

```
PM: "What is this epic about?"
User: "User Authentication Overhaul"

PM: "What is the high-level goal?"
User: "Modernize our auth system to support SSO, 2FA, and passwordless login. Current system is outdated and lacks security features."

PM: "What problems does this address?"
User: "Current auth is vulnerable, doesn't support modern security, users frequently forget passwords"

PM: "How will we measure success?"
User: "Reduce password reset requests by 60%, achieve SOC2 compliance for auth, support all major SSO providers"

PM: "What's included?"
User: "OAuth2 integration, 2FA support, passwordless magic links, SSO for enterprise, session management improvements"

PM: "What's excluded?"
User: "Mobile biometrics (future epic), user data migration (separate effort)"

PM: "Target timeline?"
User: "Q2 2024, needed for enterprise sales push"
```

### Output Ticket

```markdown
## Epic: User Authentication Overhaul

### Vision
Modernize our authentication system to meet enterprise security standards and improve user experience. Success means supporting SSO, 2FA, and passwordless login while significantly reducing password-related support tickets.

### Problem Statement
- Current authentication system uses outdated security practices
- No support for modern security features (2FA, SSO)
- High volume of password reset requests (~40% of support tickets)
- Blocking enterprise sales due to lack of SSO support
- Compliance gaps for SOC2 certification

### Success Metrics
| Metric | Current | Target |
|--------|---------|--------|
| Password reset requests | 40% of tickets | < 15% of tickets |
| Security compliance | Non-compliant | SOC2 Type II |
| SSO providers supported | 0 | 5+ (Google, Microsoft, Okta, SAML, etc.) |
| 2FA adoption rate | 0% | > 50% of users |
| Authentication-related security incidents | 3/month | 0 |

### Scope

**Included:**
1. OAuth2/OIDC integration for SSO (Google, Microsoft, Okta)
2. SAML 2.0 support for enterprise customers
3. Two-factor authentication (TOTP, SMS, backup codes)
4. Passwordless login via magic links
5. Session management improvements (timeout, device management)
6. Audit logging for authentication events
7. Password policy enforcement (strength requirements)
8. Rate limiting and brute force protection
9. Documentation and user guides
10. Migration tooling for existing users

**Excluded (Out of Scope):**
- Mobile biometric authentication (planned for Q3 epic)
- User data migration from legacy system (separate migration project)
- Custom SSO implementations for specific customers (professional services)
- Social login providers beyond Google/Microsoft (future consideration)

### Stakeholders
- **Owner:** Sarah Chen (Product)
- **Technical Lead:** Alex Rivera (Engineering)
- **Stakeholders:** Mike Johnson (Sales), Lisa Park (Security), Support Team

### Target Timeline
- Start: January 2024
- Target Completion: End of Q2 2024
- Milestone: SSO support for March enterprise demos

### Risks and Dependencies

**Risks:**
| Risk | Impact | Mitigation |
|------|--------|------------|
| SSO integration complexity | High | Engage vendor support early |
| User adoption of 2FA | Medium | Gradual rollout with incentives |
| Session management changes break existing flows | Medium | Extensive testing, feature flags |
| SOC2 auditor timeline | Medium | Begin prep in parallel |

**Dependencies:**
- Infrastructure team capacity for session store upgrade
- Security team availability for threat modeling
- Legal review of SSO vendor agreements
- Design team for auth UI/UX updates

### Initial Child Issues
1. Research and select SSO library/framework
2. Design OAuth2/OIDC implementation architecture
3. Implement Google SSO integration (MVP)
4. Design and implement 2FA enrollment flow
5. Create session management service
6. Implement passwordless magic link flow
7. Add authentication audit logging
8. Create user documentation for new auth features

### Suggested Labels
`epic`, `security`, `authentication`, `q2-2024`, `enterprise`
```

## Epic Sizing Guide

### Small Epic
- 1-2 sprints
- 3-5 child issues
- Single team effort
- Clear, bounded scope

### Medium Epic
- 3-4 sprints
- 6-12 child issues
- May involve 2 teams
- Well-defined milestones

### Large Epic
- 1-2 quarters
- 12-25 child issues
- Multiple teams
- Multiple release phases

### X-Large Epic (Consider Breaking Down)
- 2+ quarters
- 25+ child issues
- Cross-functional initiative
- Consider splitting into smaller epics

## Label Suggestions for Epics

| Content Pattern | Suggested Labels |
|-----------------|------------------|
| Authentication, security | `security`, `auth` |
| Performance, scalability | `performance`, `infrastructure` |
| UI, redesign, UX | `frontend`, `design` |
| API, integration | `backend`, `api` |
| Mobile, iOS, Android | `mobile` |
| Compliance, SOC2, GDPR | `compliance` |
| Enterprise, sales | `enterprise` |
| Q1, Q2, Q3, Q4 | `q[N]-[year]` |
