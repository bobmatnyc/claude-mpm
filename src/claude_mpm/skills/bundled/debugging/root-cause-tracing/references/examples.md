# Real-World Tracing Examples

Detailed examples showing complete root cause tracing processes with full trace chains and solutions.

## Example 1: Git Init in Wrong Directory

### The Symptom

**Observed behavior:**
```bash
$ npm test
...
Error: fatal: .git directory created in /Users/jesse/project/packages/core
```

Tests were creating a `.git` directory in the source code folder instead of a temporary directory.

### Initial Investigation

**First thought:** "Just validate the directory parameter in git init"

**WRONG:** This would be a symptom fix. We need to find WHY the directory is wrong.

### The Trace

#### Step 1: Find Immediate Cause

```typescript
// worktree-manager.ts:45
async function createSessionWorktree(projectDir: string, sessionId: string) {
  // This line creates .git in wrong place
  await execFileAsync('git', ['init'], { cwd: projectDir });
}
```

**Discovery:** `projectDir` is an empty string `''`
**Why is this wrong:** Empty string as `cwd` resolves to `process.cwd()` (current directory)

#### Step 2: Where Does Empty String Come From?

```typescript
// session.ts:34
static async create(name: string, projectDir: string) {
  const session = new Session(name);
  await session.initializeWorkspace(projectDir); // ← calls worktree manager
  return session;
}
```

**Discovery:** Session.create() receives `projectDir = ''`
**Question:** Where does Session.create() get this value?

#### Step 3: Trace to Caller

```typescript
// project.ts:67
static async create(name: string, directory: string) {
  await Session.create(name, directory); // ← passes directory through
  // ...
}
```

**Discovery:** Project.create() also receives `directory = ''`
**Question:** What calls Project.create() with empty string?

#### Step 4: Check Test Code

```typescript
// project.test.ts:12
const context = setupCoreTest();
const PROJECT_DIR = context.tempDir; // ← Accessed at module load time!

describe('Project', () => {
  it('should create project', async () => {
    await Project.create('test-project', PROJECT_DIR);
  });
});
```

**Discovery:** `PROJECT_DIR` is set to `context.tempDir` at module load time
**Question:** What is `context.tempDir` at module load time?

#### Step 5: Root Cause Found

```typescript
// test-setup.ts
export function setupCoreTest() {
  let _tempDir = ''; // ← Initial value is empty string

  beforeEach(() => {
    _tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'test-'));
  });

  afterEach(() => {
    if (_tempDir) fs.rmSync(_tempDir, { recursive: true });
  });

  return {
    tempDir: _tempDir // ← Returns empty string at module load time
  };
}
```

**ROOT CAUSE:** The test accesses `context.tempDir` at module load time (when defining `PROJECT_DIR`), but `_tempDir` is only set during `beforeEach`. At module load time, it's still `''`.

### The Solution

#### Fix at Source

```typescript
export function setupCoreTest() {
  let _tempDir: string | null = null; // ← null instead of empty string

  beforeEach(() => {
    _tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'test-'));
  });

  afterEach(() => {
    if (_tempDir) fs.rmSync(_tempDir, { recursive: true });
    _tempDir = null;
  });

  return {
    get tempDir(): string {
      if (!_tempDir) {
        throw new Error('tempDir accessed before beforeEach ran');
      }
      return _tempDir;
    }
  };
}
```

**Why this works:**
- Accessing `context.tempDir` at module load time now throws immediately
- Forces tests to access it only within test cases
- Clear error message guides developers to fix

#### Add Defense-in-Depth

```typescript
// Layer 1: Project.create() validates directory
static async create(name: string, directory: string) {
  if (!directory || directory.trim() === '') {
    throw new Error('Project directory cannot be empty');
  }
  // ...
}

// Layer 2: WorkspaceManager validates not empty
async function initializeWorkspace(projectDir: string) {
  if (!projectDir) {
    throw new Error('projectDir cannot be empty');
  }
  // ...
}

// Layer 3: NODE_ENV guard refuses git init outside tmpdir
async function createSessionWorktree(projectDir: string, sessionId: string) {
  if (process.env.NODE_ENV === 'test' && !projectDir.includes('tmp')) {
    throw new Error(`Test safety: refusing git init outside tmpdir: ${projectDir}`);
  }
  await execFileAsync('git', ['init'], { cwd: projectDir });
}

// Layer 4: Stack trace logging before git init
async function createSessionWorktree(projectDir: string, sessionId: string) {
  if (!projectDir || projectDir === process.cwd()) {
    console.error('DEBUG git init:', {
      projectDir,
      cwd: process.cwd(),
      stack: new Error().stack
    });
  }
  await execFileAsync('git', ['init'], { cwd: projectDir });
}
```

### Results

- 1847 tests passed
- Zero `.git` pollution
- Clear error message for similar issues
- Multiple layers prevent similar bugs

### Time Saved

