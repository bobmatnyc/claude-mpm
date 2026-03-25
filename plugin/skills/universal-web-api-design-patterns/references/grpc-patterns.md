# gRPC Patterns - Deep Dive

Comprehensive gRPC service design, streaming patterns, error handling, interceptors, and production deployment strategies.

## Protocol Buffers (Protobuf)

### Basic Message Definition

```protobuf
syntax = "proto3";

package users.v1;

// Import well-known types
import "google/protobuf/timestamp.proto";
import "google/protobuf/empty.proto";

// User message
message User {
  string id = 1;
  string email = 2;
  string name = 3;
  UserRole role = 4;
  google.protobuf.Timestamp created_at = 5;
  google.protobuf.Timestamp updated_at = 6;
}

// Enum for user roles
enum UserRole {
  USER_ROLE_UNSPECIFIED = 0;  // Required first value
  USER_ROLE_USER = 1;
  USER_ROLE_ADMIN = 2;
  USER_ROLE_MODERATOR = 3;
}
```

### Field Numbering Best Practices

✅ **Good: Strategic numbering**
```protobuf
message User {
  // 1-15: Single-byte encoding (most common fields)
  string id = 1;
  string email = 2;
  string name = 3;

  // 16-2047: Two-byte encoding (less common fields)
  string bio = 16;
  string website = 17;

  // 19000-19999: Reserved range (do not use)
  // 20000+: Multi-byte encoding (rare fields)
}
```

❌ **Bad: Random numbering**
```protobuf
message User {
  string id = 100;      // Wastes encoding space
  string email = 3;
  string name = 15000;  // Very inefficient
}
```

### Nested Messages

```protobuf
message User {
  string id = 1;
  string email = 2;
  Profile profile = 3;

  message Profile {
    string bio = 1;
    string avatar_url = 2;
    Address address = 3;

    message Address {
      string street = 1;
      string city = 2;
      string country = 3;
      string postal_code = 4;
    }
  }
}
```

### Repeated Fields (Arrays)

```protobuf
message User {
  string id = 1;
  repeated string tags = 2;           // Array of strings
  repeated Role roles = 3;            // Array of enums
  repeated Address addresses = 4;     // Array of messages
}
```

### Maps

```protobuf
message User {
  string id = 1;
  map<string, string> metadata = 2;        // String map
  map<string, int32> settings = 3;         // Mixed types
  map<string, Address> addresses = 4;      // Complex values
}
```

### Oneofs (Union Types)

```protobuf
message SearchRequest {
  string query = 1;

  oneof filter {
    UserFilter user_filter = 2;
    PostFilter post_filter = 3;
    CommentFilter comment_filter = 4;
  }
}

message UserFilter {
  UserRole role = 1;
  bool is_active = 2;
}
```

### Reserved Fields

```protobuf
message User {
  reserved 4, 5, 6;                    // Reserved field numbers
  reserved "old_field", "deprecated";  // Reserved field names

  string id = 1;
  string email = 2;
  string name = 3;
  // Fields 4-6 cannot be reused
  string new_field = 7;
}
```

## Service Definition

### Unary RPC (Request/Response)

```protobuf
service UserService {
  rpc GetUser(GetUserRequest) returns (User) {}
  rpc CreateUser(CreateUserRequest) returns (User) {}
  rpc UpdateUser(UpdateUserRequest) returns (User) {}
  rpc DeleteUser(DeleteUserRequest) returns (google.protobuf.Empty) {}
}

message GetUserRequest {
  string id = 1;
}

message CreateUserRequest {
  string email = 1;
  string name = 2;
  UserRole role = 3;
}

message UpdateUserRequest {
  string id = 1;
  optional string email = 2;
  optional string name = 3;
  optional UserRole role = 4;
}

message DeleteUserRequest {
  string id = 1;
}
```

### Server Streaming RPC

Server sends multiple messages in response to single client request:

