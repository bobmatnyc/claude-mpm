---
name: flask
description: Flask - Lightweight Python web framework for microservices, REST APIs, and flexible web applications with extensive extension ecosystem
version: 1.0.0
category: toolchain
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Lightweight Python web framework for microservices and REST APIs with flexible architecture and extensive extension ecosystem"
    when_to_use: "Building microservices, REST APIs with Flask-RESTful, lightweight web apps, when flexibility over batteries-included frameworks is needed, rapid prototyping"
    quick_start: "1. pip install flask 2. Create app.py with @app.route decorators 3. flask run 4. Access http://localhost:5000"
context_limit: 700
tags:
  - flask
  - python
  - web-framework
  - microservices
  - rest-api
  - lightweight
  - blueprints
  - sqlalchemy
requires_tools: []
---

# Flask - Lightweight Python Web Framework

## Overview

Flask is a micro-framework for Python web development, designed for building microservices, REST APIs, and flexible web applications. Its minimalist core and extensive extension ecosystem make it ideal for projects requiring lightweight architecture, rapid development, and full control over components.

**Key Features**:
- Micro-framework philosophy (minimal core, extensible)
- Flask-RESTful for API development
- Blueprints for modular application structure
- SQLAlchemy integration via Flask-SQLAlchemy
- Jinja2 templating engine
- Built-in development server with auto-reload
- Werkzeug WSGI toolkit foundation
- Large extension ecosystem (Flask-Login, Flask-JWT, Flask-CORS)
- Production deployment with Gunicorn/uWSGI

**Installation**:
```bash
# Basic Flask
pip install flask

# Flask with common extensions
pip install flask flask-restful flask-sqlalchemy flask-login flask-cors

# With database support
pip install flask flask-sqlalchemy psycopg2-binary  # PostgreSQL

# Full microservices stack
pip install flask flask-restful marshmallow flask-jwt-extended redis
```

## Basic Application Patterns

### 1. Minimal Flask App

```python
# app.py
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({"message": "Hello, World!"})

@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    return jsonify({"id": user_id, "name": f"User {user_id}"})

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    return jsonify({"id": 123, **data}), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Run:**
```bash
# Development server
python app.py

# Or using flask CLI
export FLASK_APP=app.py
export FLASK_ENV=development
flask run

# Custom port
flask run --port 8000 --host 0.0.0.0
```

### 2. Application Factory Pattern

**Recommended for production and testing:**

```python
# app/__init__.py
from flask import Flask
from app.config import Config
from app.extensions import db, migrate, jwt

def create_app(config_class=Config):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Register blueprints
    from app.routes import api_bp, auth_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app

# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

# app/config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret'

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
```

**Run:**
```bash
export FLASK_APP=run.py
flask run
```

### 3. Request and Response Handling

```python
from flask import Flask, request, jsonify, make_response, abort

app = Flask(__name__)

@app.route('/api/data', methods=['GET', 'POST'])
def handle_data():
    # GET request
    if request.method == 'GET':
        # Query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        return jsonify({
            "page": page,
            "limit": limit,
            "data": [...]
        })

    # POST request
    if request.method == 'POST':
        # JSON body
        data = request.get_json()

        # Validation
        if not data or 'name' not in data:
            abort(400, description="Missing required field: name")

        # Custom response with headers
        response = make_response(jsonify({"id": 1, **data}), 201)
        response.headers['X-Custom-Header'] = 'value'
        return response

# Error handling
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": str(error.description)}), 400
```

## Blueprints - Modular Applications

### Blueprint Structure

```
app/
├── __init__.py          # Application factory
├── extensions.py        # Extension instances
├── config.py            # Configuration
├── models/
│   ├── __init__.py
│   ├── user.py
│   └── product.py
├── routes/
│   ├── __init__.py
│   ├── auth.py          # Authentication routes
│   ├── users.py         # User management routes
│   └── products.py      # Product routes
└── services/
    ├── __init__.py
    ├── user_service.py
    └── auth_service.py
