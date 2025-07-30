# Crypto-0DTE-System: AI-Powered BTC/ETH Trading Platform

**Revolutionary AI-powered cryptocurrency trading system for Delta Exchange, designed specifically for Indian crypto traders.**

## 🚀 System Overview

The Crypto-0DTE-System is an autonomous AI trading platform that operates 24/7 in cryptocurrency markets, focusing on Bitcoin (BTC) and Ethereum (ETH) options and perpetual contracts on Delta Exchange. Built with advanced machine learning algorithms, the system continuously learns from market patterns and adapts its strategies for optimal performance.

### Key Features

- **24/7 Autonomous Trading**: Never misses an opportunity in the always-open crypto markets
- **AI-Powered Signal Generation**: Advanced machine learning models for pattern recognition
- **Multi-Strategy Approach**: 5+ specialized trading strategies for different market conditions
- **Delta Exchange Integration**: Deep integration with India's leading crypto derivatives platform
- **Regulatory Compliance**: Built-in compliance with Indian crypto regulations
- **Real-Time Learning**: Continuous improvement through hourly learning cycles

## 📊 Performance Targets

- **Expected Monthly Returns**: 25-40%
- **Win Rate**: 75-80%
- **Daily Trading Frequency**: 25-40 trades across all strategies
- **Maximum Drawdown**: <8% (crypto-adjusted risk management)
- **Sharpe Ratio**: >2.5

## 🏗️ Architecture

### Backend Services
- **Data Ingestion Service**: Real-time market data from Delta Exchange and reference exchanges
- **Signal Generation Service**: AI-powered analysis and strategy execution
- **Execution Service**: Order management and position tracking
- **Learning Service**: Continuous AI model improvement
- **Risk Management Service**: Portfolio-level risk controls

### Frontend Dashboard
- **Real-Time Portfolio View**: Live P&L and position tracking
- **Crypto Analytics**: BTC/ETH correlation, funding rates, sentiment analysis
- **AI Insights**: Learning progress and performance metrics
- **Compliance Dashboard**: Indian regulatory compliance tracking

### Trading Strategies
1. **BTC Lightning Scalp**: High-frequency momentum trading
2. **ETH DeFi Correlation**: ETH trading based on DeFi ecosystem movements
3. **BTC/ETH Cross-Asset Arbitrage**: Correlation breakdown exploitation
4. **Funding Rate Arbitrage**: Perpetual funding rate opportunities
5. **Fear & Greed Contrarian**: Sentiment-based volatility plays

## 🛠️ Technology Stack

### Backend
- **Python 3.11**: Core application language
- **FastAPI**: High-performance API framework
- **PostgreSQL**: Primary database for trading data
- **Redis**: Caching and real-time data
- **InfluxDB**: Time-series market data storage
- **Celery**: Asynchronous task processing

### AI/ML
- **TensorFlow**: Deep learning models
- **scikit-learn**: Traditional ML algorithms
- **pandas/numpy**: Data processing
- **TA-Lib**: Technical analysis indicators

### Frontend
- **React 19**: Modern UI framework
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Recharts**: Financial charting
- **WebSocket**: Real-time data updates

### Infrastructure
- **Docker**: Containerization
- **Kubernetes**: Orchestration (production)
- **AWS**: Cloud infrastructure
- **Terraform**: Infrastructure as code

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Delta Exchange API credentials

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/TKTINC/crypto-0DTE-system.git
cd crypto-0DTE-system
```

2. **Setup environment variables**
```bash
cp .env.example .env
# Edit .env with your Delta Exchange API credentials
```

3. **Start the development environment**
```bash
./scripts/dev-setup.sh
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Production Deployment

```bash
# Deploy to AWS
./scripts/deploy-production.sh

# Deploy locally with Docker
docker-compose -f docker-compose.prod.yml up -d
```

## 📈 Trading Strategies

### 1. BTC Lightning Scalp
**Objective**: Capture short-term momentum moves in BTC
- **Timeframe**: 15-30 minutes
- **Frequency**: 15-25 trades/day
- **Target Profit**: 0.8%
- **Stop Loss**: 0.4%

### 2. ETH DeFi Correlation
**Objective**: Trade ETH based on DeFi ecosystem movements
- **Timeframe**: 1-4 hours
- **Frequency**: 3-5 trades/day
- **Target Profit**: 2.5%
- **Stop Loss**: 1.2%

### 3. BTC/ETH Cross-Asset Arbitrage
**Objective**: Exploit correlation breakdowns between BTC and ETH
- **Timeframe**: 2-6 hours
- **Frequency**: 5-8 trades/day
- **Target Profit**: 1.5%
- **Stop Loss**: 0.8%

### 4. Funding Rate Arbitrage
**Objective**: Capture funding rate inefficiencies
- **Timeframe**: 8 hours (funding periods)
- **Frequency**: 2-3 trades/day
- **Target Profit**: 3.0%
- **Stop Loss**: 1.5%

