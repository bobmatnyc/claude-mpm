# Ticket Extractor

The Ticket Extractor is a core component that automatically detects actionable items in Claude's output and creates tickets in integrated tracking systems. This document covers its architecture, pattern detection, and integration capabilities.

## Overview

The Ticket Extractor provides:
- **Pattern Detection**: Identifies TODO, BUG, FEATURE, and custom patterns
- **Automatic Creation**: Creates tickets without manual intervention
- **Integration**: Seamlessly works with AI-Trackdown and other systems
- **Deduplication**: Prevents duplicate ticket creation
- **Session Tracking**: Links tickets to conversation context

## Architecture

### Component Structure

```
┌──────────────────────────────────────────────────┐
│              Ticket Extractor                     │
├──────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │  Pattern    │  │   Ticket    │  │ Trackdown│ │
│  │  Detector   │  │  Creator    │  │ Adapter  │ │
│  └──────┬──────┘  └──────┬──────┘  └─────┬────┘ │
│         │                 │                │      │
│         ▼                 ▼                ▼      │
│  ┌─────────────────────────────────────────────┐ │
│  │          Ticket Processing Pipeline         │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Core Implementation

```python
class TicketExtractor:
    """Extracts and creates tickets from Claude output"""
    
    def __init__(self, config: dict):
        self.config = config
        self.pattern_detector = PatternDetector()
        self.ticket_creator = TicketCreator()
        self.trackdown_adapter = TrackdownAdapter()
        self.session_tickets = []
        
    def process_output(self, text: str) -> List[Ticket]:
        """Process Claude output for tickets"""
        
        # 1. Detect patterns
        patterns = self.pattern_detector.detect_tickets(text)
        
        # 2. Create tickets
        tickets = []
        for pattern in patterns:
            ticket = self.create_ticket(pattern)
            if ticket:
                tickets.append(ticket)
        
        # 3. Sync with tracking system
        if self.config.get('sync_enabled', True):
            self.sync_tickets(tickets)
        
        return tickets
```

## Pattern Detection

### Built-in Patterns

The extractor recognizes several ticket patterns:

```python
class PatternDetector:
    """Detects ticket patterns in text"""
    
    PATTERNS = {
        'todo': {
            'regex': r'TODO:\s*(.+?)(?:\n|$)',
            'type': 'task',
            'priority': 'medium'
        },
        'bug': {
            'regex': r'BUG:\s*(.+?)(?:\n|$)',
            'type': 'bug',
            'priority': 'high'
        },
        'feature': {
            'regex': r'FEATURE:\s*(.+?)(?:\n|$)',
            'type': 'feature',
            'priority': 'medium'
        },
        'fixme': {
            'regex': r'FIXME:\s*(.+?)(?:\n|$)',
            'type': 'bug',
            'priority': 'high'
        },
        'note': {
            'regex': r'NOTE:\s*(.+?)(?:\n|$)',
            'type': 'note',
            'priority': 'low'
        }
    }
    
    def detect_tickets(self, text: str) -> List[TicketPattern]:
        """Detect all ticket patterns in text"""
        
        patterns = []
        
        for name, config in self.PATTERNS.items():
            regex = re.compile(config['regex'], re.MULTILINE)
            
            for match in regex.finditer(text):
                pattern = TicketPattern(
                    type=config['type'],
                    content=match.group(1).strip(),
                    priority=config['priority'],
                    position=match.span(),
                    raw_match=match.group(0)
                )
                patterns.append(pattern)
        
        return patterns