**With root cause tracing:** 45 minutes
**Without (symptom fixes):** 3+ hours of whack-a-mole

## Example 2: Database Connection URL Wrong

### The Symptom

```
Error: Connection failed: database "undefined" does not exist
  at Database.connect (database.ts:34)
```

Application crashes on startup because database name is undefined.

### The Trace

#### Step 1: Find Immediate Cause

```typescript
// database.ts:34
async function connect(url: string) {
  this.connection = await pg.connect(url); // ← Crashes here
}
```

**Discovery:** `url = "postgresql://localhost/undefined"`
**Why is this wrong:** Database name is literally the string "undefined"

#### Step 2: Where Does URL Come From?

```typescript
// database.ts:12
constructor(config: DatabaseConfig) {
  this.url = `postgresql://${config.host}/${config.database}`; // ← constructs URL
}
```

**Discovery:** `config.database = undefined`
**Question:** Where does config come from?

#### Step 3: Trace to Configuration Loading

```typescript
// app.ts:23
const dbConfig: DatabaseConfig = {
  host: process.env.DATABASE_HOST || 'localhost',
  database: process.env.DATABASE_NAME, // ← No default value!
  port: parseInt(process.env.DATABASE_PORT || '5432')
};
```

**Discovery:** `DATABASE_NAME` environment variable is not set
**Question:** Why isn't it set?

#### Step 4: Check Environment Setup

```typescript
// .env file
DATABASE_HOST=localhost
DATABASE_PORT=5432
# DATABASE_NAME missing!
```

**ROOT CAUSE:** Environment variable not defined, and code doesn't validate required variables.

### The Solution

#### Fix at Source

```typescript
// config.ts - Load and validate environment
export function loadDatabaseConfig(): DatabaseConfig {
  const requiredEnvVars = ['DATABASE_NAME', 'DATABASE_HOST'];
  const missing = requiredEnvVars.filter(v => !process.env[v]);

  if (missing.length > 0) {
    throw new Error(`Required environment variables missing: ${missing.join(', ')}`);
  }

  return {
    host: process.env.DATABASE_HOST!,
    database: process.env.DATABASE_NAME!,
    port: parseInt(process.env.DATABASE_PORT || '5432')
  };
}
```

#### Add Defense-in-Depth

```typescript
// Layer 1: Type-safe config with validation
interface DatabaseConfig {
  host: string;
  database: string;
  port: number;
}

// Layer 2: Constructor validates config
constructor(config: DatabaseConfig) {
  if (!config.database || config.database === 'undefined') {
    throw new Error('Database name cannot be empty or undefined');
  }
  this.url = `postgresql://${config.host}/${config.database}`;
}

// Layer 3: Validate URL before connect
async function connect(url: string) {
  if (url.includes('/undefined')) {
    throw new Error(`Invalid database URL: ${url}`);
  }
  this.connection = await pg.connect(url);
}
```

### Results

- Application fails fast at startup with clear error
- Developers immediately know which env var is missing
- Prevents confusing "database undefined does not exist" error

## Example 3: User ID = 0 in Database Query

### The Symptom

```
Error: Cannot query user: id cannot be 0
  at UserRepository.findById (user-repository.ts:45)
```

Database query fails because user ID is 0 (invalid).

### The Trace

#### Step 1: Find Immediate Cause

```typescript
// user-repository.ts:45
async findById(id: number): Promise<User> {
  if (id === 0) {
    throw new Error('Cannot query user: id cannot be 0');
  }
  return await this.db.query('SELECT * FROM users WHERE id = ?', [id]);
}
```

**Discovery:** `id = 0` being passed to query
**Question:** Where does this come from?

#### Step 2: Trace to Caller

```typescript
// auth-middleware.ts:67
async authenticate(req: Request): Promise<User> {
  const userId = this.extractUserId(req);
  return await this.userRepo.findById(userId); // ← userId is 0
}
```

**Discovery:** `extractUserId()` returns 0
**Question:** Why does it return 0?

#### Step 3: Check ID Extraction

```typescript
// auth-middleware.ts:34
private extractUserId(req: Request): number {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) return 0; // ← Default to 0 if no token!

  const decoded = jwt.verify(token, SECRET);
  return decoded.userId;
}
```

**Discovery:** Returns 0 when no authorization header
**Question:** Why is there no authorization header?

#### Step 4: Check Request Handling

```typescript
// router.ts:23
app.get('/api/user/profile', async (req, res) => {
  const user = await authMiddleware.authenticate(req); // ← Called on public route!
  res.json(user);
});
```

**ROOT CAUSE:** Authentication middleware called on public route that doesn't require authentication. When no token present, it defaults to userId=0.

### The Solution

#### Fix at Source

```typescript
// router.ts - Separate public and protected routes
app.get('/api/public/profile', async (req, res) => {
  // Public route - no authentication
  res.json({ message: 'Public profile' });
});