### 5. Fear & Greed Contrarian
**Objective**: Contrarian trades on sentiment extremes
- **Timeframe**: 1-3 days
- **Frequency**: 1-2 trades/day
- **Target Profit**: 15% (options strategies)
- **Stop Loss**: 8%

## 🔒 Risk Management

### Position Sizing
- **Base Position Size**: 30% of account (vs 40% for traditional markets)
- **Volatility Adjustment**: Dynamic sizing based on BTC/ETH volatility
- **Correlation Limits**: Maximum 60% exposure to correlated positions
- **Maximum Single Position**: 15% of account

### Risk Controls
- **Daily Loss Limit**: 3% of account value
- **Weekly Loss Limit**: 8% of account value
- **Maximum Drawdown**: 15% (emergency stop)
- **Correlation Monitoring**: Real-time cross-asset correlation tracking

## 🇮🇳 Indian Regulatory Compliance

### Tax Compliance
- **Automatic Tax Calculation**: 30% tax on crypto gains
- **TDS Tracking**: 1% TDS on transactions above ₹10,000
- **Tax Report Generation**: Automated quarterly and annual reports

### KYC/AML
- **User Verification**: Integrated KYC verification
- **Transaction Monitoring**: AML compliance monitoring
- **Suspicious Activity Reporting**: Automatic flagging and reporting

### Trading Limits
- **Daily Trading Limit**: ₹10 Lakh (configurable)
- **Monthly Trading Limit**: ₹1 Crore (configurable)
- **Position Limits**: Compliance with SEBI guidelines

## 📊 Monitoring & Analytics

### Performance Metrics
- **Real-Time P&L**: Live profit/loss tracking
- **Win Rate Analysis**: Strategy-specific performance
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Risk monitoring

### AI Learning Metrics
- **Model Accuracy**: Prediction accuracy over time
- **Learning Progress**: AI improvement tracking
- **Pattern Discovery**: New pattern identification
- **Strategy Evolution**: Strategy performance evolution

### Market Analytics
- **BTC/ETH Correlation**: Real-time correlation tracking
- **Funding Rate Monitor**: Cross-exchange funding rates
- **Volatility Analysis**: Market volatility patterns
- **Sentiment Tracking**: Fear & Greed Index monitoring

## 🔧 Configuration

### Environment Variables
```bash
# Delta Exchange API
DELTA_API_KEY=your_api_key
DELTA_API_SECRET=your_api_secret
DELTA_API_PASSPHRASE=your_passphrase

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/crypto_0dte
REDIS_URL=redis://localhost:6379
INFLUXDB_URL=http://localhost:8086

# AI Configuration
OPENAI_API_KEY=your_openai_key
MODEL_UPDATE_FREQUENCY=3600  # 1 hour

# Risk Management
MAX_POSITION_SIZE=0.30
DAILY_LOSS_LIMIT=0.03
CORRELATION_LIMIT=0.60
```

### Strategy Configuration
```yaml
strategies:
  btc_lightning_scalp:
    enabled: true
    position_size: 0.08
    momentum_threshold: 0.005
    volume_confirmation: 1.5
    
  eth_defi_correlation:
    enabled: true
    position_size: 0.10
    correlation_threshold: 0.7
    defi_tokens: ['UNI', 'AAVE', 'COMP', 'MKR']
    
  funding_arbitrage:
    enabled: true
    position_size: 0.12
    funding_threshold: 0.01
```

## 🧪 Testing

### Unit Tests
```bash
# Run backend tests
cd backend && python -m pytest tests/

# Run frontend tests
cd frontend && npm test
```

### Integration Tests
```bash
# Test Delta Exchange integration
python -m pytest tests/integration/test_delta_exchange.py

# Test AI signal generation
python -m pytest tests/integration/test_signal_generation.py
```

### Paper Trading
```bash
# Start paper trading mode
./scripts/start-paper-trading.sh
```

## 📚 Documentation

- [System Architecture](docs/SYSTEM-ARCHITECTURE.md)
- [API Documentation](docs/API-DOCUMENTATION.md)
- [Trading Strategies](docs/TRADING-STRATEGIES.md)
- [Deployment Guide](docs/DEPLOYMENT-GUIDE.md)
- [User Manual](docs/USER-MANUAL.md)
- [Developer Guide](docs/DEVELOPER-GUIDE.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**Important**: Cryptocurrency trading involves substantial risk and may not be suitable for all investors. Past performance is not indicative of future results. This software is provided for educational and research purposes. Users should conduct their own research and consult with financial advisors before making investment decisions.

## 🆘 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/TKTINC/crypto-0DTE-system/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TKTINC/crypto-0DTE-system/discussions)
- **Email**: support@tktinc.com

## 🏆 Acknowledgments

- Delta Exchange for providing robust crypto derivatives infrastructure
- The Indian crypto community for driving innovation
- Open source contributors who made this project possible

---

**Built with ❤️ for the Indian crypto trading community**