```

### Advanced Pattern Detection

Support for structured ticket formats:

```python
def detect_structured_tickets(self, text: str) -> List[TicketPattern]:
    """Detect structured multi-line tickets"""
    
    # Pattern for structured format:
    # TODO: Title here
    #   Description: More details
    #   Priority: high
    #   Tags: backend, api
    
    structured_regex = re.compile(
        r'(TODO|BUG|FEATURE):\s*(.+?)\n'
        r'(?:\s+Description:\s*(.+?)\n)?'
        r'(?:\s+Priority:\s*(low|medium|high|critical)\n)?'
        r'(?:\s+Tags:\s*(.+?)\n)?',
        re.MULTILINE
    )
    
    patterns = []
    for match in structured_regex.finditer(text):
        pattern = TicketPattern(
            type=self._map_type(match.group(1)),
            title=match.group(2).strip(),
            description=match.group(3).strip() if match.group(3) else '',
            priority=match.group(4) or 'medium',
            tags=self._parse_tags(match.group(5)) if match.group(5) else [],
            position=match.span(),
            raw_match=match.group(0)
        )
        patterns.append(pattern)
    
    return patterns
```

### Custom Pattern Support

Add custom patterns dynamically:

```python
def add_custom_pattern(self, name: str, config: dict):
    """Add a custom ticket pattern"""
    
    # Validate pattern
    try:
        re.compile(config['regex'])
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")
    
    # Add to patterns
    self.PATTERNS[name] = {
        'regex': config['regex'],
        'type': config.get('type', 'task'),
        'priority': config.get('priority', 'medium'),
        'handler': config.get('handler')  # Optional custom handler
    }
    
    logger.info(f"Added custom pattern: {name}")

# Usage
extractor.add_custom_pattern('epic', {
    'regex': r'EPIC:\s*(.+?)(?:\n|$)',
    'type': 'epic',
    'priority': 'high',
    'handler': lambda match: create_epic_ticket(match)
})
```

## Ticket Creation

### Ticket Model

```python
@dataclass
class Ticket:
    """Represents a ticket to be created"""
    
    # Core fields
    id: str
    type: str  # task, bug, feature, epic, etc.
    title: str
    description: str
    priority: str  # low, medium, high, critical
    
    # Metadata
    created_at: datetime
    session_id: str
    source: str  # 'claude-mpm'
    raw_text: str
    
    # Optional fields
    tags: List[str] = field(default_factory=list)
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    parent_id: Optional[str] = None
    
    # Integration fields
    external_id: Optional[str] = None  # ID in external system
    external_url: Optional[str] = None  # URL in external system
```

### Creation Process

```python
class TicketCreator:
    """Creates tickets from detected patterns"""
    
    def create_ticket(self, pattern: TicketPattern, context: dict) -> Ticket:
        """Create a ticket from a pattern"""
        
        # Generate unique ID
        ticket_id = self._generate_id()
        
        # Extract title and description
        title, description = self._extract_content(pattern)
        
        # Enhance with context
        description = self._enhance_description(description, context)
        
        # Create ticket
        ticket = Ticket(
            id=ticket_id,
            type=pattern.type,
            title=title,
            description=description,
            priority=pattern.priority,
            created_at=datetime.now(),
            session_id=context.get('session_id'),
            source='claude-mpm',
            raw_text=pattern.raw_match,
            tags=self._extract_tags(pattern, context)
        )
        
        # Apply enrichments
        ticket = self._enrich_ticket(ticket, context)
        
        return ticket
    
    def _enhance_description(self, description: str, context: dict) -> str:
        """Enhance ticket description with context"""
        
        enhanced = description
        
        # Add context information
        if context.get('current_file'):
            enhanced += f"\n\nFile: {context['current_file']}"
        
        if context.get('function_context'):
            enhanced += f"\n\nFunction: {context['function_context']}"
        
        if context.get('related_tickets'):
            enhanced += "\n\nRelated tickets:"
            for ticket_id in context['related_tickets']:
                enhanced += f"\n- {ticket_id}"
        
        return enhanced
