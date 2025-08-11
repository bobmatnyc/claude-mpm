# Response Tracking Development Guide

Comprehensive guide for developers working on, extending, or integrating with the Claude MPM response tracking system.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Testing Framework](#testing-framework)
3. [Extending the System](#extending-the-system)
4. [Hook Integration Details](#hook-integration-details)
5. [Request-Response Correlation](#request-response-correlation)
6. [Storage Backend Implementation](#storage-backend-implementation)
7. [Future Enhancements](#future-enhancements)
8. [Contributing Guidelines](#contributing-guidelines)

## Development Setup

### Prerequisites

- Python 3.8+
- Claude MPM development environment
- Write permissions to test directories
- Understanding of hook system architecture

### Environment Setup

```bash
# 1. Clone and setup development environment
git clone <repository-url>
cd claude-mpm
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 2. Install dependencies
pip install -e .
pip install -r requirements-dev.txt

# 3. Configure for development
export CLAUDE_MPM_DEBUG=true
export CLAUDE_MPM_RESPONSE_TRACKING_ENABLED=true

# 4. Create test directories
mkdir -p .claude-mpm/responses
chmod 755 .claude-mpm/responses
```

### Development Configuration

Create `dev-config.yaml` for development:

```yaml
response_tracking:
  enabled: true
  storage_dir: ".claude-mpm/responses-dev"
  track_all_agents: true
  excluded_agents: ["test-agent", "mock-agent"]
  min_response_length: 10
  auto_cleanup_days: 1  # Shorter for development
  max_sessions: 10
  debug_mode: true
```

### IDE Configuration

#### VS Code Settings

```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests/",
    "-v",
    "--tb=short"
  ],
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true
}
```

#### PyCharm Configuration

- Set project interpreter to `./venv/bin/python`
- Configure test runner to pytest
- Enable code coverage reporting
- Set up debugging breakpoints in key methods

## Testing Framework

### Test Structure

The response tracking system includes comprehensive tests:

```
tests/
├── test_response_tracking.py           # Core functionality tests
├── test_response_tracking_functional.py # End-to-end tests
├── test_simplified_tracking.py         # Simplified model tests
├── test_integration_flow.py            # Hook integration tests
├── test_correlation_and_format.py      # Correlation mechanism tests
└── fixtures/                          # Test data and utilities
    ├── sample_responses.json
    ├── test_sessions.json
    └── mock_agents.py
```

### Running Tests

```bash
# Run all response tracking tests
python -m pytest tests/test_response_tracking*.py -v

# Run with coverage
python -m pytest tests/test_response_tracking*.py --cov=claude_mpm.services.response_tracker

# Run specific test class
python -m pytest tests/test_response_tracking.py::TestResponseTracker -v

# Run integration tests
python -m pytest tests/test_integration_flow.py -v
```

### Test Categories

#### Unit Tests

Test individual components in isolation:

```python
def test_track_response_basic():
    """Test basic response tracking functionality."""
    tracker = ResponseTracker()
    
    response_path = tracker.track_response(
        agent_name="test-agent",
        request="Test request",
        response="Test response",
        session_id="test-session"
    )
    
    assert response_path.exists()
    assert response_path.parent.name == "test-session"
```

#### Integration Tests

Test component interactions:

```python
def test_hook_integration():
    """Test response tracking through hook system."""
    handler = ClaudeHookHandler()
    handler._initialize_response_tracking()
    
    # Simulate hook events
    pre_event = create_mock_pre_event()
    post_event = create_mock_post_event()
    
    handler.pre_tool_hook(pre_event)
    handler.post_tool_hook(post_event)
    
    # Verify response was tracked
    assert_response_tracked(post_event["session_id"])
```

#### End-to-End Tests

Test complete workflows:

```python
def test_complete_workflow():
    """Test complete response tracking workflow."""
    # Enable tracking
    os.environ["CLAUDE_MPM_RESPONSE_TRACKING_ENABLED"] = "true"
    
    # Run Claude MPM command
    result = run_claude_mpm_command("test prompt")
    
    # Verify response was tracked
    tracker = ResponseTracker()
    responses = tracker.get_latest_responses(1)
    assert len(responses) == 1
```

### Test Utilities

#### Mock Agent Responses

```python
class MockAgent:
    """Mock agent for testing response tracking."""
    
    def __init__(self, name: str):
        self.name = name
    
    def generate_response(self, request: str) -> dict:
        """Generate mock response for testing."""
        return {
            "agent": self.name,
            "request": request,
            "response": f"Mock response from {self.name} for: {request[:50]}...",
            "metadata": {
                "model": "mock-model",
                "tokens": len(request) + 100,
                "duration": 1.5,
                "tools_used": ["MockTool"]
            }
        }
```

#### Test Data Generation

```python
def generate_test_session(session_id: str, num_responses: int = 5):
    """Generate test session with multiple responses."""
    tracker = ResponseTracker()
    agents = ["engineer", "qa", "documentation", "research"]
    
    for i in range(num_responses):
        agent = agents[i % len(agents)]
        tracker.track_response(
            agent_name=agent,
            request=f"Test request {i}",
            response=f"Test response {i} from {agent}",
            session_id=session_id,
            metadata={"test_sequence": i}
        )
    
    return session_id
```

### Performance Testing

#### Load Testing

```python
import concurrent.futures
import time

def test_concurrent_tracking():
    """Test concurrent response tracking performance."""
    tracker = ResponseTracker()
    num_threads = 10
    responses_per_thread = 100
    
    def track_responses(thread_id):
        for i in range(responses_per_thread):
            tracker.track_response(
                agent_name=f"agent-{thread_id}",
                request=f"Request {i}",
                response=f"Response {i}",
                session_id=f"session-{thread_id}"
            )
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(track_responses, i) for i in range(num_threads)]
        concurrent.futures.wait(futures)
    
    elapsed = time.time() - start_time
    total_responses = num_threads * responses_per_thread
    
    print(f"Tracked {total_responses} responses in {elapsed:.2f}s")
    print(f"Rate: {total_responses / elapsed:.1f} responses/sec")
```

#### Memory Testing

```python
import psutil
import os

def test_memory_usage():
    """Test memory usage during response tracking."""
    process = psutil.Process(os.getpid())
    tracker = ResponseTracker()
    
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Track large number of responses
    for i in range(1000):
        large_response = "A" * 10000  # 10KB response
        tracker.track_response(
            agent_name="memory-test",
            request=f"Request {i}",
            response=large_response,
            session_id="memory-test-session"
        )
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"Memory increase: {memory_increase:.1f} MB")
    assert memory_increase < 50  # Should be under 50MB
```

## Extending the System

### Adding New Storage Backends

The system is designed for extensible storage backends:

#### Abstract Storage Interface

```python
from abc import ABC, abstractmethod

class ResponseStorage(ABC):
    """Abstract interface for response storage backends."""
    
    @abstractmethod
    def store_response(self, response_data: dict) -> str:
        """Store response data and return storage identifier."""
        pass
    
    @abstractmethod
    def retrieve_response(self, storage_id: str) -> dict:
        """Retrieve response data by storage identifier."""
        pass
    
    @abstractmethod
    def list_sessions(self) -> List[str]:
        """List available sessions."""
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Delete entire session."""
        pass
```

#### Database Storage Backend

```python
import sqlite3
import json

class DatabaseStorage(ResponseStorage):
    """SQLite-based storage backend for response tracking."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    request TEXT NOT NULL,
                    response TEXT NOT NULL,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_timestamp
                ON responses (session_id, timestamp)
            """)
    
    def store_response(self, response_data: dict) -> str:
        """Store response in SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO responses (session_id, agent, timestamp, request, response, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                response_data["session_id"],
                response_data["agent"],
                response_data["timestamp"],
                response_data["request"],
                response_data["response"],
                json.dumps(response_data.get("metadata", {}))
            ))
            return str(cursor.lastrowid)
```

### Custom Metadata Extractors

Extend metadata collection for specific use cases:

```python
class MetadataExtractor:
    """Extract custom metadata from responses."""
    
    def extract_code_metrics(self, response: str) -> dict:
        """Extract code-related metrics from response."""
        metrics = {
            "code_blocks": response.count("```"),
            "code_languages": self._extract_languages(response),
            "line_count": len(response.split("\n")),
            "has_imports": "import " in response,
            "function_count": response.count("def "),
            "class_count": response.count("class ")
        }
        return metrics
    
    def extract_tool_usage(self, metadata: dict) -> dict:
        """Extract and analyze tool usage patterns."""
        tools_used = metadata.get("tools_used", [])
        return {
            "tool_count": len(tools_used),
            "file_operations": len([t for t in tools_used if t in ["Read", "Write", "Edit"]]),
            "search_operations": len([t for t in tools_used if t in ["Grep", "Glob"]]),
            "execution_tools": len([t for t in tools_used if t in ["Bash", "Python"]])
        }
```

### Response Analyzers

Build analyzers for specific response patterns:

```python
class ResponseAnalyzer:
    """Analyze response patterns and quality."""
    
    def analyze_response_quality(self, response: str) -> dict:
        """Analyze response quality metrics."""
        return {
            "length": len(response),
            "word_count": len(response.split()),
            "sentence_count": response.count(".") + response.count("!") + response.count("?"),
            "code_ratio": self._calculate_code_ratio(response),
            "explanation_ratio": self._calculate_explanation_ratio(response),
            "completeness_score": self._assess_completeness(response)
        }
    
    def detect_response_patterns(self, responses: List[dict]) -> dict:
        """Detect patterns across multiple responses."""
        patterns = {
            "common_tools": self._find_common_tools(responses),
            "response_length_trend": self._analyze_length_trend(responses),
            "error_patterns": self._detect_error_patterns(responses),
            "success_indicators": self._find_success_patterns(responses)
        }
        return patterns
```

## Hook Integration Details

### Hook Event Flow

Understanding the complete hook event flow is crucial for extending the system:

```python
def pre_tool_hook(self, event: dict) -> dict:
    """Process pre-tool hook for response tracking."""
    if event.get("tool") == "Task":
        # Extract delegation request
        request_data = {
            "prompt": event.get("request", {}).get("prompt", ""),
            "description": event.get("request", {}).get("description", ""),
            "agent_type": event.get("agent_type", "unknown"),
            "session_id": event.get("session_id", "default"),
            "timestamp": datetime.now().isoformat()
        }
        
        # Store for correlation
        self.delegation_requests[event["session_id"]] = request_data
        
        # Log for debugging
        if DEBUG:
            print(f"Stored request for session {event['session_id']}", file=sys.stderr)
    
    return event

def post_tool_hook(self, event: dict) -> dict:
    """Process post-tool hook for response tracking."""
    if event.get("tool") == "Task" and self.response_tracking_enabled:
        session_id = event.get("session_id")
        agent_type = event.get("agent_type", "unknown")
        
        if session_id and session_id in self.delegation_requests:
            self._track_agent_response(session_id, agent_type, event)
    
    return event
```

### Custom Hook Handlers

Create specialized hook handlers for specific tracking needs:

```python
class DetailedResponseTrackingHook:
    """Enhanced hook handler with detailed tracking capabilities."""
    
    def __init__(self, config: dict):
        self.config = config
        self.tracker = ResponseTracker()
        self.analyzers = [
            CodeAnalyzer(),
            PerformanceAnalyzer(),
            QualityAnalyzer()
        ]
    
    def on_agent_response(self, event: dict) -> dict:
        """Enhanced response tracking with analysis."""
        # Standard tracking
        response_path = self.tracker.track_response(...)
        
        # Enhanced analysis
        analysis_results = {}
        for analyzer in self.analyzers:
            try:
                results = analyzer.analyze(event["response"])
                analysis_results[analyzer.name] = results
            except Exception as e:
                logger.warning(f"Analysis failed for {analyzer.name}: {e}")
        
        # Store analysis separately
        if analysis_results:
            analysis_path = response_path.parent / f"{response_path.stem}_analysis.json"
            with open(analysis_path, 'w') as f:
                json.dump(analysis_results, f, indent=2)
        
        return event
```

### Hook Configuration

Configure hooks for different environments:

```python
# Development configuration
dev_hook_config = {
    "response_tracking": {
        "enabled": True,
        "detailed_analysis": True,
        "store_debug_info": True,
        "analyzers": ["code", "performance", "quality"]
    }
}

# Production configuration  
prod_hook_config = {
    "response_tracking": {
        "enabled": True,
        "detailed_analysis": False,
        "store_debug_info": False,
        "analyzers": ["performance"]
    }
}
```

## Request-Response Correlation

### Correlation Mechanism Details

The correlation system ensures responses are properly matched with their original requests:

#### Correlation ID Generation

```python
import uuid
from datetime import datetime

def generate_correlation_id(session_id: str, agent_type: str) -> str:
    """Generate unique correlation ID for request-response matching."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    unique_id = str(uuid.uuid4())[:8]
    return f"{session_id}_{agent_type}_{timestamp}_{unique_id}"
```

#### Correlation Storage

```python
class CorrelationManager:
    """Manage request-response correlations with TTL."""
    
    def __init__(self, ttl_minutes: int = 5):
        self.correlations = {}
        self.ttl_minutes = ttl_minutes
    
    def store_correlation(self, correlation_id: str, request_data: dict):
        """Store correlation with timestamp."""
        self.correlations[correlation_id] = {
            "data": request_data,
            "timestamp": datetime.now(),
            "ttl": datetime.now() + timedelta(minutes=self.ttl_minutes)
        }
    
    def retrieve_correlation(self, correlation_id: str) -> Optional[dict]:
        """Retrieve and remove correlation."""
        correlation = self.correlations.pop(correlation_id, None)
        if correlation and datetime.now() < correlation["ttl"]:
            return correlation["data"]
        return None
    
    def cleanup_expired(self):
        """Remove expired correlations."""
        now = datetime.now()
        expired_keys = [
            key for key, value in self.correlations.items()
            if now > value["ttl"]
        ]
        for key in expired_keys:
            del self.correlations[key]
```

#### Advanced Correlation Features

```python
class AdvancedCorrelationManager(CorrelationManager):
    """Enhanced correlation manager with persistence and recovery."""
    
    def __init__(self, ttl_minutes: int = 5, persist_correlations: bool = True):
        super().__init__(ttl_minutes)
        self.persist_correlations = persist_correlations
        self.correlation_file = Path(".claude-mpm/correlations.json")
        
        if persist_correlations:
            self._load_correlations()
    
    def _save_correlations(self):
        """Persist correlations to disk."""
        if not self.persist_correlations:
            return
        
        serializable_correlations = {}
        for key, value in self.correlations.items():
            serializable_correlations[key] = {
                "data": value["data"],
                "timestamp": value["timestamp"].isoformat(),
                "ttl": value["ttl"].isoformat()
            }
        
        with open(self.correlation_file, 'w') as f:
            json.dump(serializable_correlations, f, indent=2)
    
    def _load_correlations(self):
        """Load correlations from disk."""
        if not self.correlation_file.exists():
            return
        
        try:
            with open(self.correlation_file, 'r') as f:
                data = json.load(f)
            
            for key, value in data.items():
                self.correlations[key] = {
                    "data": value["data"],
                    "timestamp": datetime.fromisoformat(value["timestamp"]),
                    "ttl": datetime.fromisoformat(value["ttl"])
                }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load correlations: {e}")
```

## Storage Backend Implementation

### File System Backend Details

The current file system backend implementation:

#### Directory Structure Management

```python
class FileSystemStorage(ResponseStorage):
    """File system-based storage implementation."""
    
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._setup_directory_structure()
    
    def _setup_directory_structure(self):
        """Initialize directory structure."""
        # Create subdirectories for organization
        (self.base_dir / "by_session").mkdir(exist_ok=True)
        (self.base_dir / "by_agent").mkdir(exist_ok=True)
        (self.base_dir / "by_date").mkdir(exist_ok=True)
        (self.base_dir / "metadata").mkdir(exist_ok=True)
    
    def _get_session_dir(self, session_id: str) -> Path:
        """Get session directory, creating if needed."""
        session_dir = self.base_dir / session_id
        session_dir.mkdir(exist_ok=True)
        return session_dir
    
    def _generate_filename(self, agent: str, timestamp: datetime) -> str:
        """Generate consistent filename for response."""
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S_%f')[:-3]
        return f"{agent}-{timestamp_str}.json"
```

#### File Operations

```python
    def store_response(self, response_data: dict) -> str:
        """Store response with atomic write operation."""
        session_dir = self._get_session_dir(response_data["session_id"])
        timestamp = datetime.fromisoformat(response_data["timestamp"])
        filename = self._generate_filename(response_data["agent"], timestamp)
        file_path = session_dir / filename
        
        # Atomic write using temporary file
        temp_path = file_path.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)
            
            # Atomic move
            temp_path.rename(file_path)
            return str(file_path)
        
        except Exception as e:
            # Cleanup temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise ResponseTrackingStorageError(f"Failed to store response: {e}")
```

#### Query Operations

```python
    def query_responses(
        self, 
        session_id: Optional[str] = None,
        agent: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[dict]:
        """Query responses with filters."""
        
        responses = []
        search_dirs = [self.base_dir / session_id] if session_id else self.base_dir.iterdir()
        
        for session_dir in search_dirs:
            if not session_dir.is_dir() or session_dir.name.startswith('.'):
                continue
            
            for response_file in session_dir.glob("*.json"):
                try:
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    
                    # Apply filters
                    if agent and response_data.get("agent") != agent:
                        continue
                    
                    response_time = datetime.fromisoformat(response_data["timestamp"])
                    if start_time and response_time < start_time:
                        continue
                    if end_time and response_time > end_time:
                        continue
                    
                    responses.append(response_data)
                    
                except (json.JSONDecodeError, IOError, KeyError) as e:
                    logger.warning(f"Failed to load response from {response_file}: {e}")
        
        # Sort by timestamp
        responses.sort(key=lambda x: x.get("timestamp", ""))
        
        # Apply limit
        if limit:
            responses = responses[:limit]
        
        return responses
```

### Alternative Storage Backends

#### Cloud Storage Backend

```python
import boto3
from botocore.exceptions import ClientError

class S3Storage(ResponseStorage):
    """AWS S3-based storage backend."""
    
    def __init__(self, bucket_name: str, prefix: str = "claude-mpm/responses/"):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.s3_client = boto3.client('s3')
    
    def store_response(self, response_data: dict) -> str:
        """Store response in S3."""
        key = self._generate_s3_key(response_data)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(response_data, indent=2),
                ContentType='application/json',
                Metadata={
                    'session_id': response_data["session_id"],
                    'agent': response_data["agent"],
                    'timestamp': response_data["timestamp"]
                }
            )
            return key
            
        except ClientError as e:
            raise ResponseTrackingStorageError(f"S3 storage failed: {e}")
    
    def _generate_s3_key(self, response_data: dict) -> str:
        """Generate S3 key for response."""
        session_id = response_data["session_id"]
        agent = response_data["agent"]
        timestamp = datetime.fromisoformat(response_data["timestamp"])
        timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S_%f')[:-3]
        
        return f"{self.prefix}{session_id}/{agent}-{timestamp_str}.json"
```

## Future Enhancements

### Planned Features

#### 1. Export and Import Functionality

```python
class ResponseExporter:
    """Export response data in various formats."""
    
    def export_to_csv(self, session_id: str, output_path: Path):
        """Export session responses to CSV format."""
        pass
    
    def export_to_excel(self, session_ids: List[str], output_path: Path):
        """Export multiple sessions to Excel workbook."""
        pass
    
    def export_to_json_archive(self, session_id: str, output_path: Path):
        """Export session as compressed JSON archive."""
        pass
```

#### 2. Advanced Analytics

```python
class ResponseAnalytics:
    """Advanced analytics for response data."""
    
    def generate_performance_report(self, time_range: tuple) -> dict:
        """Generate performance analysis report."""
        pass
    
    def analyze_agent_effectiveness(self, agent_name: str) -> dict:
        """Analyze agent performance and patterns."""
        pass
    
    def detect_anomalies(self, session_id: str) -> List[dict]:
        """Detect anomalous responses or patterns."""
        pass
```

#### 3. Real-time Streaming

```python
class ResponseStreamer:
    """Stream response data to external systems."""
    
    def stream_to_websocket(self, websocket_url: str):
        """Stream responses to WebSocket endpoint."""
        pass
    
    def stream_to_kafka(self, kafka_config: dict):
        """Stream responses to Kafka topic."""
        pass
    
    def stream_to_elasticsearch(self, es_config: dict):
        """Stream responses to Elasticsearch for indexing."""
        pass
```

#### 4. Machine Learning Integration

```python
class ResponseML:
    """Machine learning features for response analysis."""
    
    def train_quality_classifier(self, labeled_responses: List[dict]):
        """Train classifier for response quality assessment."""
        pass
    
    def predict_response_quality(self, response: str) -> float:
        """Predict quality score for response."""
        pass
    
    def cluster_similar_responses(self, responses: List[dict]) -> List[List[dict]]:
        """Group similar responses using clustering."""
        pass
```

### Roadmap Items

#### Short-term (Next Release)

- [ ] CLI export functionality (`claude-mpm responses export`)
- [ ] Response search and filtering improvements  
- [ ] Enhanced error reporting and recovery
- [ ] Performance optimizations for large datasets

#### Medium-term (Next 2-3 Releases)

- [ ] Alternative storage backends (SQLite, PostgreSQL)
- [ ] Real-time response streaming via WebSocket
- [ ] Advanced analytics and reporting dashboard
- [ ] Response quality assessment and scoring

#### Long-term (Future Releases)

- [ ] Machine learning-powered response analysis
- [ ] Integration with external monitoring systems
- [ ] Distributed storage for high-volume deployments
- [ ] Advanced visualization and exploration tools

### Research Areas

#### Performance Optimization

- Investigate compression techniques for response storage
- Evaluate different serialization formats (MessagePack, Protocol Buffers)
- Research indexing strategies for fast queries
- Study memory optimization for large response datasets

#### Security Enhancements  

- Implement response data encryption at rest
- Add access control and permissions system
- Develop data anonymization techniques
- Research secure multi-tenant deployments

#### Scalability Studies

- Benchmark different storage backends under load
- Evaluate horizontal scaling approaches
- Study performance impact on Claude operations
- Research optimal cleanup and archival strategies

## Contributing Guidelines

### Development Workflow

1. **Feature Planning**: Discuss proposed features in GitHub issues
2. **Branch Creation**: Create feature branch from `main`
3. **Implementation**: Follow coding standards and test requirements
4. **Testing**: Add comprehensive tests for new functionality
5. **Documentation**: Update documentation for user-facing changes
6. **Review**: Submit pull request for code review
7. **Integration**: Merge after approval and CI passes

### Code Style Guidelines

#### Python Standards

```python
# Follow PEP 8 formatting
# Use type hints for all public methods
# Add comprehensive docstrings

class ResponseProcessor:
    """Process and analyze response data.
    
    This class provides functionality for processing response data
    from agents and extracting useful insights.
    """
    
    def process_response(
        self, 
        response_data: dict, 
        options: Optional[ProcessingOptions] = None
    ) -> ProcessedResponse:
        """Process response data with specified options.
        
        Args:
            response_data: Raw response data dictionary
            options: Optional processing configuration
            
        Returns:
            ProcessedResponse: Processed response with analysis
            
        Raises:
            ProcessingError: If response data is invalid
            ConfigurationError: If options are misconfigured
        """
        pass
```

#### Error Handling Standards

```python
# Use specific exception types
class ResponseTrackingError(Exception):
    """Base exception for response tracking errors."""
    pass

class ResponseTrackingStorageError(ResponseTrackingError):
    """Storage-related errors."""
    pass

class ResponseTrackingConfigError(ResponseTrackingError):
    """Configuration-related errors."""
    pass

# Provide comprehensive error context
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(
        f"Operation failed with error: {e}",
        extra={
            "operation": "track_response",
            "session_id": session_id,
            "agent": agent_name,
            "error_type": type(e).__name__
        }
    )
    raise ResponseTrackingStorageError(f"Failed to track response: {e}") from e
```

### Testing Requirements

#### Test Coverage

- Minimum 80% code coverage for new features
- 100% coverage for critical paths (storage, correlation)
- Integration tests for hook interactions
- Performance tests for scalability features

#### Test Documentation

```python
def test_concurrent_response_tracking():
    """Test concurrent response tracking performance.
    
    This test verifies that the response tracking system can handle
    multiple concurrent requests without data corruption or performance
    degradation.
    
    Test Scenario:
    1. Create multiple threads tracking responses simultaneously
    2. Verify all responses are stored correctly
    3. Check for data consistency and integrity
    4. Measure performance metrics
    
    Expected Results:
    - All responses stored without corruption
    - No file conflicts or race conditions
    - Performance within acceptable bounds
    """
    pass
```

### Documentation Standards

#### User Documentation

- Clear, step-by-step instructions
- Real-world examples and use cases
- Troubleshooting guides with common issues
- Configuration references with all options

#### Technical Documentation

- Architecture decisions and rationale
- API documentation with examples
- Integration guides for developers
- Performance characteristics and limits

#### Code Documentation

- Comprehensive docstrings for all public interfaces
- Inline comments for complex logic
- Design decision explanations
- TODO comments for known limitations

---

*This development guide provides comprehensive information for working with the response tracking system. For user documentation, see [USER_GUIDE.md](USER_GUIDE.md). For system overview, see [README.md](README.md).*