```

### Blueprint Implementation

```python
# app/routes/users.py
from flask import Blueprint, jsonify, request
from app.models.user import User
from app.extensions import db

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
def list_users():
    """List all users."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    users = User.query.paginate(page=page, per_page=per_page)

    return jsonify({
        "users": [u.to_dict() for u in users.items],
        "total": users.total,
        "page": users.page,
        "pages": users.pages
    })

@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID."""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@users_bp.route('/', methods=['POST'])
def create_user():
    """Create new user."""
    data = request.get_json()

    user = User(
        email=data['email'],
        name=data['name']
    )
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201

@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        user.email = data['email']

    db.session.commit()
    return jsonify(user.to_dict())

@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete user."""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    return '', 204

# app/__init__.py
def create_app():
    app = Flask(__name__)

    # Register blueprints
    from app.routes.users import users_bp
    from app.routes.products import products_bp

    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(products_bp, url_prefix='/api/products')

    return app
```

## Flask-RESTful for APIs

### Basic REST API

```python
# app/api/resources.py
from flask import request
from flask_restful import Resource, Api, reqparse, fields, marshal_with
from app.models.user import User
from app.extensions import db

# Response serialization
user_fields = {
    'id': fields.Integer,
    'email': fields.String,
    'name': fields.String,
    'created_at': fields.DateTime(dt_format='iso8601')
}

class UserListResource(Resource):
    """User collection endpoint."""

    @marshal_with(user_fields)
    def get(self):
        """List all users."""
        users = User.query.all()
        return users

    def post(self):
        """Create new user."""
        parser = reqparse.RequestParser()
        parser.add_argument('email', required=True, help='Email is required')
        parser.add_argument('name', required=True, help='Name is required')
        parser.add_argument('password', required=True, help='Password is required')
        args = parser.parse_args()

        user = User(email=args['email'], name=args['name'])
        user.set_password(args['password'])

        db.session.add(user)
        db.session.commit()

        return {'id': user.id, 'email': user.email, 'name': user.name}, 201

class UserResource(Resource):
    """Single user endpoint."""

    @marshal_with(user_fields)
    def get(self, user_id):
        """Get user by ID."""
        user = User.query.get_or_404(user_id)
        return user

    @marshal_with(user_fields)
    def put(self, user_id):
        """Update user."""
        user = User.query.get_or_404(user_id)

        parser = reqparse.RequestParser()
        parser.add_argument('name')
        parser.add_argument('email')
        args = parser.parse_args()

        if args['name']:
            user.name = args['name']
        if args['email']:
            user.email = args['email']

        db.session.commit()
        return user

    def delete(self, user_id):
        """Delete user."""
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()

        return '', 204

# app/__init__.py
from flask_restful import Api

def create_app():
    app = Flask(__name__)
    api = Api(app, prefix='/api/v1')

    # Register resources
    from app.api.resources import UserListResource, UserResource

    api.add_resource(UserListResource, '/users')
    api.add_resource(UserResource, '/users/<int:user_id>')

    return app
```

## Request Validation

### Marshmallow Schemas

```python
# app/schemas/user_schema.py
from marshmallow import Schema, fields, validate, validates, ValidationError

class UserSchema(Schema):
    """User validation schema."""

    id = fields.Int(dump_only=True)
    email = fields.Email(required=True, validate=validate.Length(max=120))
    name = fields.Str(required=True, validate=validate.Length(min=2, max=80))
    password = fields.Str(
        required=True,
        load_only=True,
        validate=validate.Length(min=8)
    )
    created_at = fields.DateTime(dump_only=True)

    @validates('email')
    def validate_email(self, value):
        """Check email uniqueness."""
        from app.models.user import User
        if User.query.filter_by(email=value).first():
            raise ValidationError('Email already registered')

class UserUpdateSchema(Schema):
    """User update schema (partial updates)."""

    email = fields.Email(validate=validate.Length(max=120))
    name = fields.Str(validate=validate.Length(min=2, max=80))
    password = fields.Str(load_only=True, validate=validate.Length(min=8))

# Usage in routes
from marshmallow import ValidationError
from app.schemas.user_schema import UserSchema, UserUpdateSchema

user_schema = UserSchema()
users_schema = UserSchema(many=True)
user_update_schema = UserUpdateSchema()

@users_bp.route('/', methods=['POST'])
def create_user():
    """Create user with validation."""
    try:
        # Validate and deserialize
        data = user_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    user = User(**data)
    db.session.add(user)
    db.session.commit()

    # Serialize response
    return user_schema.dump(user), 201

@users_bp.route('/', methods=['GET'])
def list_users():
    """List users with serialization."""
    users = User.query.all()
    return jsonify(users_schema.dump(users))
```

### Pydantic Validation

```python
# app/schemas/user_schema_pydantic.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    """User creation schema."""

    email: EmailStr
    name: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=8)

    @validator('password')
    def password_complexity(cls, v):
        """Validate password complexity."""
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

class UserUpdate(BaseModel):
    """User update schema."""

    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=2, max_length=80)

class UserResponse(BaseModel):
    """User response schema."""

    id: int
    email: str
    name: str
    created_at: datetime

    class Config:
        orm_mode = True

# Usage
from pydantic import ValidationError

@users_bp.route('/', methods=['POST'])
def create_user():
    """Create user with Pydantic validation."""
    try:
        user_data = UserCreate(**request.get_json())
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    user = User(
        email=user_data.email,
        name=user_data.name
    )
    user.set_password(user_data.password)

    db.session.add(user)
    db.session.commit()

    return UserResponse.from_orm(user).dict(), 201
```

## SQLAlchemy Integration

### Models with Flask-SQLAlchemy

```python
# app/models/user.py
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class User(db.Model):
    """User model."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<User {self.email}>'

