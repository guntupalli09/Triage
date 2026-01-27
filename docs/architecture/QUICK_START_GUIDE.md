# Quick Start Guide: Enterprise Upgrade Implementation

This guide provides step-by-step instructions for implementing the most critical Phase 1 features.

---

## Step 1: Database Setup (Week 1)

### 1.1 Install PostgreSQL

```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt-get install postgresql-15

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### 1.2 Create Database

```bash
# Connect to PostgreSQL
psql postgres

# Create database and user
CREATE DATABASE triage_ai;
CREATE USER triage_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE triage_ai TO triage_user;
\q
```

### 1.3 Install Python Dependencies

Add to `requirements.txt`:
```txt
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
redis==5.0.1
boto3==1.29.7  # For S3 storage
```

Install:
```bash
pip install -r requirements.txt
```

### 1.4 Database Schema

Create `database/models.py`:

```python
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    plan_tier = Column(String(50), default="free")  # free, pro, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    analyses = relationship("Analysis", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    role = Column(String(50), default="member")  # admin, member, viewer
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    analyses = relationship("Analysis", back_populates="user")

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    filename = Column(String(255))
    file_hash = Column(String(64), index=True)  # For deduplication
    file_storage_path = Column(String(500))
    overall_risk = Column(String(20))
    findings_count = Column(JSON)  # {high: 2, medium: 5, low: 1}
    ruleset_version = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    organization = relationship("Organization", back_populates="analyses")
    findings = relationship("Finding", back_populates="analysis", cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False, index=True)
    rule_id = Column(String(50), index=True)
    rule_name = Column(String(255))
    severity = Column(String(20))
    title = Column(Text)
    rationale = Column(Text)
    matched_excerpt = Column(Text)
    start_index = Column(Integer)
    end_index = Column(Integer)
    exact_snippet = Column(Text)
    clause_number = Column(String(50))
    matched_keywords = Column(JSON)
    aliases = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    analysis = relationship("Analysis", back_populates="findings")
```

### 1.5 Database Connection

Create `database/connection.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://triage_user:your_secure_password@localhost/triage_ai"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 1.6 Alembic Setup

```bash
# Initialize Alembic
alembic init alembic

# Edit alembic.ini to set sqlalchemy.url
# Edit alembic/env.py to import Base from database.models
```

Create first migration:
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

---

## Step 2: Authentication System (Week 2)

### 2.1 Password Hashing

Create `auth/password.py`:

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)
```

### 2.2 JWT Tokens

Create `auth/jwt.py`:

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

### 2.3 Authentication Endpoints

Add to `main.py`:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User
from auth.password import hash_password, verify_password
from auth.jwt import create_access_token, verify_token
from pydantic import BaseModel, EmailStr

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    organization_name: str

class UserResponse(BaseModel):
    id: str
    email: str
    organization_id: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and organization."""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization
    from database.models import Organization
    organization = Organization(name=user_data.organization_name)
    db.add(organization)
    db.flush()
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        organization_id=organization.id,
        role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        organization_id=str(user.organization_id),
        role=user.role
    )

@app.post("/api/v1/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        organization_id=str(current_user.organization_id),
        role=current_user.role
    )
```

---

## Step 3: Update Analysis Endpoint (Week 2)

### 3.1 Store Analysis in Database

Update `/upload` endpoint in `main.py`:

