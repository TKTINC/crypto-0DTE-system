// API Service for Crypto-0DTE System
// Handles all communication with the backend

const API_BASE_URL = 'http://localhost:8000';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  // Generic API call method
  async apiCall(endpoint, options = {}) {
    try {
      const url = `${this.baseURL}${endpoint}`;
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`API call failed: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API call to ${endpoint} failed:`, error);
      throw error;
    }
  }

  // Health and System Status
  async getSystemHealth() {
    return this.apiCall('/health');
  }

  async getSystemStatus() {
    return this.apiCall('/api/v1/system/status');
  }

  // Market Data
  async getMarketData(symbol = 'BTC-USDT', limit = 100) {
    return this.apiCall(`/api/v1/market-data/recent?symbol=${symbol}&limit=${limit}`);
  }

  async getLiveMarketData(symbol = 'BTC-USDT') {
    return this.apiCall(`/api/v1/market-data/live/${symbol}`);
  }

  async getOHLCVData(symbol = 'BTC-USDT', timeframe = '1h', limit = 24) {
    return this.apiCall(`/api/v1/market-data/ohlcv?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`);
  }

  // AI Signals
  async getRecentSignals(limit = 10) {
    return this.apiCall(`/api/v1/signals/recent?limit=${limit}`);
  }

  async getActiveSignals() {
    return this.apiCall('/api/v1/signals/active');
  }

  async getSignalPerformance() {
    return this.apiCall('/api/v1/signals/performance');
  }

  async generateSignal(symbol, timeframe = '1h') {
    return this.apiCall('/api/v1/signals/generate', {
      method: 'POST',
      body: JSON.stringify({ symbol, timeframe }),
    });
  }

  // Portfolio
  async getPortfolioStatus() {
    return this.apiCall('/api/v1/portfolio/status');
  }

  async getPortfolioSummary() {
    return this.apiCall('/api/v1/portfolio/summary');
  }

  async getPortfolioHistory(days = 7) {
    return this.apiCall(`/api/v1/portfolio/history?days=${days}`);
  }

  // Trading
  async getRecentTrades(limit = 20) {
    return this.apiCall(`/api/v1/trading/recent?limit=${limit}`);
  }

  async getTradingActivity() {
    return this.apiCall('/api/v1/trading/activity');
  }

  async getTradingPerformance() {
    return this.apiCall('/api/v1/trading/performance');
  }

  // Performance Metrics
  async getPerformanceMetrics() {
    return this.apiCall('/api/v1/portfolio/performance');
  }

  async getSystemMetrics() {
    return this.apiCall('/api/v1/monitoring/system-metrics');
  }

  // Connection Testing
  async testDeltaConnection() {
    return this.apiCall('/api/v1/market-data/test-connection');
  }

  async testOpenAIConnection() {
    return this.apiCall('/api/v1/signals/test-ai-connection');
  }

  // Autonomous System Monitoring
  async getAutonomousStatus() {
    return this.apiCall('/api/v1/autonomous/status');
  }

  async getSystemMetrics() {
    return this.apiCall('/api/v1/monitoring/metrics');
  }

  async getConnectionStatus() {
    return this.apiCall('/api/v1/monitoring/connections');
  }

  // API Connection Tests
  async testDeltaConnection() {
    return this.apiCall('/api/v1/market-data/test-connection');
  }

  async testOpenAIConnection() {
    return this.apiCall('/api/v1/signals/test-ai-connection');
  }

  // Real-time data helpers
  async getAllDashboardData() {
    try {
      const [
        systemHealth,
        marketDataBTC,
        marketDataETH,
        recentSignals,
        portfolioStatus,
        recentTrades,
        autonomousStatus
      ] = await Promise.allSettled([
        this.getSystemHealth(),
        this.getOHLCVData('BTC-USDT'),
        this.getOHLCVData('ETH-USDT'),
        this.getRecentSignals(5),
        this.getPortfolioStatus(),
        this.getRecentTrades(10),
        this.getAutonomousStatus()
      ]);

      return {
        systemHealth: systemHealth.status === 'fulfilled' ? systemHealth.value : null,
        marketData: {
          BTC: marketDataBTC.status === 'fulfilled' ? marketDataBTC.value : [],
          ETH: marketDataETH.status === 'fulfilled' ? marketDataETH.value : []
        },
        signals: recentSignals.status === 'fulfilled' ? recentSignals.value : [],
        portfolio: portfolioStatus.status === 'fulfilled' ? portfolioStatus.value : null,
        trades: recentTrades.status === 'fulfilled' ? recentTrades.value : [],
        autonomous: autonomousStatus.status === 'fulfilled' ? autonomousStatus.value : null
      };
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      return {
        systemHealth: null,
        marketData: { BTC: [], ETH: [] },
        signals: [],
        portfolio: null,
        trades: [],
        autonomous: null
      };
    }
  }
}

// Create and export a singleton instance
const apiService = new ApiService();
export default apiService;

// Export individual methods for convenience
export const {
  getSystemHealth,
  getSystemStatus,
  getMarketData,
  getLiveMarketData,
  getOHLCVData,
  getRecentSignals,
  getActiveSignals,
  getSignalPerformance,
  generateSignal,
  getPortfolioStatus,
  getPortfolioSummary,
  getPortfolioHistory,
  getRecentTrades,
  getTradingActivity,
  getTradingPerformance,
  getAutonomousStatus,
  getSystemMetrics,
  getConnectionStatus,
  testDeltaConnection,
  testOpenAIConnection,
  getAllDashboardData
} = apiService;