```

## Deduplication

### Duplicate Detection

Prevent creating duplicate tickets:

```python
class DuplicateDetector:
    """Detects duplicate tickets"""
    
    def __init__(self):
        self.ticket_cache = {}
        self.similarity_threshold = 0.85
    
    def is_duplicate(self, ticket: Ticket) -> Optional[str]:
        """Check if ticket is duplicate, return existing ID if found"""
        
        # Quick hash check
        ticket_hash = self._compute_hash(ticket)
        if ticket_hash in self.ticket_cache:
            return self.ticket_cache[ticket_hash]
        
        # Similarity check for near-duplicates
        for existing_id, existing_ticket in self.get_recent_tickets():
            similarity = self._compute_similarity(ticket, existing_ticket)
            
            if similarity > self.similarity_threshold:
                logger.info(f"Found duplicate ticket: {existing_id}")
                return existing_id
        
        # Not a duplicate
        self.ticket_cache[ticket_hash] = ticket.id
        return None
    
    def _compute_hash(self, ticket: Ticket) -> str:
        """Compute hash for exact duplicate detection"""
        
        # Hash based on type and normalized title
        normalized_title = self._normalize_text(ticket.title)
        return hashlib.md5(
            f"{ticket.type}:{normalized_title}".encode()
        ).hexdigest()
    
    def _compute_similarity(self, ticket1: Ticket, ticket2: Ticket) -> float:
        """Compute similarity between two tickets"""
        
        if ticket1.type != ticket2.type:
            return 0.0
        
        # Use simple text similarity (can be enhanced with NLP)
        title_sim = self._text_similarity(ticket1.title, ticket2.title)
        desc_sim = self._text_similarity(
            ticket1.description[:100],  # First 100 chars
            ticket2.description[:100]
        )
        
        return (title_sim * 0.7 + desc_sim * 0.3)
```

## AI-Trackdown Integration

### Integration Architecture

```python
class TrackdownAdapter:
    """Integrates with AI-Trackdown ticket system"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = self._create_client()
        self.project_id = config.get('project_id')
    
    def sync_ticket(self, ticket: Ticket) -> dict:
        """Sync ticket with AI-Trackdown"""
        
        # Convert to Trackdown format
        trackdown_data = self._to_trackdown_format(ticket)
        
        # Check if already exists
        existing = self._find_existing(ticket)
        
        if existing:
            # Update existing ticket
            result = self.client.update_ticket(
                existing['id'],
                trackdown_data
            )
            ticket.external_id = existing['id']
        else:
            # Create new ticket
            result = self.client.create_ticket(trackdown_data)
            ticket.external_id = result['id']
        
        ticket.external_url = result.get('url')
        
        return result
    
    def _to_trackdown_format(self, ticket: Ticket) -> dict:
        """Convert ticket to AI-Trackdown format"""
        
        return {
            'title': ticket.title,
            'description': ticket.description,
            'type': self._map_ticket_type(ticket.type),
            'priority': self._map_priority(ticket.priority),
            'labels': ticket.tags,
            'custom_fields': {
                'source': 'claude-mpm',
                'session_id': ticket.session_id,
                'created_by': 'claude'
            }
        }
```

### Webhook Support

Handle updates from external systems:

```python
class TicketWebhookHandler:
    """Handles webhooks from ticket systems"""
    
    def handle_webhook(self, event: dict):
        """Process webhook event"""
        
        event_type = event.get('type')
        
        if event_type == 'ticket.updated':
            self._handle_ticket_update(event['data'])
        elif event_type == 'ticket.closed':
            self._handle_ticket_closed(event['data'])
        elif event_type == 'ticket.commented':
            self._handle_comment(event['data'])
    
    def _handle_ticket_update(self, data: dict):
        """Handle ticket update from external system"""
        
        ticket_id = data['id']
        changes = data['changes']
        
        # Update local cache
        if 'status' in changes:
            self.update_ticket_status(ticket_id, changes['status'])
        
        # Notify relevant components
        self.notify_update(ticket_id, changes)
```

## Session Integration

### Session Context

Link tickets to conversation context:

```python
class SessionTicketManager:
    """Manages tickets within a session context"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.tickets = []
        self.context = {}
    
    def add_ticket(self, ticket: Ticket):
        """Add ticket to session"""
        
        # Link to session
        ticket.session_id = self.session_id
        
        # Add session context
        ticket.metadata = {
            **ticket.metadata,
            'conversation_context': self.get_conversation_context(),
            'related_files': self.get_related_files(),
            'user_info': self.get_user_info()
        }
        
        self.tickets.append(ticket)
        
        # Update relationships
        self._update_relationships(ticket)
    
    def get_session_summary(self) -> dict:
        """Get summary of tickets in session"""
        
        return {
            'total_tickets': len(self.tickets),
            'by_type': self._count_by_type(),
            'by_priority': self._count_by_priority(),
            'timeline': self._create_timeline(),
            'relationships': self._get_relationships()
        }