```protobuf
service UserService {
  // Stream all users
  rpc ListUsers(ListUsersRequest) returns (stream User) {}

  // Stream user events
  rpc WatchUser(WatchUserRequest) returns (stream UserEvent) {}
}

message ListUsersRequest {
  int32 page_size = 1;
  string page_token = 2;
  UserRole role = 3;
}

message WatchUserRequest {
  string user_id = 1;
}

message UserEvent {
  string event_id = 1;
  EventType type = 2;
  User user = 3;
  google.protobuf.Timestamp timestamp = 4;
}

enum EventType {
  EVENT_TYPE_UNSPECIFIED = 0;
  EVENT_TYPE_CREATED = 1;
  EVENT_TYPE_UPDATED = 2;
  EVENT_TYPE_DELETED = 3;
}
```

### Client Streaming RPC

Client sends multiple messages, server responds once:

```protobuf
service UserService {
  // Bulk create users
  rpc BulkCreateUsers(stream CreateUserRequest) returns (BulkCreateUsersResponse) {}

  // Upload user data
  rpc UploadUserData(stream UserDataChunk) returns (UploadResponse) {}
}

message BulkCreateUsersResponse {
  int32 created_count = 1;
  repeated User users = 2;
  repeated Error errors = 3;
}

message UserDataChunk {
  bytes data = 1;
  int32 chunk_number = 2;
}

message UploadResponse {
  int64 bytes_received = 1;
  string file_id = 2;
}
```

### Bidirectional Streaming RPC

Both client and server send multiple messages:

```protobuf
service ChatService {
  rpc Chat(stream ChatMessage) returns (stream ChatMessage) {}
}

message ChatMessage {
  string id = 1;
  string user_id = 2;
  string text = 3;
  google.protobuf.Timestamp sent_at = 4;
}
```

## Server Implementation

### Go Server

```go
package main

import (
    "context"
    "log"
    "net"

    "google.golang.org/grpc"
    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"
    pb "myapp/proto/users/v1"
)

type server struct {
    pb.UnimplementedUserServiceServer
    db *Database
}

// Unary RPC
func (s *server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.User, error) {
    if req.Id == "" {
        return nil, status.Error(codes.InvalidArgument, "user ID is required")
    }

    user, err := s.db.GetUser(ctx, req.Id)
    if err != nil {
        if errors.Is(err, sql.ErrNoRows) {
            return nil, status.Error(codes.NotFound, "user not found")
        }
        return nil, status.Error(codes.Internal, "database error")
    }

    return &pb.User{
        Id:    user.ID,
        Email: user.Email,
        Name:  user.Name,
        Role:  pb.UserRole(user.Role),
    }, nil
}

// Server streaming RPC
func (s *server) ListUsers(req *pb.ListUsersRequest, stream pb.UserService_ListUsersServer) error {
    users, err := s.db.ListUsers(stream.Context(), req)
    if err != nil {
        return status.Error(codes.Internal, "failed to fetch users")
    }

    for _, user := range users {
        if err := stream.Send(&pb.User{
            Id:    user.ID,
            Email: user.Email,
            Name:  user.Name,
        }); err != nil {
            return status.Error(codes.Internal, "failed to send user")
        }
    }

    return nil
}

// Client streaming RPC
func (s *server) BulkCreateUsers(stream pb.UserService_BulkCreateUsersServer) error {
    var users []*pb.User
    var errors []*pb.Error

    for {
        req, err := stream.Recv()
        if err == io.EOF {
            // Client finished sending
            return stream.SendAndClose(&pb.BulkCreateUsersResponse{
                CreatedCount: int32(len(users)),
                Users:        users,
                Errors:       errors,
            })
        }
        if err != nil {
            return status.Error(codes.Internal, "failed to receive request")
        }

        user, err := s.db.CreateUser(stream.Context(), req)
        if err != nil {
            errors = append(errors, &pb.Error{
                Message: err.Error(),
                Field:   "email",
            })
            continue
        }

        users = append(users, user)
    }
}

// Bidirectional streaming RPC
func (s *server) Chat(stream pb.ChatService_ChatServer) error {
    for {
        msg, err := stream.Recv()
        if err == io.EOF {
            return nil
        }
        if err != nil {
            return status.Error(codes.Internal, "failed to receive message")
        }

        // Process message
        response := &pb.ChatMessage{
            Id:     generateID(),
            UserId: "bot",
            Text:   fmt.Sprintf("Echo: %s", msg.Text),
            SentAt: timestamppb.Now(),
        }

        if err := stream.Send(response); err != nil {
            return status.Error(codes.Internal, "failed to send message")
        }
    }
}

func main() {
    lis, err := net.Listen("tcp", ":50051")
    if err != nil {
        log.Fatalf("failed to listen: %v", err)
    }

    s := grpc.NewServer()
    pb.RegisterUserServiceServer(s, &server{db: newDatabase()})

    log.Printf("server listening at %v", lis.Addr())
    if err := s.Serve(lis); err != nil {
        log.Fatalf("failed to serve: %v", err)
    }
}
```

