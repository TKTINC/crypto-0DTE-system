# Local Testing Guide
## Crypto-0DTE System Pre-Deployment Validation

### 🎯 **TESTING OBJECTIVES**

Before deploying to Railway, we must verify:
1. Application starts without errors
2. All dependencies are properly installed
3. Database connections work
4. API endpoints respond correctly
5. Health checks pass
6. Environment variables are properly configured

### 🔧 **PREREQUISITES**

#### **System Requirements**
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Git

#### **Install Dependencies**
```bash
# Clone repository
git clone https://github.com/TKTINC/crypto-0DTE-system.git
cd crypto-0DTE-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
cd backend
pip install -r requirements.txt
```

### 🗄️ **DATABASE SETUP**

#### **PostgreSQL Setup**
```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE crypto_0dte_local;
CREATE USER crypto_user WITH PASSWORD 'crypto_password';
GRANT ALL PRIVILEGES ON DATABASE crypto_0dte_local TO crypto_user;
\q
```

#### **Redis Setup**
```bash
# Install Redis (Ubuntu/Debian)
sudo apt install redis-server

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis connection
redis-cli ping
# Should return: PONG
```

### 🔐 **ENVIRONMENT CONFIGURATION**

#### **Create Local Environment File**
Create `backend/.env.local`:
```bash
# Database Configuration
DATABASE_URL=postgresql://crypto_user:crypto_password@localhost:5432/crypto_0dte_local

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
ENVIRONMENT=development
DEBUG=true
JWT_SECRET_KEY=local-development-secret-key-for-testing-only
API_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Delta Exchange Configuration (Testnet)
DELTA_EXCHANGE_API_KEY=your-testnet-api-key
DELTA_EXCHANGE_API_SECRET=your-testnet-api-secret
DELTA_EXCHANGE_BASE_URL=https://testnet-api.delta.exchange
DELTA_EXCHANGE_TESTNET=true

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_BASE=https://api.openai.com/v1

# Logging Configuration
LOG_LEVEL=DEBUG
```

#### **Load Environment Variables**
```bash
# Install python-dotenv if not already installed
pip install python-dotenv

# Create script to load environment
cat > load_env.py << 'EOF'
import os
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv('.env.local')

# Verify critical variables are loaded
required_vars = [
    'DATABASE_URL',
    'REDIS_URL',
    'JWT_SECRET_KEY'
]

for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {'*' * len(value[:10])}...")
    else:
        print(f"❌ {var}: NOT SET")
EOF

python load_env.py
```

### 🗃️ **DATABASE MIGRATIONS**

#### **Initialize Alembic**
```bash
# Navigate to backend directory
cd backend

# Initialize Alembic (if not already done)
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

#### **Verify Database Tables**
```bash
# Connect to database and check tables
psql postgresql://crypto_user:crypto_password@localhost:5432/crypto_0dte_local

# List tables
\dt

# Should see tables like: users, portfolios, signals, etc.
\q
```

### 🚀 **APPLICATION TESTING**

#### **Test 1: Basic Application Startup**
```bash
# Navigate to backend directory
cd backend

# Start the application
python -m app.main

# Expected output:
# INFO:     Started server process [PID]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### **Test 2: Health Check Endpoints**
Open new terminal and test endpoints:
```bash
# Basic health check
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"crypto-0dte-system"}

# Detailed health check
curl http://localhost:8000/health/detailed
# Expected: Detailed health status with all checks

# Readiness check
curl http://localhost:8000/health/ready
# Expected: {"status":"ready"}

# Liveness check
curl http://localhost:8000/health/live
# Expected: {"status":"alive"}
```

#### **Test 3: API Documentation**
```bash
# Open API documentation in browser
open http://localhost:8000/docs

# Or test with curl
curl http://localhost:8000/openapi.json
```

#### **Test 4: Database Connectivity**
```bash
# Test database connection through API
curl http://localhost:8000/health/detailed | jq '.checks.database'
# Expected: {"status":"healthy","message":"Database connection successful"}
```

#### **Test 5: Redis Connectivity**
```bash
# Test Redis connection through API
curl http://localhost:8000/health/detailed | jq '.checks.redis'
# Expected: {"status":"healthy","message":"Redis connection successful"}
```

