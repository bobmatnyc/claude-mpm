# Agent Schema Security Guide

## Critical Security Notice

**This schema is a SECURITY BOUNDARY.** Any changes to agent_schema.json must be carefully reviewed for security implications.

## Security Controls in agent_schema.json

### 1. Field Validation
- **agent_id**: Pattern `^[a-z][a-z0-9_]*$` prevents path traversal and command injection
- **version fields**: Semantic versioning pattern prevents version injection
- **enums**: All enums are allowlists preventing arbitrary values

### 2. Size Limits
- **instructions**: 8000 char max prevents memory exhaustion
- **name**: 50 char max prevents UI breaking
- **description**: 200 char max prevents storage abuse
- **tags**: max 10 items prevents array bombing

### 3. Resource Limits by Tier
```
intensive:    memory: 4096-8192MB, cpu: 60-100%, timeout: 600-3600s
standard:     memory: 2048-4096MB, cpu: 30-60%,  timeout: 300-1200s  
lightweight:  memory: 512-2048MB,  cpu: 10-30%,  timeout: 30-600s
```

### 4. Tool Security Matrix

| Tool Combination | Risk Level | Security Impact |
|-----------------|------------|-----------------|
| Bash + Write | CRITICAL | Arbitrary code execution |
| docker + kubectl | HIGH | Container escape potential |
| aws + gcloud + azure | HIGH | Multi-cloud attack surface |
| WebFetch + Write | MEDIUM | Data exfiltration risk |
| Read + network_access | MEDIUM | Information disclosure |

### 5. Required Security Reviews

Any PR modifying agent_schema.json MUST include:
1. Security impact assessment
2. Validation that no new fields bypass security controls
3. Test cases for new validation rules
4. Update to this security guide if needed

### 6. Security Checklist for Schema Changes

- [ ] No new fields allow arbitrary string input without validation
- [ ] All new arrays have maxItems limits
- [ ] All new strings have maxLength limits
- [ ] New enum values are reviewed for security impact
- [ ] Resource limits maintain tier boundaries
- [ ] No new fields can bypass additionalProperties: false
- [ ] Pattern validations prevent injection attacks
- [ ] Default values follow principle of least privilege

## Common Security Mistakes to Avoid

1. **Never** add fields that accept arbitrary file paths without validation
2. **Never** increase resource limits without security review
3. **Never** add tools that bypass the enum list
4. **Never** remove pattern validation from ID fields
5. **Never** set additionalProperties to true
6. **Always** default network_access to false
7. **Always** validate new tool combinations for security impact

## Security Testing

Run these tests after any schema change:
```bash
# Validate schema structure
python scripts/validate_agent_schema.py

# Test security boundaries
python tests/test_agent_security_boundaries.py

# Check for injection vulnerabilities
python tests/test_agent_validation_security.py
```

## Incident Response

If a security vulnerability is found in the schema:
1. Immediately add validation in agent_validator.py as a hotfix
2. Update schema to prevent the vulnerability
3. Audit all existing agents for exploitation
4. Document the vulnerability and fix in security log

## Security Contacts

- Security reviews: security-team@company.com
- Vulnerability reports: security@company.com
- Emergency response: security-oncall@company.com