app.get('/api/user/profile',
  requireAuth(), // ← Middleware throws if no auth
  async (req, res) => {
    const user = await authMiddleware.authenticate(req);
    res.json(user);
  }
);
```

#### Add Defense-in-Depth

```typescript
// Layer 1: Don't default to 0, throw instead
private extractUserId(req: Request): number {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    throw new UnauthorizedError('No authorization token provided');
  }

  const decoded = jwt.verify(token, SECRET);
  return decoded.userId;
}

// Layer 2: Validate userId before query
async findById(id: number): Promise<User> {
  if (!id || id <= 0) {
    throw new Error(`Invalid user ID: ${id}`);
  }
  return await this.db.query('SELECT * FROM users WHERE id = ?', [id]);
}

// Layer 3: Type system (use branded types)
type UserId = number & { readonly __brand: 'UserId' };

function validateUserId(id: number): UserId {
  if (!id || id <= 0) throw new Error('Invalid user ID');
  return id as UserId;
}
```

### Results

- Authentication errors are clear and immediate
- Protected routes always require authentication
- No magic "0" default that causes confusing errors

## Example 4: React Component Renders Wrong Data

### The Symptom

```
Component shows data from previous user after logout/login
```

User logs out, logs in as different user, but sees previous user's data briefly.

### The Trace

#### Step 1: Observe Behavior

- User A logs in → sees correct data
- User A logs out → data clears
- User B logs in → sees User A's data for ~100ms
- After 100ms → sees correct User B data

**Discovery:** Stale data being shown before new data loads

#### Step 2: Check Component Data Source

```typescript
// UserDashboard.tsx
function UserDashboard() {
  const user = useSelector(state => state.auth.user);
  const data = useSelector(state => state.userData.data);

  useEffect(() => {
    dispatch(fetchUserData(user.id)); // ← Fetches new data
  }, [user.id]);

  return <div>{data.name}</div>; // ← Shows stale data during fetch
}
```

**Discovery:** Redux store still has old user's data when new user logs in
**Question:** Why isn't the old data cleared?

#### Step 3: Check Login/Logout Actions

```typescript
// auth.actions.ts
export function logout() {
  return { type: 'LOGOUT' }; // ← Only clears auth state
}

// auth.reducer.ts
case 'LOGOUT':
  return { user: null }; // ← Only clears user

// userData.reducer.ts (SEPARATE REDUCER)
case 'FETCH_USER_DATA':
  return { ...state, data: action.payload }; // ← Never cleared!
```

**ROOT CAUSE:** Logout action only clears auth state, not user data. User data reducer never listens to LOGOUT action.

### The Solution

#### Fix at Source

```typescript
// userData.reducer.ts
import { LOGOUT } from './auth.actions';

case LOGOUT:
  return initialState; // ← Clear data on logout

case 'FETCH_USER_DATA':
  return { ...state, data: action.payload };
```

#### Add Defense-in-Depth

```typescript
// Layer 1: Clear all data on logout
export function logout() {
  return (dispatch) => {
    dispatch({ type: 'LOGOUT' });
    dispatch({ type: 'CLEAR_USER_DATA' });
    dispatch({ type: 'CLEAR_PREFERENCES' });
    dispatch({ type: 'CLEAR_CACHE' });
  };
}

// Layer 2: Check user ID matches before showing data
function UserDashboard() {
  const user = useSelector(state => state.auth.user);
  const userData = useSelector(state => state.userData.data);

  // Don't show data if user IDs don't match
  const dataIsValid = userData && userData.userId === user?.id;

  return <div>{dataIsValid ? userData.name : 'Loading...'}</div>;
}

// Layer 3: Reset all reducers on logout
const appReducer = combineReducers({
  auth: authReducer,
  userData: userDataReducer,
  // ...
});

const rootReducer = (state, action) => {
  if (action.type === 'LOGOUT') {
    state = undefined; // ← Reset entire store
  }
  return appReducer(state, action);
};
```

### Results

- No stale data shown after logout
- Clean state for each user session
- Prevents data leakage between users

## Common Patterns Across Examples

### Pattern: Unvalidated Input at Boundaries

**Examples:**
- Git init: Empty string not caught at entry point
- Database: Missing env var not validated at startup
- User ID: Missing token defaulted to 0

**Solution:** Validate at system boundaries (entry points, config loading)

### Pattern: State Not Cleared on Transitions

**Examples:**
- Test setup: tempDir accessed before initialization
- React: User data not cleared on logout

**Solution:** Explicit state transitions with cleanup

### Pattern: Magic Default Values

**Examples:**
- Empty string defaulting to process.cwd()
- 0 as default user ID
- undefined becoming string "undefined"

**Solution:** No magic defaults - fail fast with errors

## Takeaways

1. **Never stop at symptoms** - Always trace to root cause
2. **Fix at source** - Don't add bandaids at error point
3. **Add defense** - Multiple layers catch similar issues
4. **Document trace** - Write down call chain as you go
5. **Verify fix** - Ensure fix addresses root cause, not just symptom
