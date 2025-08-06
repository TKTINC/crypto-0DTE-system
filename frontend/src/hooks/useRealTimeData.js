import { useState, useEffect, useCallback, useRef } from 'react';
import apiService from '../services/api';

// Custom hook for managing real-time data updates
export const useRealTimeData = (updateInterval = 30000) => {
  const [data, setData] = useState({
    systemHealth: null,
    marketData: { BTC: [], ETH: [] },
    signals: [],
    portfolio: null,
    trades: [],
    autonomous: null,
    loading: true,
    error: null,
    lastUpdated: null
  });

  const [connectionStatus, setConnectionStatus] = useState({
    backend: false,
    delta: false,
    openai: false
  });

  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  // Fetch all dashboard data
  const fetchDashboardData = useCallback(async () => {
    try {
      const dashboardData = await apiService.getAllDashboardData();
      
      if (mountedRef.current) {
        setData(prevData => ({
          ...dashboardData,
          loading: false,
          error: null,
          lastUpdated: new Date()
        }));

        // Update connection status based on successful API calls
        setConnectionStatus({
          backend: dashboardData.systemHealth !== null,
          delta: dashboardData.marketData.BTC.length > 0 || dashboardData.marketData.ETH.length > 0,
          openai: dashboardData.signals.length > 0
        });
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
      if (mountedRef.current) {
        setData(prevData => ({
          ...prevData,
          loading: false,
          error: error.message
        }));

        setConnectionStatus({
          backend: false,
          delta: false,
          openai: false
        });
      }
    }
  }, []);

  // Test individual API connections
  const testConnections = useCallback(async () => {
    try {
      const [healthTest, deltaTest, openaiTest] = await Promise.allSettled([
        apiService.getSystemHealth(),
        apiService.testDeltaConnection(),
        apiService.testOpenAIConnection()
      ]);

      if (mountedRef.current) {
        setConnectionStatus({
          backend: healthTest.status === 'fulfilled',
          delta: deltaTest.status === 'fulfilled',
          openai: openaiTest.status === 'fulfilled'
        });
      }
    } catch (error) {
      console.error('Connection test failed:', error);
    }
  }, []);

  // Manual refresh function
  const refreshData = useCallback(() => {
    setData(prevData => ({ ...prevData, loading: true }));
    fetchDashboardData();
  }, [fetchDashboardData]);

  // Start/stop real-time updates
  const startRealTimeUpdates = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // Initial fetch
    fetchDashboardData();
    testConnections();

    // Set up interval for updates
    intervalRef.current = setInterval(() => {
      fetchDashboardData();
      // Test connections less frequently
      if (Math.random() < 0.3) {
        testConnections();
      }
    }, updateInterval);
  }, [fetchDashboardData, testConnections, updateInterval]);

  const stopRealTimeUpdates = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Initialize on mount
  useEffect(() => {
    mountedRef.current = true;
    startRealTimeUpdates();

    return () => {
      mountedRef.current = false;
      stopRealTimeUpdates();
    };
  }, [startRealTimeUpdates, stopRealTimeUpdates]);

  return {
    ...data,
    connectionStatus,
    refreshData,
    startRealTimeUpdates,
    stopRealTimeUpdates
  };
};

// Hook for autonomous system monitoring
export const useAutonomousMonitoring = () => {
  const [autonomousData, setAutonomousData] = useState({
    isActive: false,
    signalGeneration: { active: false, lastSignal: null, count: 0 },
    marketDataFlow: { active: false, lastUpdate: null, rate: 0 },
    tradingActivity: { active: false, lastTrade: null, count: 0 },
    systemMetrics: null,
    loading: true,
    error: null
  });

  const fetchAutonomousStatus = useCallback(async () => {
    try {
      const [autonomousStatus, systemMetrics, recentSignals, recentTrades] = await Promise.allSettled([
        apiService.getAutonomousStatus(),
        apiService.getSystemMetrics(),
        apiService.getRecentSignals(1),
        apiService.getRecentTrades(1)
      ]);

      const status = {
        isActive: autonomousStatus.status === 'fulfilled' && autonomousStatus.value?.active,
        signalGeneration: {
          active: recentSignals.status === 'fulfilled' && recentSignals.value?.length > 0,
          lastSignal: recentSignals.status === 'fulfilled' ? recentSignals.value?.[0] : null,
          count: recentSignals.status === 'fulfilled' ? recentSignals.value?.length || 0 : 0
        },
        tradingActivity: {
          active: recentTrades.status === 'fulfilled' && recentTrades.value?.length > 0,
          lastTrade: recentTrades.status === 'fulfilled' ? recentTrades.value?.[0] : null,
          count: recentTrades.status === 'fulfilled' ? recentTrades.value?.length || 0 : 0
        },
        systemMetrics: systemMetrics.status === 'fulfilled' ? systemMetrics.value : null,
        loading: false,
        error: null
      };

      setAutonomousData(status);
    } catch (error) {
      console.error('Failed to fetch autonomous status:', error);
      setAutonomousData(prevData => ({
        ...prevData,
        loading: false,
        error: error.message
      }));
    }
  }, []);

  useEffect(() => {
    fetchAutonomousStatus();
    const interval = setInterval(fetchAutonomousStatus, 15000); // Update every 15 seconds

    return () => clearInterval(interval);
  }, [fetchAutonomousStatus]);

  return {
    ...autonomousData,
    refresh: fetchAutonomousStatus
  };
};

// Hook for market data with real-time updates
export const useMarketData = (symbols = ['BTC-USDT', 'ETH-USDT'], timeframe = '1h') => {
  const [marketData, setMarketData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMarketData = useCallback(async () => {
    try {
      setLoading(true);
      const promises = symbols.map(symbol => 
        apiService.getOHLCVData(symbol, timeframe, 24)
      );

      const results = await Promise.allSettled(promises);
      const data = {};

      symbols.forEach((symbol, index) => {
        if (results[index].status === 'fulfilled') {
          data[symbol] = results[index].value;
        } else {
          data[symbol] = [];
        }
      });

      setMarketData(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbols, timeframe]);

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [fetchMarketData]);

  return { marketData, loading, error, refresh: fetchMarketData };
};