# app/models/post.py
class Post(db.Model):
    """Post model."""

    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'user_id': self.user_id,
            'author': self.author.name,
            'created_at': self.created_at.isoformat()
        }

# Database operations
@users_bp.route('/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    """Get user posts with pagination."""
    user = User.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)

    posts = user.posts.paginate(page=page, per_page=20)

    return jsonify({
        'posts': [p.to_dict() for p in posts.items],
        'total': posts.total,
        'page': posts.page
    })
```

### Database Migrations

```bash
# Initialize migrations
flask db init

# Create migration
flask db migrate -m "Create users table"

# Apply migration
flask db upgrade

# Rollback
flask db downgrade
```

```python
# migrations/versions/xxx_create_users.py (auto-generated)
def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
```

## Authentication

### Flask-Login Session-Based Auth

```python
# app/extensions.py
from flask_login import LoginManager

login_manager = LoginManager()

# app/__init__.py
def create_app():
    app = Flask(__name__)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    return app

# app/models/user.py
from flask_login import UserMixin

class User(UserMixin, db.Model):
    # ... existing fields ...

    def get_id(self):
        return str(self.id)

# app/routes/auth.py
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login."""
    data = request.get_json()

    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({"error": "Invalid credentials"}), 401

    login_user(user, remember=data.get('remember', False))
    return jsonify(user.to_dict())

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """User logout."""
    logout_user()
    return jsonify({"message": "Logged out successfully"})

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current authenticated user."""
    return jsonify(current_user.to_dict())
```

### JWT Authentication

```python
# app/extensions.py
from flask_jwt_extended import JWTManager

jwt = JWTManager()

# app/__init__.py
def create_app():
    app = Flask(__name__)
    app.config['JWT_SECRET_KEY'] = 'super-secret-key'
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

    jwt.init_app(app)

    return app

# app/routes/auth.py
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login and return JWT tokens."""
    data = request.get_json()

    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    })

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)

    return jsonify({"access_token": access_token})

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user from JWT."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)

    return jsonify(user.to_dict())

# Protected route example
@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete user (authenticated)."""
    current_user_id = get_jwt_identity()

    # Authorization check
    if current_user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()

    return '', 204
