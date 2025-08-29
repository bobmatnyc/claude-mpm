# Security Guide

This guide documents the security architecture, validation patterns, input sanitization, path traversal prevention, and security best practices in Claude MPM.

**Last Updated**: 2025-08-14  
**Architecture Version**: 3.8.2  
**Related Documents**: [ARCHITECTURE.md](ARCHITECTURE.md), [SERVICES.md](developer/SERVICES.md)

## Table of Contents

- [Overview](#overview)
- [Security Architecture](#security-architecture)
- [Input Validation Framework](#input-validation-framework)
- [Path Traversal Prevention](#path-traversal-prevention)
- [Authentication and Authorization](#authentication-and-authorization)
- [Data Protection](#data-protection)
- [Secure Communication](#secure-communication)
- [Security Monitoring](#security-monitoring)
- [Vulnerability Management](#vulnerability-management)
- [Best Practices](#best-practices)

## Overview

Claude MPM implements a comprehensive security framework designed to protect against common security threats while maintaining usability and performance. The security approach is built on defense-in-depth principles with multiple layers of protection.

### Security Principles

1. **Input Validation**: All inputs are validated using JSON Schema and custom validators
2. **Path Sanitization**: File operations include path traversal protection
3. **Resource Limits**: Prevent resource exhaustion attacks
4. **Secure Communication**: TLS encryption for all network communication
5. **Principle of Least Privilege**: Minimal required permissions
6. **Defense in Depth**: Multiple layers of security controls

### Threat Model

Claude MPM addresses the following security threats:

- **Path Traversal Attacks**: Malicious file path manipulation
- **Injection Attacks**: Code injection through agent configurations
- **Resource Exhaustion**: Memory and CPU-based denial of service
- **Data Exposure**: Unauthorized access to sensitive information
- **Configuration Tampering**: Unauthorized modification of agent settings
- **Network Attacks**: Man-in-the-middle and eavesdropping

## Security Architecture

### Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Input Valid │  │ Auth/Authz  │  │ Audit Log   │         │
│  │ -ation      │  │ Controls    │  │ -ging       │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                     Service Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Schema      │  │ Path        │  │ Resource    │         │
│  │ Validation  │  │ Sanitization│  │ Limits      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ TLS/SSL     │  │ File System │  │ Network     │         │
│  │ Encryption  │  │ Permissions │  │ Security    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Security Components

#### 1. Input Validation Service

```python
class SecurityValidator:
    """Comprehensive input validation and sanitization service"""
    
    def __init__(self):
        self.schema_validator = JsonSchemaValidator()
        self.path_validator = PathValidator()
        self.content_validator = ContentValidator()
    
    def validate_agent_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate agent configuration against security requirements"""
        result = ValidationResult()
        
        # Schema validation
        schema_result = self.schema_validator.validate(config)
        result.merge(schema_result)
        
        # Path validation for file references
        if 'file_paths' in config:
            path_result = self.path_validator.validate_paths(config['file_paths'])
            result.merge(path_result)
        
        # Content validation
        content_result = self.content_validator.validate_content(config)
        result.merge(content_result)
        
        return result
```

#### 2. Path Security Service

```python
class PathSecurityService:
    """Secure path operations with traversal protection"""
    
    def __init__(self, allowed_directories: List[Path]):
        self.allowed_directories = [Path(d).resolve() for d in allowed_directories]
    
    def sanitize_path(self, user_path: Union[str, Path]) -> Optional[Path]:
        """Sanitize and validate path against traversal attacks"""
        try:
            # Convert to Path object and resolve
            path = Path(user_path).resolve()
            
            # Check if path is within allowed directories
            for allowed_dir in self.allowed_directories:
                if self._is_path_within_directory(path, allowed_dir):
                    return path
            
            raise SecurityError(f"Path '{path}' is not within allowed directories")
            
        except Exception as e:
            logger.warning(f"Path sanitization failed: {e}")
            return None
    
    def _is_path_within_directory(self, path: Path, directory: Path) -> bool:
        """Check if path is within directory (no traversal)"""
        try:
            path.relative_to(directory)
            return True
        except ValueError:
            return False
```

## Input Validation Framework

### JSON Schema Validation

Claude MPM uses JSON Schema for comprehensive input validation with security-focused constraints.

#### Agent Configuration Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Agent Configuration",
  "type": "object",
  "additionalProperties": false,
  "required": ["agent_id", "version", "metadata", "capabilities", "instructions"],
  "properties": {
    "agent_id": {
      "type": "string",
      "pattern": "^[a-z0-9_-]+$",
      "minLength": 1,
      "maxLength": 50,
      "description": "Alphanumeric agent identifier"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semantic version string"
    },
    "metadata": {
      "type": "object",
      "additionalProperties": false,
      "required": ["name", "description"],
      "properties": {
        "name": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100
        },
        "description": {
          "type": "string",
          "minLength": 1,
          "maxLength": 500
        }
      }
    },
    "instructions": {
      "type": "string",
      "minLength": 10,
      "maxLength": 50000,
      "description": "Agent instructions with size limits"
    }
  }
}
```

#### Validation Implementation

```python
class AgentValidator:
    """Secure agent configuration validator"""
    
    def __init__(self):
        self.schema = self._load_security_schema()
        self.validator = Draft7Validator(self.schema)
    
    def validate_agent(self, agent_config: Dict[str, Any]) -> ValidationResult:
        """Validate agent configuration with security checks"""
        result = ValidationResult()
        
        try:
            # JSON Schema validation
            self.validator.validate(agent_config)
            
            # Additional security validations
            self._validate_agent_id_security(agent_config.get('agent_id', ''), result)
            self._validate_instruction_content(agent_config.get('instructions', ''), result)
            self._validate_resource_limits(agent_config, result)
            
            result.is_valid = len(result.errors) == 0
            
        except ValidationError as e:
            result.errors.append(f"Schema validation failed: {e.message}")
            result.is_valid = False
        except Exception as e:
            result.errors.append(f"Validation error: {str(e)}")
            result.is_valid = False
        
        return result
    
    def _validate_agent_id_security(self, agent_id: str, result: ValidationResult):
        """Validate agent ID for security concerns"""
        # Check for path traversal attempts
        if '..' in agent_id or '/' in agent_id or '\\' in agent_id:
            result.errors.append("Agent ID contains invalid path characters")
        
        # Check for reserved names
        reserved_names = ['system', 'admin', 'root', 'config']
        if agent_id.lower() in reserved_names:
            result.errors.append(f"Agent ID '{agent_id}' is reserved")
    
    def _validate_instruction_content(self, instructions: str, result: ValidationResult):
        """Validate instruction content for security issues"""
        # Check for potential script injection
        dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'data:text/html',
            r'eval\s*\(',
            r'Function\s*\('
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, instructions, re.IGNORECASE):
                result.warnings.append(f"Potentially dangerous pattern detected: {pattern}")
```

### Input Sanitization

```python
class InputSanitizer:
    """Comprehensive input sanitization service"""
    
    def __init__(self):
        self.html_parser = html.parser.HTMLParser()
    
    def sanitize_string(self, input_string: str, max_length: int = 10000) -> str:
        """Sanitize string input with length limits"""
        if not isinstance(input_string, str):
            raise ValueError("Input must be a string")
        
        # Enforce length limits
        if len(input_string) > max_length:
            raise ValueError(f"Input exceeds maximum length of {max_length}")
        
        # Remove null bytes and control characters
        sanitized = input_string.replace('\x00', '').replace('\r', '\n')
        
        # Normalize unicode
        sanitized = unicodedata.normalize('NFKC', sanitized)
        
        # HTML escape if needed
        sanitized = html.escape(sanitized)
        
        return sanitized
    
    def sanitize_file_content(self, content: bytes, max_size: int = 10 * 1024 * 1024) -> bytes:
        """Sanitize file content with size limits"""
        if len(content) > max_size:
            raise ValueError(f"File size exceeds maximum of {max_size} bytes")
        
        # Check for binary markers that might indicate malicious content
        if b'\x00' in content[:1024]:  # Check first 1KB for null bytes
            raise ValueError("Binary content detected in text file")
        
        return content
```

## Path Traversal Prevention

### Secure File Operations

```python
class SecureFileOperations:
    """Secure file operations with path traversal protection"""
    
    def __init__(self, base_directories: List[Path]):
        self.base_directories = [Path(d).resolve() for d in base_directories]
        self.logger = logging.getLogger(__name__)
    
    def secure_read_file(self, file_path: Union[str, Path]) -> Optional[str]:
        """Securely read file with path validation"""
        validated_path = self._validate_path(file_path)
        if not validated_path:
            return None
        
        try:
            with open(validated_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Additional content validation
            if len(content) > 10 * 1024 * 1024:  # 10MB limit
                raise ValueError("File size exceeds security limit")
            
            return content
            
        except Exception as e:
            self.logger.error(f"Secure file read failed: {e}")
            return None
    
    def secure_write_file(self, file_path: Union[str, Path], content: str) -> bool:
        """Securely write file with path validation"""
        validated_path = self._validate_path(file_path)
        if not validated_path:
            return False
        
        # Validate content
        if len(content.encode('utf-8')) > 10 * 1024 * 1024:  # 10MB limit
            self.logger.error("Content size exceeds security limit")
            return False
        
        try:
            # Create directory if it doesn't exist (securely)
            validated_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write with secure permissions
            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Set secure file permissions
            os.chmod(validated_path, 0o644)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Secure file write failed: {e}")
            return False
    
    def _validate_path(self, file_path: Union[str, Path]) -> Optional[Path]:
        """Validate file path against traversal attacks"""
        try:
            # Convert to Path and resolve
            path = Path(file_path).resolve()
            
            # Check if within allowed base directories
            for base_dir in self.base_directories:
                try:
                    path.relative_to(base_dir)
                    return path
                except ValueError:
                    continue
            
            self.logger.warning(f"Path '{path}' not within allowed directories")
            return None
            
        except Exception as e:
            self.logger.error(f"Path validation failed: {e}")
            return None
```

### Directory Security

```python
class DirectorySecurity:
    """Directory access control and validation"""
    
    def __init__(self):
        self.allowed_patterns = [
            r'^\.claude-mpm/.*',
            r'^\.claude/.*',
            r'^src/.*',
            r'^docs/.*',
            r'^tests/.*'
        ]
        self.blocked_patterns = [
            r'.*\.\..*',  # Path traversal
            r'.*/etc/.*', # System directories
            r'.*/var/.*',
            r'.*/usr/.*',
            r'.*\.ssh/.*', # SSH keys
            r'.*\.aws/.*'  # AWS credentials
        ]
    
    def is_directory_allowed(self, directory: Path) -> bool:
        """Check if directory access is allowed"""
        dir_str = str(directory)
        
        # Check blocked patterns first
        for pattern in self.blocked_patterns:
            if re.match(pattern, dir_str):
                return False
        
        # Check allowed patterns
        for pattern in self.allowed_patterns:
            if re.match(pattern, dir_str):
                return True
        
        return False
```

## Authentication and Authorization

### Service Authentication

```python
class ServiceAuthenticator:
    """Authentication service for API access"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.active_tokens = {}
    
    def generate_token(self, service_id: str, permissions: List[str]) -> str:
        """Generate JWT token for service authentication"""
        payload = {
            'service_id': service_id,
            'permissions': permissions,
            'issued_at': datetime.utcnow().timestamp(),
            'expires_at': (datetime.utcnow() + timedelta(hours=24)).timestamp()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        self.active_tokens[token] = payload
        
        return token
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check expiration
            if payload['expires_at'] < datetime.utcnow().timestamp():
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
```

### Permission System

```python
class PermissionManager:
    """Fine-grained permission management"""
    
    def __init__(self):
        self.permissions = {
            'agent:read': 'Read agent configurations',
            'agent:write': 'Modify agent configurations',
            'agent:deploy': 'Deploy agents',
            'config:read': 'Read configuration',
            'config:write': 'Modify configuration',
            'system:admin': 'System administration'
        }
    
    def check_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission"""
        # Admin permission grants all access
        if 'system:admin' in user_permissions:
            return True
        
        # Check specific permission
        return required_permission in user_permissions
    
    def validate_operation(self, operation: str, user_permissions: List[str]) -> bool:
        """Validate if operation is allowed for user"""
        permission_map = {
            'read_agent': 'agent:read',
            'modify_agent': 'agent:write',
            'deploy_agent': 'agent:deploy',
            'read_config': 'config:read',
            'modify_config': 'config:write'
        }
        
        required_permission = permission_map.get(operation)
        if not required_permission:
            return False
        
        return self.check_permission(user_permissions, required_permission)
```

## Data Protection

### Sensitive Data Handling

```python
class SensitiveDataProtection:
    """Protection for sensitive data in configurations"""
    
    def __init__(self):
        self.sensitive_patterns = [
            r'password',
            r'secret',
            r'key',
            r'token',
            r'credential',
            r'api_key'
        ]
    
    def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in configuration"""
        masked_data = data.copy()
        
        for key, value in data.items():
            if self._is_sensitive_key(key):
                if isinstance(value, str) and len(value) > 4:
                    masked_data[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                else:
                    masked_data[key] = '*' * len(str(value))
        
        return masked_data
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if key contains sensitive information"""
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in self.sensitive_patterns)
```

### Encryption Services

```python
class EncryptionService:
    """Encryption service for sensitive data at rest"""
    
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt_data(self, data: str) -> bytes:
        """Encrypt string data"""
        return self.fernet.encrypt(data.encode('utf-8'))
    
    def decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt encrypted data"""
        return self.fernet.decrypt(encrypted_data).decode('utf-8')
    
    def encrypt_file(self, file_path: Path, output_path: Path) -> bool:
        """Encrypt file contents"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            encrypted_data = self.fernet.encrypt(data)
            
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            return True
            
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            return False
```

## Secure Communication

### TLS Configuration

```python
class TLSConfiguration:
    """TLS configuration for secure communication"""
    
    def __init__(self):
        self.min_tls_version = ssl.TLSVersion.TLSv1_2
        self.ciphers = [
            'ECDHE-RSA-AES256-GCM-SHA384',
            'ECDHE-RSA-AES128-GCM-SHA256',
            'ECDHE-RSA-AES256-SHA384',
            'ECDHE-RSA-AES128-SHA256'
        ]
    
    def create_secure_context(self) -> ssl.SSLContext:
        """Create secure SSL context"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.minimum_version = self.min_tls_version
        context.set_ciphers(':'.join(self.ciphers))
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        return context
```

### API Security

```python
class APISecurityMiddleware:
    """Security middleware for API endpoints"""
    
    def __init__(self, rate_limiter: RateLimiter, authenticator: ServiceAuthenticator):
        self.rate_limiter = rate_limiter
        self.authenticator = authenticator
    
    async def process_request(self, request) -> Optional[Dict[str, Any]]:
        """Process request with security checks"""
        # Rate limiting
        if not await self.rate_limiter.check_rate_limit(request.remote_addr):
            raise SecurityError("Rate limit exceeded")
        
        # Authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise SecurityError("Missing or invalid authentication")
        
        token = auth_header[7:]  # Remove 'Bearer '
        payload = self.authenticator.validate_token(token)
        if not payload:
            raise SecurityError("Invalid authentication token")
        
        # Input validation
        if request.content_length > 10 * 1024 * 1024:  # 10MB limit
            raise SecurityError("Request body too large")
        
        return payload
```

## Security Monitoring

### Security Event Logging

```python
class SecurityLogger:
    """Centralized security event logging"""
    
    def __init__(self, log_file: Path):
        self.logger = self._setup_security_logger(log_file)
    
    def log_authentication_attempt(self, service_id: str, success: bool, ip_address: str):
        """Log authentication attempts"""
        self.logger.info({
            'event_type': 'authentication_attempt',
            'service_id': service_id,
            'success': success,
            'ip_address': ip_address,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def log_authorization_failure(self, service_id: str, operation: str, reason: str):
        """Log authorization failures"""
        self.logger.warning({
            'event_type': 'authorization_failure',
            'service_id': service_id,
            'operation': operation,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def log_security_violation(self, violation_type: str, details: Dict[str, Any]):
        """Log security violations"""
        self.logger.error({
            'event_type': 'security_violation',
            'violation_type': violation_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })
```

### Intrusion Detection

```python
class IntrusionDetectionSystem:
    """Basic intrusion detection for common attack patterns"""
    
    def __init__(self):
        self.suspicious_patterns = [
            r'\.\./',  # Path traversal
            r'<script',  # XSS attempts
            r'union.*select',  # SQL injection
            r'eval\s*\(',  # Code injection
            r'/etc/passwd',  # System file access
        ]
        self.alert_threshold = 5
        self.violation_counts = defaultdict(int)
    
    def analyze_request(self, request_data: str, source_ip: str) -> bool:
        """Analyze request for suspicious patterns"""
        violations = 0
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, request_data, re.IGNORECASE):
                violations += 1
                self.violation_counts[source_ip] += 1
        
        if violations > 0 or self.violation_counts[source_ip] > self.alert_threshold:
            self._trigger_security_alert(source_ip, violations)
            return True
        
        return False
    
    def _trigger_security_alert(self, source_ip: str, violations: int):
        """Trigger security alert for suspicious activity"""
        alert_data = {
            'source_ip': source_ip,
            'violations': violations,
            'total_violations': self.violation_counts[source_ip],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Log security event
        logger.error(f"Security alert triggered: {alert_data}")
        
        # Could integrate with external alerting systems
```

## Vulnerability Management

### Security Scanner

```python
class SecurityScanner:
    """Automated security scanning for configurations"""
    
    def __init__(self):
        self.checks = [
            self._check_default_passwords,
            self._check_insecure_permissions,
            self._check_exposed_secrets,
            self._check_outdated_dependencies
        ]
    
    def scan_configuration(self, config: Dict[str, Any]) -> List[SecurityIssue]:
        """Comprehensive security scan of configuration"""
        issues = []
        
        for check in self.checks:
            try:
                check_issues = check(config)
                issues.extend(check_issues)
            except Exception as e:
                logger.error(f"Security check failed: {e}")
        
        return issues
    
    def _check_default_passwords(self, config: Dict[str, Any]) -> List[SecurityIssue]:
        """Check for default or weak passwords"""
        issues = []
        default_passwords = ['password', '123456', 'admin', 'default']
        
        for key, value in config.items():
            if 'password' in key.lower() and value in default_passwords:
                issues.append(SecurityIssue(
                    severity='HIGH',
                    type='weak_password',
                    description=f"Default password detected in {key}",
                    recommendation="Use strong, unique passwords"
                ))
        
        return issues
```

### Dependency Security

```python
class DependencySecurityChecker:
    """Check dependencies for known vulnerabilities"""
    
    def __init__(self):
        self.vulnerability_db = self._load_vulnerability_database()
    
    def check_dependencies(self, requirements_file: Path) -> List[SecurityIssue]:
        """Check dependencies against vulnerability database"""
        issues = []
        
        try:
            with open(requirements_file, 'r') as f:
                requirements = f.readlines()
            
            for req in requirements:
                package, version = self._parse_requirement(req.strip())
                if package in self.vulnerability_db:
                    vulnerable_versions = self.vulnerability_db[package]
                    if version in vulnerable_versions:
                        issues.append(SecurityIssue(
                            severity='HIGH',
                            type='vulnerable_dependency',
                            description=f"Vulnerable dependency: {package} {version}",
                            recommendation=f"Update {package} to latest secure version"
                        ))
        
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
        
        return issues
```

## Git Commit Security (Ops Agent v2.2.2+)

The Ops agent has been enhanced with comprehensive git commit authority and security verification capabilities. This section documents the security protocols and verification procedures implemented for safe code repository operations.

### Git Commit Security Framework

#### Pre-commit Security Scanning

The Ops agent implements a multi-layered security scanning approach before any git commit:

```python
class GitCommitSecurityScanner:
    """Comprehensive security scanner for git commits"""
    
    def __init__(self):
        self.prohibited_patterns = [
            # API Keys and Tokens
            r'sk_[a-zA-Z0-9]{32,}',  # Stripe keys
            r'pk_[a-zA-Z0-9]{32,}',  # Public keys
            r'AKIA[0-9A-Z]{16}',     # AWS Access Keys
            r'[A-Za-z0-9/+=]{40}',   # AWS Secret Keys
            r'ghp_[a-zA-Z0-9]{36}',  # GitHub Personal Access Tokens
            r'gho_[a-zA-Z0-9]{36}',  # GitHub OAuth Tokens
            r'vercel_[a-zA-Z0-9]{24}',  # Vercel tokens
            
            # Database Credentials
            r'postgresql://[^:]+:[^@]+@[^/]+',  # PostgreSQL connection strings
            r'mysql://[^:]+:[^@]+@[^/]+',       # MySQL connection strings
            r'mongodb://[^:]+:[^@]+@[^/]+',     # MongoDB connection strings
            
            # Private Keys
            r'-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----',
            r'-----BEGIN OPENSSH PRIVATE KEY-----',
            
            # Generic Secrets
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]
        self.quality_checker = QualityGateChecker()
    
    def scan_staged_files(self) -> SecurityScanResult:
        """Scan all staged files for security violations"""
        result = SecurityScanResult()
        
        # Get staged files
        staged_files = self._get_staged_files()
        
        for file_path in staged_files:
            file_result = self._scan_file(file_path)
            result.merge(file_result)
        
        return result
    
    def _scan_file(self, file_path: str) -> FileScanResult:
        """Scan individual file for prohibited patterns"""
        result = FileScanResult(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in self.prohibited_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        result.add_violation(
                            line_num=line_num,
                            pattern=pattern,
                            matched_text=line.strip(),
                            severity=ViolationSeverity.HIGH
                        )
        except Exception as e:
            result.add_error(f"Failed to scan file: {e}")
        
        return result
```

#### Quality Gate Integration

All git commits are integrated with the project's quality assurance pipeline:

```python
class QualityGateChecker:
    """Integrates with make quality for comprehensive checks"""
    
    def run_quality_checks(self) -> QualityCheckResult:
        """Run complete quality gate before commit"""
        try:
            # Run make quality command
            result = subprocess.run(
                ['make', 'quality'],
                capture_output=True,
                text=True,
                timeout=300  # 5-minute timeout
            )
            
            return QualityCheckResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            return QualityCheckResult(
                success=False,
                error="Quality check timeout (5 minutes)"
            )
        except Exception as e:
            return QualityCheckResult(
                success=False,
                error=f"Quality check failed: {e}"
            )
```

### Security Verification Protocols

#### Prohibited Pattern Detection

The system maintains a comprehensive list of patterns that are prohibited in committed code:

**API Keys and Service Tokens**:
- Stripe API keys (`sk_`, `pk_` prefixes)
- AWS access keys and secrets (`AKIA` prefix, base64 patterns)
- GitHub tokens (`ghp_`, `gho_` prefixes)
- Vercel tokens (`vercel_` prefix)
- Google Cloud service account keys
- Azure storage connection strings

**Database Credentials**:
- PostgreSQL connection strings with credentials
- MySQL connection strings with credentials
- MongoDB connection strings with credentials
- Redis AUTH passwords
- Database password environment variables with hardcoded values

**Cryptographic Material**:
- Private keys (RSA, DSA, EC, OpenSSH)
- SSL certificates with private keys
- JWT signing secrets
- Encryption keys

**Configuration Secrets**:
- Hardcoded passwords in configuration files
- API endpoints with embedded credentials
- OAuth client secrets
- Webhook signing secrets

#### Security Response Protocol

When security violations are detected, the following protocol is executed:

1. **Immediate Block**: Prevent the commit from proceeding
2. **Detailed Report**: Provide specific violation details:
   ```
   🔒 Security Violation Detected
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📁 File: src/config/database.js
   📍 Line: 15
   🚨 Issue: Database connection string with credentials
   🔍 Pattern: postgresql://user:password@host/db
   
   💡 Recommended Fix:
   Replace with environment variable:
   DATABASE_URL=process.env.DATABASE_URL
   
   🛡️ Security Note:
   Never commit database credentials to version control.
   Use environment variables or secure key management.
   ```

3. **Guidance**: Provide specific remediation steps
4. **Verification**: Re-scan after fixes are applied
5. **Audit Logging**: Record all security events for compliance

#### Environment-Specific Considerations

**Development Environment**:
```bash
# Acceptable in development (using placeholders)
DATABASE_URL=postgresql://user:password@localhost:5432/dev_db
API_KEY=your_api_key_here
```

**Production Environment**:
```bash
# Required in production (environment variables only)
DATABASE_URL=${DATABASE_URL}
API_KEY=${API_KEY}
```

### Integration with Development Workflow

#### Secure Commit Workflow

```mermaid
graph TD
    A[User Requests Commit] --> B[Scan Staged Files]
    B --> C{Security Issues?}
    C -->|Yes| D[Block Commit]
    C -->|No| E[Run Quality Checks]
    D --> F[Report Issues]
    F --> G[Provide Fixes]
    G --> H[User Makes Changes]
    H --> B
    E --> I{Quality Pass?}
    I -->|No| J[Block Commit]
    I -->|Yes| K[Generate Commit Message]
    J --> L[Report Quality Issues]
    L --> H
    K --> M[Execute Git Commit]
    M --> N[Log Audit Trail]
```

#### Audit Trail Requirements

All security-related operations are logged with the following information:

```python
class GitCommitAuditLogger:
    def log_security_scan(self, scan_result: SecurityScanResult):
        """Log security scan results for audit purposes"""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'git_commit_security_scan',
            'files_scanned': scan_result.files_scanned,
            'violations_found': len(scan_result.violations),
            'violations': [
                {
                    'file': v.file_path,
                    'line': v.line_number,
                    'severity': v.severity.name,
                    'pattern_type': v.pattern_type
                } for v in scan_result.violations
            ],
            'quality_check_passed': scan_result.quality_check_passed,
            'commit_authorized': scan_result.violations == 0
        }
        
        self._write_audit_log(audit_entry)
```

### Security Configuration

#### Environment Variables

Configure security scanning behavior:

```bash
# Enable/disable git commit security scanning
CLAUDE_MPM_GIT_SECURITY_ENABLED=true

# Configure scan sensitivity (low, medium, high)
CLAUDE_MPM_SECURITY_SENSITIVITY=high

# Enable/disable quality gate integration
CLAUDE_MPM_QUALITY_GATE_ENABLED=true

# Configure audit logging
CLAUDE_MPM_AUDIT_LOG_ENABLED=true
CLAUDE_MPM_AUDIT_LOG_PATH=/var/log/claude-mpm/security.log
```

#### Custom Pattern Configuration

Teams can customize prohibited patterns:

```yaml
# .claude-mpm/security/patterns.yaml
prohibited_patterns:
  api_keys:
    - pattern: 'company_api_[a-zA-Z0-9]{32}'
      description: 'Company-specific API keys'
      severity: 'high'
  
  database:
    - pattern: 'DB_PASSWORD\s*=\s*["\'][^"\']+["\']'
      description: 'Hardcoded database passwords'
      severity: 'critical'
  
  custom_secrets:
    - pattern: 'SECRET_TOKEN_[A-Z0-9]{16}'
      description: 'Custom secret tokens'
      severity: 'high'
```

### Emergency Response Procedures

#### Security Incident Response

If sensitive data is accidentally committed:

1. **Immediate Actions**:
   ```bash
   # Remove from latest commit
   git reset --soft HEAD~1
   git reset HEAD <file_with_secrets>
   
   # Clean up the file
   # Edit file to remove secrets
   
   # Re-commit safely
   git add <cleaned_file>
   git commit -m "fix: remove sensitive data from configuration"
   ```

2. **History Cleanup** (if already pushed):
   ```bash
   # Use BFG Repo-Cleaner or git filter-branch
   # Coordinate with team before force-pushing
   git filter-branch --index-filter 'git rm --cached --ignore-unmatch <file_with_secrets>'
   ```

3. **Credential Rotation**:
   - Immediately revoke compromised credentials
   - Generate new credentials
   - Update all systems using the old credentials
   - Document the incident for security review

#### Monitoring and Alerting

```python
class SecurityMonitor:
    """Monitor security events and trigger alerts"""
    
    def __init__(self):
        self.alert_thresholds = {
            'violations_per_hour': 5,
            'failed_commits_per_day': 10,
            'quality_failures_per_day': 20
        }
    
    def check_security_metrics(self):
        """Check security metrics and trigger alerts if needed"""
        metrics = self._collect_security_metrics()
        
        if metrics['violations_per_hour'] > self.alert_thresholds['violations_per_hour']:
            self._send_security_alert('High violation rate detected')
        
        if metrics['failed_commits_per_day'] > self.alert_thresholds['failed_commits_per_day']:
            self._send_security_alert('High commit failure rate')
```

This comprehensive git commit security framework ensures that all code changes undergo rigorous security verification before entering the repository, maintaining the integrity and security of the codebase.

## Best Practices

### 1. Input Validation

- **Validate All Inputs**: Use JSON Schema for structured validation
- **Sanitize Data**: Clean inputs before processing
- **Enforce Length Limits**: Prevent resource exhaustion
- **Use Allow Lists**: Prefer allow lists over block lists
- **Validate File Paths**: Prevent path traversal attacks

```python
# Example: Secure input validation
def validate_agent_input(agent_data: Dict[str, Any]) -> ValidationResult:
    """Secure agent input validation"""
    # Schema validation
    validator = AgentValidator()
    result = validator.validate(agent_data)
    
    # Additional security checks
    if result.is_valid:
        # Check for suspicious content
        content_checker = ContentSecurityChecker()
        security_result = content_checker.check_content(agent_data)
        result.merge(security_result)
    
    return result
```

### 2. File Security

- **Validate File Paths**: Always validate and sanitize file paths
- **Use Absolute Paths**: Resolve paths to prevent traversal
- **Set File Permissions**: Use appropriate file permissions (644/755)
- **Limit File Sizes**: Enforce reasonable file size limits
- **Scan File Content**: Check for malicious content

```python
# Example: Secure file operations
def secure_file_write(file_path: str, content: str) -> bool:
    """Securely write file with validation"""
    # Validate and sanitize path
    safe_path = path_security.sanitize_path(file_path)
    if not safe_path:
        return False
    
    # Validate content
    if not content_validator.validate_content(content):
        return False
    
    # Write with secure permissions
    try:
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.chmod(safe_path, 0o644)
        return True
    except Exception:
        return False
```

### 3. Authentication Security

- **Use Strong Authentication**: Implement JWT or similar token-based auth
- **Token Expiration**: Set appropriate token expiration times
- **Secure Token Storage**: Store tokens securely
- **Rate Limiting**: Implement rate limiting for authentication attempts
- **Audit Authentication**: Log all authentication attempts

### 4. Configuration Security

- **Encrypt Sensitive Data**: Encrypt passwords and keys at rest
- **Environment Variables**: Use environment variables for secrets
- **Configuration Validation**: Validate all configuration settings
- **Access Control**: Limit access to configuration files
- **Regular Updates**: Keep security configurations updated

### 5. Monitoring and Incident Response

- **Security Logging**: Log all security-relevant events
- **Anomaly Detection**: Monitor for unusual patterns
- **Alert Systems**: Set up alerts for security events
- **Incident Response**: Have procedures for security incidents
- **Regular Security Reviews**: Conduct periodic security assessments

This security guide provides comprehensive protection strategies for Claude MPM. Regular security reviews and updates ensure the framework maintains strong security posture against evolving threats.