### Node.js/TypeScript Server

```typescript
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import { UserServiceHandlers } from './proto/users/v1/user_service';

const packageDefinition = protoLoader.loadSync('proto/users/v1/user.proto', {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const userProto = grpc.loadPackageDefinition(packageDefinition).users.v1;

const server = new grpc.Server();

const userService: UserServiceHandlers = {
  // Unary RPC
  getUser: async (call, callback) => {
    const { id } = call.request;

    if (!id) {
      return callback({
        code: grpc.status.INVALID_ARGUMENT,
        message: 'User ID is required',
      });
    }

    try {
      const user = await db.users.findUnique({ where: { id } });

      if (!user) {
        return callback({
          code: grpc.status.NOT_FOUND,
          message: 'User not found',
        });
      }

      callback(null, {
        id: user.id,
        email: user.email,
        name: user.name,
        role: user.role,
      });
    } catch (error) {
      callback({
        code: grpc.status.INTERNAL,
        message: 'Database error',
      });
    }
  },

  // Server streaming RPC
  listUsers: async (call) => {
    const users = await db.users.findMany();

    for (const user of users) {
      call.write({
        id: user.id,
        email: user.email,
        name: user.name,
      });
    }

    call.end();
  },

  // Client streaming RPC
  bulkCreateUsers: async (call, callback) => {
    const users: any[] = [];
    const errors: any[] = [];

    call.on('data', async (request) => {
      try {
        const user = await db.users.create({ data: request });
        users.push(user);
      } catch (error) {
        errors.push({ message: error.message, field: 'email' });
      }
    });

    call.on('end', () => {
      callback(null, {
        created_count: users.length,
        users,
        errors,
      });
    });

    call.on('error', (error) => {
      callback({
        code: grpc.status.INTERNAL,
        message: error.message,
      });
    });
  },

  // Bidirectional streaming RPC
  chat: (call) => {
    call.on('data', (message) => {
      // Echo message back
      call.write({
        id: generateId(),
        user_id: 'bot',
        text: `Echo: ${message.text}`,
        sent_at: new Date(),
      });
    });

    call.on('end', () => {
      call.end();
    });
  },
};

server.addService(userProto.UserService.service, userService);

server.bindAsync(
  '0.0.0.0:50051',
  grpc.ServerCredentials.createInsecure(),
  (err, port) => {
    if (err) {
      console.error('Failed to bind server:', err);
      return;
    }
    console.log(`Server running on port ${port}`);
    server.start();
  }
);
```

## Client Implementation

### Go Client

```go
package main

import (
    "context"
    "log"
    "time"

    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
    pb "myapp/proto/users/v1"
)

func main() {
    conn, err := grpc.Dial("localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
    if err != nil {
        log.Fatalf("did not connect: %v", err)
    }
    defer conn.Close()

    client := pb.NewUserServiceClient(conn)
    ctx, cancel := context.WithTimeout(context.Background(), time.Second*10)
    defer cancel()

    // Unary call
    user, err := client.GetUser(ctx, &pb.GetUserRequest{Id: "123"})
    if err != nil {
        log.Fatalf("could not get user: %v", err)
    }
    log.Printf("User: %v", user)

    // Server streaming call
    stream, err := client.ListUsers(ctx, &pb.ListUsersRequest{PageSize: 10})
    if err != nil {
        log.Fatalf("could not list users: %v", err)
    }

    for {
        user, err := stream.Recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            log.Fatalf("error receiving: %v", err)
        }
        log.Printf("User: %v", user)
    }

    // Client streaming call
    bulkStream, err := client.BulkCreateUsers(ctx)
    if err != nil {
        log.Fatalf("could not create bulk stream: %v", err)
    }

    users := []*pb.CreateUserRequest{
        {Email: "alice@example.com", Name: "Alice"},
        {Email: "bob@example.com", Name: "Bob"},
    }

    for _, req := range users {
        if err := bulkStream.Send(req); err != nil {
            log.Fatalf("failed to send: %v", err)
        }
    }

    response, err := bulkStream.CloseAndRecv()
    if err != nil {
        log.Fatalf("failed to receive response: %v", err)
    }
    log.Printf("Created %d users", response.CreatedCount)
}
```