```

## Configuration Management

### Environment-Based Configuration

```python
# app/config.py
import os
from datetime import timedelta

class Config:
    """Base configuration."""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # Pagination
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

    # Strict security requirements
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

    # Production database (PostgreSQL recommended)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

    @classmethod
    def init_app(cls, app):
        """Production-specific initialization."""
        # Log to syslog or external service
        import logging
        from logging.handlers import SysLogHandler

        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

# Configuration factory
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(env_name='default'):
    """Get configuration by environment name."""
    return config_by_name.get(env_name, DevelopmentConfig)

# app/__init__.py
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    return app
```

### .env File Support

```bash
# .env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
DATABASE_URL=postgresql://user:password@localhost/dbname
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

```python
# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# app/__init__.py
import os
from dotenv import load_dotenv

def create_app():
    load_dotenv()

    config_name = os.getenv('FLASK_ENV', 'development')
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    return app
```

## Error Handling and Logging

### Global Error Handlers

```python
# app/errors/handlers.py
from flask import jsonify
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError

def register_error_handlers(app):
    """Register global error handlers."""

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found"
        }), 404

    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({
            "error": "Bad Request",
            "message": str(error.description) if hasattr(error, 'description') else "Invalid request"
        }), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication required"
        }), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({
            "error": "Forbidden",
            "message": "You don't have permission to access this resource"
        }), 403

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal server error: {error}')
        db.session.rollback()
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }), 500

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle all HTTP exceptions."""
        return jsonify({
            "error": error.name,
            "message": error.description
        }), error.code

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        """Handle database errors."""
        app.logger.error(f'Database error: {error}')
        db.session.rollback()
        return jsonify({
            "error": "Database Error",
            "message": "A database error occurred"
        }), 500

# app/__init__.py
def create_app():
    app = Flask(__name__)

    from app.errors.handlers import register_error_handlers
    register_error_handlers(app)

    return app
```

### Logging Configuration

```python
# app/logging_config.py
import logging
from logging.handlers import RotatingFileHandler
import os

def configure_logging(app):
    """Configure application logging."""

    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # File handler with rotation
        file_handler = RotatingFileHandler(
            'logs/flask_app.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Flask application startup')

# app/__init__.py
def create_app():
    app = Flask(__name__)

    from app.logging_config import configure_logging
    configure_logging(app)

    return app

# Usage in routes
@users_bp.route('/', methods=['POST'])
def create_user():
    current_app.logger.info(f'Creating new user: {request.get_json()}')
    # ... create user ...
    current_app.logger.info(f'User created successfully: {user.id}')
```

## Testing with pytest

### Test Configuration

```python
# conftest.py
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User

@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app('testing')

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Flask CLI test runner."""
    return app.test_cli_runner()

@pytest.fixture
def db_session(app):
    """Database session for testing."""
    with app.app_context():
        db.session.begin_nested()
        yield db.session
        db.session.rollback()

@pytest.fixture
def sample_user(db_session):
    """Create sample user."""
    user = User(email='test@example.com', name='Test User')
    user.set_password('password123')
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def auth_headers(client, sample_user):
    """Get JWT authentication headers."""
    response = client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}
```

### API Testing

```python
# tests/test_users.py
import pytest
from app.models.user import User

def test_create_user(client):
    """Test user creation endpoint."""
    response = client.post('/api/users', json={
        'email': 'new@example.com',
        'name': 'New User',
        'password': 'password123'
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['email'] == 'new@example.com'
    assert data['name'] == 'New User'
    assert 'id' in data

def test_get_user(client, sample_user):
    """Test get user endpoint."""
    response = client.get(f'/api/users/{sample_user.id}')

    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == sample_user.id
    assert data['email'] == sample_user.email

def test_list_users(client, sample_user):
    """Test list users endpoint."""
    response = client.get('/api/users')

    assert response.status_code == 200
    data = response.get_json()
    assert 'users' in data
    assert len(data['users']) > 0

def test_update_user(client, sample_user, auth_headers):
    """Test user update endpoint."""
    response = client.put(
        f'/api/users/{sample_user.id}',
        json={'name': 'Updated Name'},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == 'Updated Name'

def test_delete_user(client, sample_user, auth_headers):
    """Test user deletion endpoint."""
    response = client.delete(
        f'/api/users/{sample_user.id}',
        headers=auth_headers
    )

    assert response.status_code == 204
    assert User.query.get(sample_user.id) is None

def test_authentication_required(client, sample_user):
    """Test that protected endpoints require authentication."""
    response = client.delete(f'/api/users/{sample_user.id}')
    assert response.status_code == 401
```

