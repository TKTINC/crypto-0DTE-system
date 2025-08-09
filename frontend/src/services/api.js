// API Service for Crypto-0DTE System
// Handles all communication with the backend using the new API client

import apiClient from './apiClient.js';

class ApiService {
  constructor() {
    this.client = apiClient;
  }

  // Health and System Status
  async getSystemHealth() {
    return this.client.getHealthStatus();
  }

  async getSystemStatus() {
    return this.client.get('/api/v1/system/status');
  }

  // Market Data
  async getMarketData(symbol = 'BTC-USDT', limit = 100) {
    return this.client.get('/api/v1/market-data/recent', {
      params: { symbol, limit }
    });
  }

  async getLiveMarketData(symbol = 'BTC-USDT') {
    return this.client.get(`/api/v1/market-data/live/${symbol}`);
  }

  async getOHLCVData(symbol = 'BTC-USDT', timeframe = '1h', limit = 24) {
    return this.client.getMarketData(symbol, timeframe, limit);
  }

  // AI Signals
  async getRecentSignals(limit = 10) {
    return this.client.getSignals(limit);
  }

  async getActiveSignals() {
    return this.client.get('/api/v1/signals/active');
  }

  async getSignalPerformance() {
    return this.client.get('/api/v1/signals/performance');
  }

  async generateSignal(symbol, timeframe = '1h') {
    return this.client.post('/api/v1/signals/generate', { symbol, timeframe });
  }

  // Portfolio
  async getPortfolioStatus() {
    return this.client.getPortfolioStatus();
  }

  async getPortfolioSummary() {
    return this.client.get('/api/v1/portfolio/summary');
  }

  async getPortfolioHistory(days = 7) {
    return this.client.get('/api/v1/portfolio/history', {
      params: { days }
    });
  }

  // Trading
  async getRecentTrades(limit = 20) {
    return this.client.getTrades(limit);
  }

  async getTradingActivity() {
    return this.client.get('/api/v1/trading/activity');
  }

  async getTradingPerformance() {
    return this.client.get('/api/v1/trading/performance');
  }

  // Performance Metrics
  async getPerformanceMetrics() {
    return this.client.get('/api/v1/portfolio/performance');
  }

  async getSystemMetrics() {
    return this.client.getMetrics();
  }

  // Connection Testing
  async testDeltaConnection() {
    return this.client.get('/api/v1/market-data/test-connection');
  }

  async testOpenAIConnection() {
    return this.client.get('/api/v1/signals/test-ai-connection');
  }

  // Autonomous System Monitoring
  async getAutonomousStatus() {
    return this.client.get('/api/v1/autonomous/status');
  }

  async getConnectionStatus() {
    return this.client.get('/api/v1/monitoring/connections');
  }

  // Environment Management
  async getEnvironmentStatus() {
    return this.client.getEnvironmentStatus();
  }

  async switchEnvironment(environment) {
    return this.client.switchEnvironment(environment);
  }

  async emergencyStop() {
    return this.client.emergencyStop();
  }

  // Orders Journal
  async getOrdersJournal(params = {}) {
    return this.client.getOrdersJournal(params);
  }

  // Real-time Metrics
  async getRealTimeMetrics() {
    return this.client.getRealTimeMetrics();
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
        autonomousStatus,
        environmentStatus
      ] = await Promise.allSettled([
        this.getSystemHealth(),
        this.getOHLCVData('BTC-USDT'),
        this.getOHLCVData('ETH-USDT'),
        this.getRecentSignals(5),
        this.getPortfolioStatus(),
        this.getRecentTrades(10),
        this.getAutonomousStatus(),
        this.getEnvironmentStatus()
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
        autonomous: autonomousStatus.status === 'fulfilled' ? autonomousStatus.value : null,
        environment: environmentStatus.status === 'fulfilled' ? environmentStatus.value : null
      };
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      return {
        systemHealth: null,
        marketData: { BTC: [], ETH: [] },
        signals: [],
        portfolio: null,
        trades: [],
        autonomous: null,
        environment: null
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
  getAllDashboardData,
  getEnvironmentStatus,
  switchEnvironment,
  emergencyStop,
  getOrdersJournal,
  getRealTimeMetrics
} = apiService;