### TypeScript Client

```typescript
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';

const packageDefinition = protoLoader.loadSync('proto/users/v1/user.proto');
const userProto = grpc.loadPackageDefinition(packageDefinition).users.v1;

const client = new userProto.UserService(
  'localhost:50051',
  grpc.credentials.createInsecure()
);

// Unary call
client.getUser({ id: '123' }, (error, response) => {
  if (error) {
    console.error('Error:', error);
    return;
  }
  console.log('User:', response);
});

// Promise wrapper for unary calls
function getUserAsync(id: string): Promise<any> {
  return new Promise((resolve, reject) => {
    client.getUser({ id }, (error, response) => {
      if (error) reject(error);
      else resolve(response);
    });
  });
}

// Server streaming call
const stream = client.listUsers({ page_size: 10 });

stream.on('data', (user) => {
  console.log('User:', user);
});

stream.on('end', () => {
  console.log('Stream ended');
});

stream.on('error', (error) => {
  console.error('Stream error:', error);
});

// Client streaming call
const bulkStream = client.bulkCreateUsers((error, response) => {
  if (error) {
    console.error('Error:', error);
    return;
  }
  console.log(`Created ${response.created_count} users`);
});

bulkStream.write({ email: 'alice@example.com', name: 'Alice' });
bulkStream.write({ email: 'bob@example.com', name: 'Bob' });
bulkStream.end();
```

## Error Handling

### gRPC Status Codes

```go
import "google.golang.org/grpc/codes"

// codes.OK                 - Success
// codes.Canceled           - Operation canceled
// codes.Unknown            - Unknown error
// codes.InvalidArgument    - Invalid client input
// codes.DeadlineExceeded   - Timeout
// codes.NotFound           - Resource not found
// codes.AlreadyExists      - Resource already exists
// codes.PermissionDenied   - No permission
// codes.ResourceExhausted  - Rate limit, quota
// codes.FailedPrecondition - System state invalid
// codes.Aborted            - Concurrency conflict
// codes.OutOfRange         - Out of valid range
// codes.Unimplemented      - Not implemented
// codes.Internal           - Internal server error
// codes.Unavailable        - Service unavailable
// codes.DataLoss           - Data corruption
// codes.Unauthenticated    - Invalid credentials
```

### Rich Error Details

```go
import (
    "google.golang.org/genproto/googleapis/rpc/errdetails"
    "google.golang.org/grpc/status"
)

func (s *server) CreateUser(ctx context.Context, req *pb.CreateUserRequest) (*pb.User, error) {
    // Validation errors
    if req.Email == "" || !strings.Contains(req.Email, "@") {
        st := status.New(codes.InvalidArgument, "invalid email")

        br := &errdetails.BadRequest{
            FieldViolations: []*errdetails.BadRequest_FieldViolation{
                {
                    Field:       "email",
                    Description: "email must be valid format",
                },
            },
        }

        st, _ = st.WithDetails(br)
        return nil, st.Err()
    }

    // Quota/rate limit
    if !s.checkQuota(ctx) {
        st := status.New(codes.ResourceExhausted, "quota exceeded")

        qi := &errdetails.QuotaFailure{
            Violations: []*errdetails.QuotaFailure_Violation{
                {
                    Subject:     "user:" + getUserID(ctx),
                    Description: "API quota exceeded. Try again in 60 seconds",
                },
            },
        }

        st, _ = st.WithDetails(qi)
        return nil, st.Err()
    }

    return user, nil
}
```