## Deployment

### Production with Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn --workers 4 --bind 0.0.0.0:8000 "app:create_app()"

# With environment variable
gunicorn --workers 4 --bind 0.0.0.0:8000 --env FLASK_ENV=production "app:create_app()"
```

**gunicorn.conf.py:**
```python
import multiprocessing

# Server socket
bind = '0.0.0.0:8000'
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = 'logs/access.log'
errorlog = 'logs/error.log'
loglevel = 'info'

# Process naming
proc_name = 'flask-app'

# Server mechanics
daemon = False
pidfile = 'gunicorn.pid'
```

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 flask && chown -R flask:flask /app
USER flask

# Run with Gunicorn
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:create_app()"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/flask_db
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=flask_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

## Microservices Patterns

### Service Communication

```python
# app/services/external_api.py
import requests
from flask import current_app

class ExternalAPIService:
    """External API client service."""

    def __init__(self, base_url, timeout=10):
        self.base_url = base_url
        self.timeout = timeout

    def get(self, endpoint, **kwargs):
        """GET request to external API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            current_app.logger.error(f'External API error: {e}')
            raise

    def post(self, endpoint, data, **kwargs):
        """POST request to external API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.post(url, json=data, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            current_app.logger.error(f'External API error: {e}')
            raise

# Usage
api_service = ExternalAPIService('https://api.example.com')

@app.route('/proxy/data')
def proxy_data():
    """Proxy request to external service."""
    try:
        data = api_service.get('data')
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": "External service unavailable"}), 503
```

### Health Checks

```python
# app/routes/health.py
from flask import Blueprint, jsonify
from app.extensions import db
from sqlalchemy import text

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """Basic health check."""
    return jsonify({"status": "healthy"}), 200

@health_bp.route('/health/ready')
def readiness_check():
    """Readiness check with dependencies."""
    checks = {
        "database": False,
        "status": "unhealthy"
    }

    # Check database
    try:
        db.session.execute(text('SELECT 1'))
        checks["database"] = True
    except Exception as e:
        current_app.logger.error(f'Database health check failed: {e}')

    # Overall status
    checks["status"] = "healthy" if all([checks["database"]]) else "unhealthy"

    status_code = 200 if checks["status"] == "healthy" else 503
    return jsonify(checks), status_code
```

## Best Practices

### 1. Use Application Factory Pattern
```python
# ✅ GOOD: Application factory
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    return app

# ❌ BAD: Global app instance
app = Flask(__name__)
```

### 2. Use Blueprints for Modularity
```python
# ✅ GOOD: Organized blueprints
from app.routes.users import users_bp
from app.routes.products import products_bp

app.register_blueprint(users_bp, url_prefix='/api/users')
app.register_blueprint(products_bp, url_prefix='/api/products')

# ❌ BAD: All routes in single file
```

### 3. Validate All Input
```python
# ✅ GOOD: Validation with Marshmallow/Pydantic
try:
    data = user_schema.load(request.get_json())
except ValidationError as e:
    return jsonify({"errors": e.messages}), 400

# ❌ BAD: No validation
data = request.get_json()
user = User(**data)  # Unsafe!
```

### 4. Use Environment Variables for Secrets
```python
# ✅ GOOD: Environment variables
SECRET_KEY = os.getenv('SECRET_KEY')

# ❌ BAD: Hardcoded secrets
SECRET_KEY = 'hardcoded-secret-key'
```

### 5. Implement Proper Error Handling
```python
# ✅ GOOD: Global error handlers
@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f'Error: {error}')
    return jsonify({"error": "Internal server error"}), 500