### 🧪 **COMPREHENSIVE TESTING SCRIPT**

Create `test_local_deployment.py`:
```python
#!/usr/bin/env python3
"""
Local deployment testing script for Crypto-0DTE System
"""

import requests
import json
import time
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint: str, expected_status: int = 200) -> Dict[str, Any]:
    """Test a single endpoint"""
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        success = response.status_code == expected_status
        
        return {
            "endpoint": endpoint,
            "status_code": response.status_code,
            "expected": expected_status,
            "success": success,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
            "response_time": response.elapsed.total_seconds()
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "success": False,
            "error": str(e)
        }

def main():
    """Run comprehensive local testing"""
    print("🧪 Starting Crypto-0DTE System Local Testing")
    print("=" * 50)
    
    # Wait for application to start
    print("⏳ Waiting for application to start...")
    time.sleep(5)
    
    # Test endpoints
    endpoints = [
        "/health",
        "/health/detailed", 
        "/health/ready",
        "/health/live",
        "/info",
        "/docs",
        "/openapi.json"
    ]
    
    results = []
    for endpoint in endpoints:
        print(f"Testing {endpoint}...")
        result = test_endpoint(endpoint)
        results.append(result)
        
        if result["success"]:
            print(f"✅ {endpoint} - OK ({result.get('response_time', 0):.2f}s)")
        else:
            print(f"❌ {endpoint} - FAILED")
            if "error" in result:
                print(f"   Error: {result['error']}")
            else:
                print(f"   Status: {result['status_code']} (expected {result['expected']})")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Ready for Railway deployment!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Fix issues before deployment")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

#### **Run Comprehensive Tests**
```bash
# Install requests if not already installed
pip install requests

# Run the test script
python test_local_deployment.py
```

### 🔍 **TROUBLESHOOTING COMMON ISSUES**

#### **Issue 1: Import Errors**
```bash
# Error: ModuleNotFoundError: No module named 'app.xxx'
# Solution: Check PYTHONPATH and ensure you're in the correct directory

export PYTHONPATH="${PYTHONPATH}:$(pwd)"
cd backend
python -m app.main
```

#### **Issue 2: Database Connection Failed**
```bash
# Error: could not connect to server
# Solution: Check PostgreSQL is running and credentials are correct

sudo systemctl status postgresql
psql postgresql://crypto_user:crypto_password@localhost:5432/crypto_0dte_local
```

#### **Issue 3: Redis Connection Failed**
```bash
# Error: Redis connection failed
# Solution: Check Redis is running

sudo systemctl status redis-server
redis-cli ping
```

#### **Issue 4: Port Already in Use**
```bash
# Error: [Errno 98] Address already in use
# Solution: Kill existing process or use different port

lsof -i :8000
kill -9 <PID>

# Or change port in main.py
```

#### **Issue 5: Environment Variables Not Loaded**
```bash
# Error: Environment variable not found
# Solution: Ensure .env.local is in correct location and properly formatted

ls -la .env.local
cat .env.local | grep -v "^#" | grep "="
```

### ✅ **PRE-DEPLOYMENT CHECKLIST**

Before proceeding to Railway deployment:

- [ ] Application starts without errors
- [ ] All health check endpoints return 200
- [ ] Database connection successful
- [ ] Redis connection successful
- [ ] API documentation accessible
- [ ] No import errors in logs
- [ ] Environment variables properly loaded
- [ ] Database migrations applied successfully
- [ ] All tests pass with 100% success rate

### 🚀 **NEXT STEPS**

Once all local tests pass:

1. **Commit any fixes** to your repository
2. **Create Railway project** and add database services
3. **Configure environment variables** in Railway
4. **Deploy to Railway** using git push or CLI
5. **Monitor deployment logs** for any issues
6. **Test deployed application** using Railway domain

### 📞 **SUPPORT**

If you encounter issues during local testing:

1. Check application logs for detailed error messages
2. Verify all dependencies are installed correctly
3. Ensure database and Redis services are running
4. Validate environment variable configuration
5. Test individual components in isolation

Remember: **Local testing success is critical for Railway deployment success!**