**Client error handling**:
```go
user, err := client.GetUser(ctx, req)
if err != nil {
    st := status.Convert(err)
    log.Printf("Error code: %s", st.Code())
    log.Printf("Error message: %s", st.Message())

    for _, detail := range st.Details() {
        switch t := detail.(type) {
        case *errdetails.BadRequest:
            for _, violation := range t.FieldViolations {
                log.Printf("Field %s: %s", violation.Field, violation.Description)
            }
        case *errdetails.QuotaFailure:
            for _, violation := range t.Violations {
                log.Printf("Quota: %s", violation.Description)
            }
        }
    }
}
```

## Interceptors (Middleware)

### Server Interceptor (Go)

```go
import (
    "context"
    "log"
    "time"

    "google.golang.org/grpc"
)

// Unary interceptor
func loggingInterceptor(
    ctx context.Context,
    req interface{},
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (interface{}, error) {
    start := time.Now()

    // Call handler
    resp, err := handler(ctx, req)

    duration := time.Since(start)
    log.Printf("Method: %s, Duration: %v, Error: %v", info.FullMethod, duration, err)

    return resp, err
}

// Stream interceptor
func streamLoggingInterceptor(
    srv interface{},
    ss grpc.ServerStream,
    info *grpc.StreamServerInfo,
    handler grpc.StreamHandler,
) error {
    start := time.Now()

    err := handler(srv, ss)

    duration := time.Since(start)
    log.Printf("Stream: %s, Duration: %v, Error: %v", info.FullMethod, duration, err)

    return err
}

// Register interceptors
s := grpc.NewServer(
    grpc.UnaryInterceptor(loggingInterceptor),
    grpc.StreamInterceptor(streamLoggingInterceptor),
)
```

### Authentication Interceptor

```go
func authInterceptor(
    ctx context.Context,
    req interface{},
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (interface{}, error) {
    // Extract metadata
    md, ok := metadata.FromIncomingContext(ctx)
    if !ok {
        return nil, status.Error(codes.Unauthenticated, "missing metadata")
    }

    // Check authorization header
    tokens := md["authorization"]
    if len(tokens) == 0 {
        return nil, status.Error(codes.Unauthenticated, "missing token")
    }

    token := tokens[0]
    userID, err := validateToken(token)
    if err != nil {
        return nil, status.Error(codes.Unauthenticated, "invalid token")
    }

    // Add user to context
    ctx = context.WithValue(ctx, "userID", userID)

    return handler(ctx, req)
}
```

### Client Interceptor (Go)

```go
func clientLoggingInterceptor(
    ctx context.Context,
    method string,
    req, reply interface{},
    cc *grpc.ClientConn,
    invoker grpc.UnaryInvoker,
    opts ...grpc.CallOption,
) error {
    start := time.Now()

    err := invoker(ctx, method, req, reply, cc, opts...)

    log.Printf("Method: %s, Duration: %v", method, time.Since(start))

    return err
}

// Use interceptor
conn, err := grpc.Dial(
    "localhost:50051",
    grpc.WithUnaryInterceptor(clientLoggingInterceptor),
)
```

## Metadata (Headers)

### Server: Read Metadata

```go
import "google.golang.org/grpc/metadata"

func (s *server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.User, error) {
    md, ok := metadata.FromIncomingContext(ctx)
    if !ok {
        return nil, status.Error(codes.InvalidArgument, "missing metadata")
    }

    // Get header values
    tokens := md["authorization"]
    userAgent := md["user-agent"]

    log.Printf("Authorization: %v", tokens)
    log.Printf("User-Agent: %v", userAgent)

    return user, nil
}
```

### Server: Send Metadata

```go
func (s *server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.User, error) {
    // Send header
    header := metadata.Pairs("x-request-id", generateID())
    grpc.SendHeader(ctx, header)

    // Send trailer
    trailer := metadata.Pairs("x-response-time", "123ms")
    grpc.SetTrailer(ctx, trailer)

    return user, nil
}
```

