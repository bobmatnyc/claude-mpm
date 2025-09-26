# Database Driver Configuration

## Overview

Claude MPM agents that work with databases now use intelligent fallback mechanisms to handle database connectivity. This ensures agents can work across different platforms without compilation issues.

## MySQL Connectivity

### Recommended Driver: PyMySQL

As of version 4.3.21, the Data Engineer agent uses **PyMySQL** as the default MySQL driver. PyMySQL is a pure Python implementation that:
- ✅ Requires no compilation
- ✅ Works on all platforms (macOS, Linux, Windows)
- ✅ No system dependencies required
- ✅ Easy installation: `pip install pymysql`

### Alternative Drivers

If you need higher performance and are willing to install system dependencies:

#### mysqlclient (C-based, faster)
```bash
# macOS
brew install mysql
pip install mysqlclient

# Ubuntu/Debian
sudo apt-get install libmysqlclient-dev
pip install mysqlclient

# RHEL/CentOS
sudo yum install mysql-devel
pip install mysqlclient
```

#### mysql-connector-python (Oracle's pure Python)
```bash
pip install mysql-connector-python
```

## PostgreSQL Connectivity

### Recommended Driver: psycopg2-binary

For PostgreSQL connections, use the pre-compiled binary version:
```bash
pip install psycopg2-binary
```

### Alternative Drivers

#### psycopg2 (source version, requires compilation)
```bash
# macOS
brew install postgresql
pip install psycopg2

# Ubuntu/Debian
sudo apt-get install libpq-dev
pip install psycopg2
```

#### pg8000 (pure Python alternative)
```bash
pip install pg8000
```

## Oracle Connectivity

### Recommended Driver: oracledb

The new pure Python Oracle driver requires no Oracle client:
```bash
pip install oracledb
```

### Alternative: cx_Oracle

Requires Oracle Instant Client installation:
1. Download Oracle Instant Client from oracle.com
2. Set environment variables
3. `pip install cx_Oracle`

## Automatic Fallback

Claude MPM includes a `DatabaseConnector` utility that automatically:
1. Detects available database drivers
2. Falls back to alternatives if primary drivers fail
3. Provides helpful error messages with installation instructions

### Using DatabaseConnector

```python
from claude_mpm.utils.database_connector import DatabaseConnector

# Initialize connector
connector = DatabaseConnector()

# Get connection strings with automatic driver selection
mysql_url = connector.get_mysql_connection_string(
    host="localhost",
    database="mydb",
    user="user",
    password="pass"
)

# Check available drivers
available = connector.get_available_drivers()
print(f"Available drivers: {available}")

# Get installation suggestions
suggestions = connector.suggest_missing_drivers()
for db_type, package in suggestions.items():
    print(f"Install {package} for {db_type} support")
```

## Troubleshooting

### Common Issues

#### 1. mysqlclient compilation fails on macOS

**Error:** `mysql_config not found` or `MySQL headers missing`

**Solution:** Use PyMySQL instead:
```bash
pip install pymysql
```

#### 2. psycopg2 compilation fails

**Error:** `pg_config not found` or `libpq-fe.h missing`

**Solution:** Use the binary version:
```bash
pip install psycopg2-binary
```

#### 3. cx_Oracle requires Oracle client

**Error:** `Oracle client libraries not found`

**Solution:** Use the new pure Python driver:
```bash
pip install oracledb
```

### Testing Database Connectivity

Test your database driver setup:
```bash
python -m claude_mpm.utils.database_connector
```

This will show:
- Available drivers
- Missing drivers with installation recommendations
- Detailed installation instructions

## Performance Considerations

### Speed Comparison

| Driver | Type | Relative Speed | Ease of Install |
|--------|------|---------------|-----------------|
| **MySQL** |
| mysqlclient | C-based | 100% (fastest) | Difficult (needs headers) |
| PyMySQL | Pure Python | 70-80% | Very Easy |
| mysql-connector | Pure Python | 60-70% | Very Easy |
| **PostgreSQL** |
| psycopg2 | C-based | 100% (fastest) | Difficult (needs headers) |
| psycopg2-binary | Pre-compiled | 100% | Easy |
| pg8000 | Pure Python | 60-70% | Very Easy |
| **Oracle** |
| cx_Oracle | C-based | 100% (fastest) | Difficult (needs client) |
| oracledb | Pure Python | 80-90% | Very Easy |

### Recommendations

1. **Development**: Use pure Python drivers for ease of setup
2. **Production**: Consider C-based drivers if:
   - Performance is critical
   - You can manage system dependencies
   - You have controlled deployment environment

3. **CI/CD**: Use binary wheels or pure Python drivers to avoid build issues

## Agent-Specific Configuration

### Data Engineer Agent

The Data Engineer agent automatically handles database driver fallback:
- Primary: PyMySQL (pure Python)
- Fallback: mysql-connector-python
- Manual override: mysqlclient (if you install it)

### Custom Agents

When creating custom agents with database dependencies:

```json
{
  "dependencies": {
    "python": [
      "sqlalchemy>=2.0.0",
      "pymysql>=1.1.0",  // Use pure Python by default
      // "mysqlclient>=2.2.0"  // Optional, for performance
    ]
  }
}
```

## Migration from mysqlclient to PyMySQL

If you have existing code using mysqlclient, the migration is usually seamless:

### SQLAlchemy
```python
# Before (mysqlclient)
engine = create_engine("mysql+mysqldb://user:pass@localhost/db")

# After (PyMySQL)
engine = create_engine("mysql+pymysql://user:pass@localhost/db")
```

### Direct Usage
```python
# Before
import MySQLdb
conn = MySQLdb.connect(...)

# After
import pymysql
pymysql.install_as_MySQLdb()  # Compatibility mode
import MySQLdb  # Now uses PyMySQL
conn = MySQLdb.connect(...)
```

## Summary

Claude MPM prioritizes ease of use and cross-platform compatibility:
- Default to pure Python drivers that work everywhere
- Automatic fallback when compilation-dependent packages fail
- Clear error messages with alternative suggestions
- Optional high-performance drivers for production use

This approach ensures agents work out-of-the-box while allowing power users to optimize for performance when needed.