```python
from database.models import Analysis, Finding
from database.connection import get_db
import hashlib

@app.post("/upload")
async def upload_contract(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and analyze contract (authenticated)."""
    # ... existing file validation and extraction code ...
    
    # Calculate file hash for deduplication
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    # Check for duplicate analysis
    existing_analysis = db.query(Analysis).filter(
        Analysis.file_hash == file_hash,
        Analysis.organization_id == current_user.organization_id
    ).first()
    
    if existing_analysis:
        # Return existing analysis
        return RedirectResponse(
            url=f"/results/{existing_analysis.id}",
            status_code=303
        )
    
    # Run analysis
    analysis_result = rule_engine.analyze(contract_text)
    
    # Store file in S3 (or local storage for now)
    # file_storage_path = upload_to_s3(file_bytes, filename)
    
    # Create analysis record
    analysis = Analysis(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        filename=file.filename,
        file_hash=file_hash,
        file_storage_path=None,  # Set when S3 is configured
        overall_risk=analysis_result["overall_risk"],
        findings_count=analysis_result["rule_counts"],
        ruleset_version=analysis_result["version"]
    )
    db.add(analysis)
    db.flush()
    
    # Store findings
    for finding in analysis_result["findings"]:
        db_finding = Finding(
            analysis_id=analysis.id,
            rule_id=finding.rule_id,
            rule_name=finding.rule_name,
            severity=finding.severity.value,
            title=finding.title,
            rationale=finding.rationale,
            matched_excerpt=finding.matched_excerpt,
            start_index=finding.start_index,
            end_index=finding.end_index,
            exact_snippet=finding.exact_snippet,
            clause_number=finding.clause_number,
            matched_keywords=finding.matched_keywords,
            aliases=finding.aliases
        )
        db.add(db_finding)
    
    db.commit()
    db.refresh(analysis)
    
    # Get LLM evaluation (if available)
    findings_dict = [
        {
            "rule_id": f.rule_id,
            "rule_name": f.rule_name,
            "title": f.title,
            "severity": f.severity.value,
            "rationale": f.rationale,
            "matched_excerpt": f.matched_excerpt,
            # ... other fields
        }
        for f in analysis_result["findings"]
    ]
    
    llm_result = llm_evaluator.evaluate(
        findings=findings_dict,
        overall_risk=analysis_result["overall_risk"],
        contract_text=None
    )
    
    # Redirect to results
    return RedirectResponse(
        url=f"/results/{analysis.id}",
        status_code=303
    )
```

### 3.2 Analysis History Endpoint

Add to `main.py`:

```python
from fastapi import Query
from typing import Optional

@app.get("/api/v1/analyses")
async def list_analyses(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List analyses for current user's organization."""
    query = db.query(Analysis).filter(
        Analysis.organization_id == current_user.organization_id
    )
    
    if risk_level:
        query = query.filter(Analysis.overall_risk == risk_level)
    
    total = query.count()
    analyses = query.order_by(Analysis.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "analyses": [
            {
                "id": str(a.id),
                "filename": a.filename,
                "overall_risk": a.overall_risk,
                "findings_count": a.findings_count,
                "created_at": a.created_at.isoformat()
            }
            for a in analyses
        ]
    }

@app.get("/api/v1/analyses/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis details."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.organization_id == current_user.organization_id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    findings = db.query(Finding).filter(Finding.analysis_id == analysis.id).all()
    
    return {
        "id": str(analysis.id),
        "filename": analysis.filename,
        "overall_risk": analysis.overall_risk,
        "findings_count": analysis.findings_count,
        "ruleset_version": analysis.ruleset_version,
        "created_at": analysis.created_at.isoformat(),
        "findings": [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity,
                "title": f.title,
                "rationale": f.rationale,
                "matched_excerpt": f.matched_excerpt,
                # ... other fields
            }
            for f in findings
        ]
    }
```

---

## Step 4: Environment Variables

Update `.env` file:

```bash
# Database
DATABASE_URL=postgresql://triage_user:your_secure_password@localhost/triage_ai

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production

# Existing variables
OPENAI_API_KEY=sk-...
STRIPE_SECRET_KEY=sk-...
STRIPE_WEBHOOK_SECRET=whsec_...
BASE_URL=http://localhost:8000
DEV_MODE=true
```

---

## Step 5: Initialize Database

Run on first startup:

```python
# In main.py or a separate script
from database.connection import init_db

if __name__ == "__main__":
    init_db()
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
```

Or run Alembic migrations:
```bash
alembic upgrade head
```

---

## Next Steps

1. **Test authentication**: Register user, login, access protected endpoints
2. **Test analysis storage**: Upload contract, verify it's stored in database
3. **Test analysis history**: List analyses, view analysis details
4. **Add frontend**: Update UI to use new authentication and API endpoints
5. **Add file storage**: Set up S3 or similar for contract file storage

---

## Testing

Create `tests/test_auth.py`:

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register():
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123",
        "organization_name": "Test Org"
    })
    assert response.status_code == 200
    assert "id" in response.json()

def test_login():
    # First register
    client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123",
        "organization_name": "Test Org"
    })
    
    # Then login
    response = client.post("/api/v1/auth/login", data={
        "username": "test@example.com",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

Run tests:
```bash
pytest tests/ -v
```

---

## Common Issues & Solutions

### Issue: Database connection fails
**Solution**: Check DATABASE_URL, ensure PostgreSQL is running, verify user permissions

### Issue: JWT token invalid
**Solution**: Check JWT_SECRET_KEY is set, ensure token hasn't expired

### Issue: Migration errors
**Solution**: Drop database and recreate, or fix migration manually

### Issue: Password hashing errors
**Solution**: Ensure passlib[bcrypt] is installed correctly

---

## Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