### Client: Send Metadata

```go
func main() {
    ctx := context.Background()

    // Add metadata to context
    md := metadata.New(map[string]string{
        "authorization": "Bearer token123",
        "x-request-id":  generateID(),
    })
    ctx = metadata.NewOutgoingContext(ctx, md)

    // Make call with metadata
    user, err := client.GetUser(ctx, &pb.GetUserRequest{Id: "123"})
}
```

### Client: Receive Metadata

```go
var header, trailer metadata.MD

user, err := client.GetUser(
    ctx,
    req,
    grpc.Header(&header),
    grpc.Trailer(&trailer),
)

if err == nil {
    log.Printf("Header: %v", header)
    log.Printf("Trailer: %v", trailer)
}
```

## Performance Optimization

### Connection Pooling

```go
// Client-side connection pool
var (
    conn     *grpc.ClientConn
    connOnce sync.Once
)

func getConnection() *grpc.ClientConn {
    connOnce.Do(func() {
        var err error
        conn, err = grpc.Dial(
            "localhost:50051",
            grpc.WithTransportCredentials(insecure.NewCredentials()),
            grpc.WithDefaultCallOptions(
                grpc.MaxCallRecvMsgSize(10*1024*1024), // 10MB
                grpc.MaxCallSendMsgSize(10*1024*1024),
            ),
        )
        if err != nil {
            log.Fatalf("Failed to dial: %v", err)
        }
    })
    return conn
}
```

### Keep-Alive Settings

```go
// Server keep-alive
s := grpc.NewServer(
    grpc.KeepaliveParams(keepalive.ServerParameters{
        Time:    10 * time.Second, // Ping every 10s if no activity
        Timeout: 3 * time.Second,  // Wait 3s for pong
    }),
    grpc.KeepaliveEnforcementPolicy(keepalive.EnforcementPolicy{
        MinTime:             5 * time.Second, // Min time between pings
        PermitWithoutStream: true,            // Allow pings when no streams
    }),
)

// Client keep-alive
conn, err := grpc.Dial(
    "localhost:50051",
    grpc.WithKeepaliveParams(keepalive.ClientParameters{
        Time:                10 * time.Second,
        Timeout:             3 * time.Second,
        PermitWithoutStream: true,
    }),
)
```

### Compression

```go
// Enable gzip compression
conn, err := grpc.Dial(
    "localhost:50051",
    grpc.WithDefaultCallOptions(grpc.UseCompressor("gzip")),
)

// Per-call compression
user, err := client.GetUser(
    ctx,
    req,
    grpc.UseCompressor("gzip"),
)
```

## TLS/SSL Security

### Server TLS

```go
import "google.golang.org/grpc/credentials"

creds, err := credentials.NewServerTLSFromFile("server.crt", "server.key")
if err != nil {
    log.Fatalf("Failed to load TLS: %v", err)
}

s := grpc.NewServer(grpc.Creds(creds))
```

### Client TLS

```go
creds, err := credentials.NewClientTLSFromFile("ca.crt", "")
if err != nil {
    log.Fatalf("Failed to load TLS: %v", err)
}

conn, err := grpc.Dial(
    "localhost:50051",
    grpc.WithTransportCredentials(creds),
)
```

### Mutual TLS (mTLS)

```go
// Server
cert, err := tls.LoadX509KeyPair("server.crt", "server.key")
certPool := x509.NewCertPool()
ca, _ := ioutil.ReadFile("ca.crt")
certPool.AppendCertsFromPEM(ca)

creds := credentials.NewTLS(&tls.Config{
    ClientAuth:   tls.RequireAndVerifyClientCert,
    Certificates: []tls.Certificate{cert},
    ClientCAs:    certPool,
})

s := grpc.NewServer(grpc.Creds(creds))
```

## Health Checking

