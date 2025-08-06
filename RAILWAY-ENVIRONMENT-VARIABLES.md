# Railway Environment Variables Configuration
## Crypto-0DTE System Deployment

### 🔧 **REQUIRED ENVIRONMENT VARIABLES**

Configure these variables in your Railway project settings:

#### **Database Configuration**
```bash
# Railway will provide this automatically when you add PostgreSQL service
DATABASE_URL=postgresql://username:password@host:port/database_name
```

#### **Redis Configuration**
```bash
# Railway will provide this automatically when you add Redis service
REDIS_URL=redis://username:password@host:port/database_number
```

#### **Application Configuration**
```bash
# Environment setting
ENVIRONMENT=production

# JWT Secret Key (generate a secure 32+ character string)
JWT_SECRET_KEY=your-super-secure-jwt-secret-key-here-32-chars-minimum

# CORS Origins (your frontend domain)
API_CORS_ORIGINS=https://your-frontend-domain.com

# Allowed hosts for production
ALLOWED_HOSTS=your-backend-domain.railway.app,localhost
```

#### **Delta Exchange API Configuration**
```bash
# Delta Exchange API credentials
DELTA_EXCHANGE_API_KEY=your-delta-exchange-api-key
DELTA_EXCHANGE_API_SECRET=your-delta-exchange-api-secret
DELTA_EXCHANGE_BASE_URL=https://api.delta.exchange

# Trading configuration
DELTA_EXCHANGE_TESTNET=false
```

#### **OpenAI API Configuration**
```bash
# OpenAI API for AI trading signals
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_BASE=https://api.openai.com/v1
```

#### **InfluxDB Configuration (Optional)**
```bash
# InfluxDB for time-series data storage
INFLUXDB_URL=your-influxdb-url
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=your-influxdb-org
INFLUXDB_BUCKET=crypto-0dte-data
```

#### **Logging Configuration**
```bash
# Logging level
LOG_LEVEL=INFO

# Sentry for error tracking (optional)
SENTRY_DSN=your-sentry-dsn-url
```

### 🚂 **RAILWAY-SPECIFIC VARIABLES**

Railway automatically provides these variables:

```bash
# Railway automatically sets these
PORT=8000                           # Dynamic port assignment
RAILWAY_ENVIRONMENT=production      # Environment name
RAILWAY_PROJECT_ID=your-project-id  # Project identifier
RAILWAY_SERVICE_ID=your-service-id  # Service identifier
RAILWAY_PUBLIC_DOMAIN=your-app.railway.app  # Public domain
RAILWAY_PRIVATE_DOMAIN=your-app.railway.internal  # Private domain
```

### 📋 **RAILWAY SETUP STEPS**

#### **1. Create Railway Project**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init
```

#### **2. Add Database Services**
In Railway dashboard:
1. Click "Add Service"
2. Select "PostgreSQL" 
3. Click "Add Service" again
4. Select "Redis"

#### **3. Configure Environment Variables**
In Railway dashboard:
1. Go to your service
2. Click "Variables" tab
3. Add all required variables from the list above

#### **4. Deploy Application**
```bash
# Deploy from CLI
railway up

# Or connect GitHub repository in Railway dashboard
```

### 🔐 **SECURITY BEST PRACTICES**

#### **JWT Secret Key Generation**
```bash
# Generate secure JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### **API Key Security**
- Never commit API keys to version control
- Use Railway's "Sealed Variables" for sensitive data
- Rotate API keys regularly
- Monitor API key usage

#### **Database Security**
- Use Railway's managed PostgreSQL (automatic backups)
- Enable SSL connections
- Restrict database access to Railway services only

### 🧪 **TESTING CONFIGURATION**

#### **Local Development**
Create `.env.local` file (not committed to git):
```bash
DATABASE_URL=postgresql://localhost:5432/crypto_0dte_local
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=local-development-secret-key
ENVIRONMENT=development
API_CORS_ORIGINS=http://localhost:3000
DELTA_EXCHANGE_TESTNET=true
```

#### **Staging Environment**
Configure staging variables in Railway:
```bash
ENVIRONMENT=staging
DELTA_EXCHANGE_TESTNET=true
LOG_LEVEL=DEBUG
```

### 📊 **MONITORING VARIABLES**

#### **Health Check Configuration**
```bash
# Health check settings (optional)
HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=60
```

#### **Performance Monitoring**
```bash
# APM configuration (optional)
NEW_RELIC_LICENSE_KEY=your-new-relic-key
DATADOG_API_KEY=your-datadog-key
```

### 🚀 **DEPLOYMENT CHECKLIST**

Before deploying to Railway:

- [ ] All required environment variables configured
- [ ] Database service added to Railway project
- [ ] Redis service added to Railway project
- [ ] JWT secret key generated and set
- [ ] Delta Exchange API keys configured
- [ ] OpenAI API key configured
- [ ] CORS origins set to frontend domain
- [ ] Health check endpoint tested
- [ ] Database migrations prepared

### 🔧 **TROUBLESHOOTING**

#### **Common Issues**

1. **Database Connection Failed**
   - Check DATABASE_URL format
   - Ensure PostgreSQL service is running
   - Verify network connectivity

2. **JWT Authentication Failed**
   - Check JWT_SECRET_KEY is set
   - Ensure key is 32+ characters
   - Verify key matches across services

3. **CORS Errors**
   - Check API_CORS_ORIGINS includes frontend domain
   - Verify protocol (http/https) matches
   - Ensure no trailing slashes

4. **Health Check Failed**
   - Check /health endpoint is accessible
   - Verify all dependencies are healthy
   - Check application logs for errors

### 📞 **SUPPORT**

For Railway-specific issues:
- Railway Documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Railway Support: support@railway.app