# ❌ BAD: Unhandled exceptions
```

## Resources

- **Official Documentation**: https://flask.palletsprojects.com/
- **Flask-RESTful**: https://flask-restful.readthedocs.io/
- **Flask-SQLAlchemy**: https://flask-sqlalchemy.palletsprojects.com/
- **Flask-JWT-Extended**: https://flask-jwt-extended.readthedocs.io/
- **Marshmallow**: https://marshmallow.readthedocs.io/
- **Pydantic**: https://pydantic-docs.helpmanual.io/

## Related Skills

When using Flask, consider these complementary skills:

- **pytest**: Testing Flask applications with fixtures and test client
- **sqlalchemy**: Database ORM patterns with Flask-SQLAlchemy integration
- **fastapi-local-dev**: Modern async alternative for high-performance APIs
- **django**: Batteries-included framework with built-in admin and ORM

### Quick Flask Testing Patterns (Inlined for Standalone Use)

```python
# Testing Flask with pytest
import pytest
from flask import Flask
from app import create_app, db

@pytest.fixture
def app():
    """Create and configure test app"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Test client for making requests"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """CLI test runner"""
    return app.test_cli_runner()

# Test routes
def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Welcome' in response.data

def test_api_endpoint(client):
    response = client.post('/api/users', json={
        'username': 'alice',
        'email': 'alice@example.com'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['username'] == 'alice'

def test_authentication(client):
    # Login
    response = client.post('/login', data={
        'username': 'alice',
        'password': 'secret123'
    })
    assert response.status_code == 302  # Redirect after login

    # Access protected route
    response = client.get('/dashboard')
    assert response.status_code == 200

# Test with database
def test_user_creation(app):
    with app.app_context():
        user = User(username='bob', email='bob@example.com')
        db.session.add(user)
        db.session.commit()

        found = User.query.filter_by(username='bob').first()
        assert found is not None
        assert found.email == 'bob@example.com'

# Test error handling
def test_404_error(client):
    response = client.get('/nonexistent')
    assert response.status_code == 404
    assert b'Not Found' in response.data
```

### Quick SQLAlchemy Integration (Inlined for Standalone Use)

```python
# Flask-SQLAlchemy setup
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app

# Define models
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    posts = db.relationship('Post', backref='author', lazy='dynamic')

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

# Query patterns
@app.route('/users/<int:user_id>')
def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'posts': [{'title': p.title} for p in user.posts]
    })

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    user = User(username=data['username'], email=data['email'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'id': user.id}), 201

# Transaction handling
from sqlalchemy.exc import IntegrityError

@app.route('/transfer', methods=['POST'])
def transfer_funds():
    try:
        # All operations in single transaction
        sender = User.query.get_or_404(request.json['sender_id'])
        receiver = User.query.get_or_404(request.json['receiver_id'])
        amount = request.json['amount']

        sender.balance -= amount
        receiver.balance += amount

        db.session.commit()
        return jsonify({'status': 'success'})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Transaction failed'}), 400
```

### Quick FastAPI Comparison (Inlined for Standalone Use)

**When to Choose FastAPI over Flask:**
- Need async/await for high concurrency
- Want automatic API documentation (OpenAPI/Swagger)
- Require built-in data validation (Pydantic)
- Building modern microservices or GraphQL APIs
- Need WebSocket or Server-Sent Events support

**When to Stick with Flask:**
- Building traditional server-rendered web apps
- Existing large Flask codebase
- Need mature ecosystem and extensive plugins
- Team familiar with synchronous Python patterns
- Simpler deployment (no async runtime complexity)

**Migration Considerations:**
```python
# Flask pattern
@app.route('/users/<int:user_id>')
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({'id': user.id, 'name': user.name})

# FastAPI equivalent
@app.get('/users/{user_id}', response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

[Full pytest, SQLAlchemy, and FastAPI patterns available in respective skills if deployed together]