```protobuf
syntax = "proto3";

package grpc.health.v1;

service Health {
  rpc Check(HealthCheckRequest) returns (HealthCheckResponse);
  rpc Watch(HealthCheckRequest) returns (stream HealthCheckResponse);
}

message HealthCheckRequest {
  string service = 1;
}

message HealthCheckResponse {
  enum ServingStatus {
    UNKNOWN = 0;
    SERVING = 1;
    NOT_SERVING = 2;
    SERVICE_UNKNOWN = 3;
  }
  ServingStatus status = 1;
}
```

**Implementation**:
```go
import "google.golang.org/grpc/health/grpc_health_v1"

healthServer := health.NewServer()
healthServer.SetServingStatus("users.v1.UserService", grpc_health_v1.HealthCheckResponse_SERVING)

grpc_health_v1.RegisterHealthServer(s, healthServer)
```

## Testing

### Unit Testing

```go
import (
    "testing"

    "google.golang.org/grpc/codes"
    "google.golang.org/grpc/status"
)

func TestGetUser(t *testing.T) {
    mockDB := &MockDatabase{
        users: map[string]*User{
            "123": {ID: "123", Email: "test@example.com"},
        },
    }

    srv := &server{db: mockDB}

    user, err := srv.GetUser(context.Background(), &pb.GetUserRequest{Id: "123"})

    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }

    if user.Email != "test@example.com" {
        t.Errorf("expected test@example.com, got %s", user.Email)
    }

    // Test not found
    _, err = srv.GetUser(context.Background(), &pb.GetUserRequest{Id: "999"})
    if status.Code(err) != codes.NotFound {
        t.Errorf("expected NotFound, got %v", status.Code(err))
    }
}
```

### Integration Testing

```go
func TestUserService(t *testing.T) {
    // Start test server
    lis := bufconn.Listen(1024 * 1024)
    s := grpc.NewServer()
    pb.RegisterUserServiceServer(s, &server{db: testDB})

    go func() {
        if err := s.Serve(lis); err != nil {
            log.Fatalf("Server exited with error: %v", err)
        }
    }()
    defer s.Stop()

    // Create test client
    conn, err := grpc.DialContext(
        context.Background(),
        "bufnet",
        grpc.WithContextDialer(func(context.Context, string) (net.Conn, error) {
            return lis.Dial()
        }),
        grpc.WithInsecure(),
    )
    if err != nil {
        t.Fatalf("Failed to dial: %v", err)
    }
    defer conn.Close()

    client := pb.NewUserServiceClient(conn)

    // Test GetUser
    user, err := client.GetUser(context.Background(), &pb.GetUserRequest{Id: "123"})
    if err != nil {
        t.Fatalf("GetUser failed: %v", err)
    }

    if user.Id != "123" {
        t.Errorf("expected ID 123, got %s", user.Id)
    }
}
```

## Best Practices Summary

✅ **Use proto3**: Modern syntax, better performance
✅ **Version services**: Use package versioning (`users.v1`)
✅ **Reserve field numbers**: Protect against breaking changes
✅ **Use well-known types**: Timestamp, Duration, Empty, Any
✅ **Implement health checks**: For load balancers, Kubernetes
✅ **Enable TLS**: Encrypt traffic in production
✅ **Add interceptors**: Logging, auth, metrics
✅ **Use keep-alive**: Maintain long-lived connections
✅ **Stream large datasets**: Avoid large unary responses
✅ **Handle errors properly**: Use correct status codes with details

❌ **Don't reuse field numbers**: Reserved fields protect from bugs
❌ **Don't use HTTP/JSON for gRPC**: Use binary Protobuf
❌ **Don't ignore deadlines**: Always set request timeouts
❌ **Don't skip error details**: Provide actionable error info
❌ **Don't run without TLS**: Production must use encryption
❌ **Don't forget connection pooling**: Reuse connections

## Additional Resources

- [gRPC Official Documentation](https://grpc.io/docs/)
- [Protocol Buffers Guide](https://developers.google.com/protocol-buffers/docs/proto3)
- [gRPC Go Examples](https://github.com/grpc/grpc-go/tree/master/examples)
- [gRPC Best Practices](https://grpc.io/docs/guides/performance/)
- [gRPC Error Handling](https://grpc.io/docs/guides/error/)
- [Awesome gRPC](https://github.com/grpc-ecosystem/awesome-grpc)
