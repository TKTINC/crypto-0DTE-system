# 🚀 **Crypto-0DTE System - Deployment Guide**

## 📋 **Quick Start**

### **1. Environment Setup (One-Time)**
```bash
# Clone and enter the repository
git clone https://github.com/TKTINC/crypto-0DTE-system.git
cd crypto-0DTE-system

# Set up environment variables (interactive setup)
./setup-environment.sh
```

### **2. Deploy the System**
```bash
# Deploy the complete system
./deploy-v2-macos.sh
```

### **3. Emergency Cleanup (If Needed)**
```bash
# Stop all services and clean up
./emergency-cleanup.sh
```

## 🔧 **Detailed Setup Instructions**

### **Prerequisites**
- **macOS** (for deploy-v2-macos.sh)
- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL** (will be installed if needed)
- **Redis** (will be installed if needed)

### **API Keys Required**
- **Delta Exchange Testnet API Key** (required for paper trading)
- **Delta Exchange Testnet API Secret** (required for paper trading)
- **OpenAI API Key** (optional, for AI features)

## 📁 **Project Structure**

### **Essential Files:**
```
crypto-0DTE-system/
├── deploy-v2-macos.sh          # Main deployment script
├── deploy-utils.sh             # Deployment utilities
├── emergency-cleanup.sh        # Emergency system cleanup
├── setup-environment.sh       # Unified environment setup
├── monitor-autonomous-trading.sh # System monitoring
├── README.md                   # Main documentation
├── DEPLOYMENT-GUIDE.md         # This file
├── CLAUDE-PROJECT-BRIEF.md     # Project specifications
├── .env.example               # Environment template
├── config/                    # Configuration directory
│   └── api-keys.conf         # API keys configuration
├── backend/                   # Backend application
├── frontend/                  # Frontend application
└── logs/                     # Log files (runtime)
```

### **Archive Directory:**
- `archive/redundant-scripts/` - Old/redundant scripts (kept for reference)
- `archive/old-docs/` - Outdated documentation (kept for reference)

## 🎯 **Environment Setup Details**

### **setup-environment.sh Features:**
- ✅ **Interactive setup** with current value detection
- ✅ **Shell profile integration** (bash/zsh auto-detection)
- ✅ **Configuration file management** (config/api-keys.conf)
- ✅ **Backend environment generation** (backend/.env.local)
- ✅ **Validation and error checking**
- ✅ **Secure API key input** (hidden from terminal)

### **Configuration Files Created:**
1. **Shell Profile** (`~/.bashrc`, `~/.zshrc`, etc.)
   - Permanent environment variables
   - Available in all terminal sessions

2. **Config File** (`config/api-keys.conf`)
   - Persistent API key storage
   - Not committed to git
   - Easy to edit manually

3. **Backend Environment** (`backend/.env.local`)
   - Backend-specific configuration
   - Generated from config file
   - Used by the application

## 🚀 **Deployment Process**

### **deploy-v2-macos.sh Workflow:**
1. **Environment Validation** - Checks system requirements
2. **Dependency Installation** - Python packages, Node modules
3. **Database Setup** - PostgreSQL, Redis, migrations
4. **Service Startup** - Backend API, Frontend dev server
5. **Health Checks** - Validates all services are running
6. **Error Handling** - Comprehensive cleanup on failure

### **Service Ports:**
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 🛡️ **Emergency Procedures**

### **If Services Won't Stop:**
```bash
./emergency-cleanup.sh
```

### **If Deployment Fails:**
The deployment script automatically runs cleanup, but you can also:
```bash
./emergency-cleanup.sh
# Fix any issues
./deploy-v2-macos.sh
```

### **Check Environment Configuration:**
```bash
./setup-environment.sh --check
```

## 📊 **Monitoring**

### **System Monitoring:**
```bash
./monitor-autonomous-trading.sh
```

### **Log Files:**
- `logs/backend.log` - Backend application logs
- `logs/frontend.log` - Frontend development server logs
- `logs/deployment.log` - Deployment process logs

### **Health Checks:**
- Backend API: http://localhost:8000/health
- Frontend: http://localhost:3000

## 🔄 **Common Workflows**

### **First Time Setup:**
```bash
git clone https://github.com/TKTINC/crypto-0DTE-system.git
cd crypto-0DTE-system
./setup-environment.sh
./deploy-v2-macos.sh
```

### **Regular Development:**
```bash
# Pull latest changes
git pull origin main

# Deploy (environment already configured)
./deploy-v2-macos.sh
```

### **Update API Keys:**
```bash
# Interactive update
./setup-environment.sh

# Or edit directly
nano config/api-keys.conf
```

### **Clean Restart:**
```bash
./emergency-cleanup.sh
./deploy-v2-macos.sh
```

## 🎯 **Trading Modes**

### **Paper Trading (Default):**
- Uses Delta Exchange testnet
- No real money involved
- Full system functionality
- Safe for testing and development

### **Live Trading (Advanced):**
- Requires live Delta Exchange API keys
- Real money trading
- Set up via `./setup-environment.sh`
- Change `ENVIRONMENT=live` in backend/.env.local

## 🔧 **Troubleshooting**

### **Common Issues:**

1. **Port Already in Use:**
   ```bash
   ./emergency-cleanup.sh
   ```

2. **API Key Errors:**
   ```bash
   ./setup-environment.sh --check
   ./setup-environment.sh  # Re-run setup
   ```

3. **Database Connection Issues:**
   ```bash
   brew services restart postgresql@15
   ./deploy-v2-macos.sh
   ```

4. **Background Processes Running:**
   ```bash
   ./emergency-cleanup.sh
   ```

### **Getting Help:**
- Check logs in `logs/` directory
- Run `./setup-environment.sh --check` for configuration status
- Use `./emergency-cleanup.sh` to reset system state

## 🎉 **Success Indicators**

### **Successful Deployment:**
```
✅ Risk Manager initialized
✅ Position Manager initialized  
✅ Trade Execution Engine initialized
✅ Autonomous Trading Orchestrator initialized
🚀 Autonomous Trading System ACTIVE
```

### **System URLs:**
- **Trading Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

**For additional help, see README.md or CLAUDE-PROJECT-BRIEF.md**

