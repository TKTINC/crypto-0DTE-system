import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, TrendingDown, Shield, AlertTriangle, Clock, Target, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx';
import { Badge } from '@/components/ui/badge.jsx';

const RealTimeMetrics = ({ environment }) => {
  const [metrics, setMetrics] = useState({
    risk_gate: {
      total_checks: 0,
      approvals: 0,
      denials: 0,
      approval_rate: 0,
      top_denial_reasons: []
    },
    orders: {
      total_submitted: 0,
      total_filled: 0,
      total_rejected: 0,
      fill_rate: 0,
      avg_fill_time: 0,
      avg_slippage: 0
    },
    portfolio: {
      total_value: 0,
      daily_pnl: 0,
      daily_pnl_percent: 0,
      open_positions: 0,
      total_exposure: 0,
      available_balance: 0
    },
    system: {
      uptime: 0,
      last_update: null,
      environment: environment || 'TESTNET',
      status: 'active'
    }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Fetch metrics from API
  const fetchMetrics = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/metrics/summary');
      if (!response.ok) throw new Error('Failed to fetch metrics');
      
      const data = await response.json();
      setMetrics(prevMetrics => ({
        ...prevMetrics,
        ...data
      }));
      setLastUpdate(new Date());
    } catch (err) {
      setError(err.message);
      console.error('Error fetching metrics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Set up real-time updates
  useEffect(() => {
    fetchMetrics();
    
    // Update every 5 seconds for real-time feel
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, [environment]);

  // Format time duration
  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  };

  // Format percentage
  const formatPercent = (value) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  // Format currency
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  // Get status color
  const getStatusColor = (value, thresholds) => {
    if (value >= thresholds.good) return 'text-green-600';
    if (value >= thresholds.warning) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Get PnL color
  const getPnLColor = (value) => {
    if (value > 0) return 'text-green-600';
    if (value < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const isPaperTrading = environment === 'TESTNET';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Real-Time Metrics</h2>
        <div className="flex items-center gap-2">
          <Badge variant={isPaperTrading ? "secondary" : "destructive"} className={isPaperTrading ? "bg-blue-500" : "bg-red-500"}>
            {environment}
          </Badge>
          <div className="flex items-center gap-1 text-sm text-gray-500">
            <Activity className={`h-4 w-4 ${isLoading ? 'animate-pulse' : ''}`} />
            Updated {formatDuration(Math.floor((new Date() - lastUpdate) / 1000))} ago
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="h-4 w-4" />
              <span className="font-medium">Error loading metrics:</span>
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Risk Gate Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-600" />
            Risk Gate Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {metrics.risk_gate.total_checks.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500">Total Checks</div>
            </div>
            
            <div className="text-center">
              <div className={`text-2xl font-bold ${getStatusColor(metrics.risk_gate.approval_rate, { good: 0.8, warning: 0.6 })}`}>
                {formatPercent(metrics.risk_gate.approval_rate)}
              </div>
              <div className="text-sm text-gray-500">Approval Rate</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {metrics.risk_gate.approvals.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500">Approved</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {metrics.risk_gate.denials.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500">Denied</div>
            </div>
          </div>
          
          {/* Top Denial Reasons */}
          {metrics.risk_gate.top_denial_reasons.length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <h4 className="font-medium text-gray-700 mb-2">Top Denial Reasons:</h4>
              <div className="flex flex-wrap gap-2">
                {metrics.risk_gate.top_denial_reasons.slice(0, 3).map((reason, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {reason.reason}: {reason.count}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Order Execution Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5 text-purple-600" />
            Order Execution Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {metrics.orders.total_submitted.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500">Orders Submitted</div>
            </div>
            
            <div className="text-center">
              <div className={`text-2xl font-bold ${getStatusColor(metrics.orders.fill_rate, { good: 0.95, warning: 0.85 })}`}>
                {formatPercent(metrics.orders.fill_rate)}
              </div>
              <div className="text-sm text-gray-500">Fill Rate</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {metrics.orders.avg_fill_time.toFixed(1)}s
              </div>
              <div className="text-sm text-gray-500">Avg Fill Time</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {metrics.orders.total_filled.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500">Filled</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {metrics.orders.total_rejected.toLocaleString()}
              </div>
              <div className="text-sm text-gray-500">Rejected</div>
            </div>
            
            <div className="text-center">
              <div className={`text-2xl font-bold ${getStatusColor(1 - Math.abs(metrics.orders.avg_slippage), { good: 0.999, warning: 0.995 })}`}>
                {(metrics.orders.avg_slippage * 100).toFixed(3)}%
              </div>
              <div className="text-sm text-gray-500">Avg Slippage</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Portfolio Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-green-600" />
            Portfolio Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {formatCurrency(metrics.portfolio.total_value)}
              </div>
              <div className="text-sm text-gray-500">Total Value</div>
            </div>
            
            <div className="text-center">
              <div className={`text-2xl font-bold ${getPnLColor(metrics.portfolio.daily_pnl)}`}>
                {formatCurrency(metrics.portfolio.daily_pnl)}
              </div>
              <div className="text-sm text-gray-500">Daily P&L</div>
            </div>
            
            <div className="text-center">
              <div className={`text-2xl font-bold ${getPnLColor(metrics.portfolio.daily_pnl_percent)}`}>
                {formatPercent(metrics.portfolio.daily_pnl_percent)}
              </div>
              <div className="text-sm text-gray-500">Daily P&L %</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {metrics.portfolio.open_positions}
              </div>
              <div className="text-sm text-gray-500">Open Positions</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {formatCurrency(metrics.portfolio.total_exposure)}
              </div>
              <div className="text-sm text-gray-500">Total Exposure</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {formatCurrency(metrics.portfolio.available_balance)}
              </div>
              <div className="text-sm text-gray-500">Available Balance</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-600" />
            System Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {formatDuration(metrics.system.uptime)}
              </div>
              <div className="text-sm text-gray-500">Uptime</div>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center gap-1">
                <div className={`w-3 h-3 rounded-full ${metrics.system.status === 'active' ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
                <span className="text-lg font-bold text-gray-700 capitalize">
                  {metrics.system.status}
                </span>
              </div>
              <div className="text-sm text-gray-500">Status</div>
            </div>
            
            <div className="text-center">
              <div className={`text-lg font-bold ${isPaperTrading ? 'text-blue-600' : 'text-red-600'}`}>
                {metrics.system.environment}
              </div>
              <div className="text-sm text-gray-500">Environment</div>
            </div>
            
            <div className="text-center">
              <div className="text-lg font-bold text-gray-600">
                {metrics.system.last_update ? 
                  new Date(metrics.system.last_update).toLocaleTimeString() : 
                  'Never'
                }
              </div>
              <div className="text-sm text-gray-500">Last Update</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default RealTimeMetrics;