```

## Configuration

### Configuration Options

```python
# config.yaml
ticket_extractor:
  enabled: true
  
  # Pattern detection
  patterns:
    - todo
    - bug
    - feature
    - fixme
  custom_patterns:
    - name: security
      regex: 'SECURITY:\s*(.+)'
      type: security
      priority: critical
  
  # Deduplication
  deduplication:
    enabled: true
    similarity_threshold: 0.85
    cache_size: 1000
  
  # Integration
  integrations:
    ai_trackdown:
      enabled: true
      project_id: "project-123"
      api_key: "${AI_TRACKDOWN_API_KEY}"
      webhook_secret: "${WEBHOOK_SECRET}"
    
    github:
      enabled: false
      repo: "owner/repo"
      labels: ["claude-mpm", "automated"]
    
    jira:
      enabled: false
      project: "PROJ"
      issue_type: "Task"
  
  # Session tracking
  session:
    link_tickets: true
    include_context: true
    max_context_length: 1000
```

### Environment Variables

```bash
# Enable/disable ticket extraction
export CLAUDE_MPM_NO_TICKETS=false

# AI-Trackdown configuration
export AI_TRACKDOWN_API_KEY="your-api-key"
export AI_TRACKDOWN_PROJECT_ID="project-123"

# Custom pattern file
export CLAUDE_MPM_CUSTOM_PATTERNS="/path/to/patterns.yaml"
```

## Usage Examples

### Basic Usage

```python
# Initialize extractor
extractor = TicketExtractor(config)

# Process Claude output
output = """
I'll help you implement this feature.

TODO: Add input validation for the API endpoint
This should validate email format and password strength.

BUG: The current implementation doesn't handle Unicode properly
We need to update the text processing to support UTF-8.

FEATURE: Add caching layer for improved performance
Implement Redis caching for frequently accessed data.
"""

# Extract tickets
tickets = extractor.process_output(output)

# Tickets are automatically created and synced
for ticket in tickets:
    print(f"Created {ticket.type}: {ticket.title}")
    print(f"  ID: {ticket.id}")
    print(f"  External URL: {ticket.external_url}")
```

### With Session Context

```python
# Create session manager
session = SessionTicketManager("session-123")

# Configure extractor with session
extractor = TicketExtractor(config)
extractor.set_session(session)

# Process output with context
context = {
    'current_file': 'api/endpoints.py',
    'function_context': 'create_user_endpoint',
    'related_tickets': ['TASK-123', 'BUG-456']
}

tickets = extractor.process_output(output, context)
```

### Custom Integration

```python
# Create custom integration
class SlackIntegration:
    def sync_ticket(self, ticket: Ticket):
        # Post to Slack channel
        self.slack_client.post_message(
            channel="#tickets",
            text=f"New {ticket.type}: {ticket.title}",
            attachments=[{
                'color': self.get_color(ticket.priority),
                'fields': [
                    {'title': 'Priority', 'value': ticket.priority},
                    {'title': 'Session', 'value': ticket.session_id}
                ]
            }]
        )

# Register integration
extractor.add_integration('slack', SlackIntegration())
```

## Monitoring and Analytics

### Ticket Metrics

```python
class TicketMetrics:
    """Track ticket extraction metrics"""
    
    def __init__(self):
        self.metrics = {
            'tickets_created': 0,
            'tickets_by_type': defaultdict(int),
            'tickets_by_priority': defaultdict(int),
            'duplicates_prevented': 0,
            'sync_failures': 0
        }
    
    def record_ticket(self, ticket: Ticket):
        """Record ticket creation"""
        
        self.metrics['tickets_created'] += 1
        self.metrics['tickets_by_type'][ticket.type] += 1
        self.metrics['tickets_by_priority'][ticket.priority] += 1
    
    def get_summary(self) -> dict:
        """Get metrics summary"""
        
        return {
            'total_tickets': self.metrics['tickets_created'],
            'breakdown': {
                'by_type': dict(self.metrics['tickets_by_type']),
                'by_priority': dict(self.metrics['tickets_by_priority'])
            },
            'efficiency': {
                'duplicates_prevented': self.metrics['duplicates_prevented'],
                'sync_success_rate': self._calculate_sync_rate()
            }
        }
```

## Testing

### Unit Tests

```python
def test_pattern_detection():
    detector = PatternDetector()
    
    text = "TODO: Fix authentication bug"
    patterns = detector.detect_tickets(text)
    
    assert len(patterns) == 1
    assert patterns[0].type == 'task'
    assert patterns[0].content == 'Fix authentication bug'

def test_duplicate_detection():
    detector = DuplicateDetector()
    
    ticket1 = Ticket(
        id='1',
        type='bug',
        title='Fix authentication issue',
        description='Users cannot login'
    )
    
    ticket2 = Ticket(
        id='2',
        type='bug',
        title='Fix authentication problem',  # Similar title
        description='Users cannot login'
    )
    
    # First ticket is not duplicate
    assert detector.is_duplicate(ticket1) is None
    
    # Second ticket is duplicate
    assert detector.is_duplicate(ticket2) == '1'
```

### Integration Tests

```python
def test_trackdown_integration():
    # Mock Trackdown client
    mock_client = Mock()
    mock_client.create_ticket.return_value = {
        'id': 'TRACK-123',
        'url': 'https://trackdown.ai/tickets/TRACK-123'
    }
    
    adapter = TrackdownAdapter(config)
    adapter.client = mock_client
    
    ticket = Ticket(
        id='local-1',
        type='task',
        title='Test ticket',
        description='Test description'
    )
    
    result = adapter.sync_ticket(ticket)
    
    assert ticket.external_id == 'TRACK-123'
    assert ticket.external_url == 'https://trackdown.ai/tickets/TRACK-123'
```

## Best Practices

### 1. Clear Ticket Formatting

```
# Good: Clear, actionable tickets
TODO: Implement rate limiting for API endpoints
  - Add Redis-based rate limiter
  - Configure limits per endpoint
  - Return 429 status when exceeded

# Bad: Vague tickets
TODO: fix stuff
```

### 2. Use Appropriate Types

```
BUG: Data corruption when saving Unicode
FEATURE: Add export to PDF functionality
TODO: Refactor database queries for performance
SECURITY: SQL injection vulnerability in search
```

### 3. Include Context

```python
# Configure extractor to capture context
extractor.config['capture_context'] = True
extractor.config['context_lines'] = 5  # Lines around ticket
```

### 4. Handle Failures Gracefully

```python
try:
    tickets = extractor.process_output(output)
except TicketExtractionError as e:
    logger.error(f"Failed to extract tickets: {e}")
    # Continue without tickets
except IntegrationError as e:
    logger.error(f"Failed to sync tickets: {e}")
    # Store locally for later sync
    extractor.queue_for_retry(tickets)
```

## Next Steps

- See [Orchestrators](orchestrators.md) for output processing
- Review [Hook Service](hook-service.md) for ticket hooks
- Check [API Reference](../04-api-reference/services-api.md#ticket-extractor) for complete API