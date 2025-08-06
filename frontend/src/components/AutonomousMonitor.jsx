import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx';
import { Badge } from '@/components/ui/badge.jsx';
import { Progress } from '@/components/ui/progress.jsx';
import { 
  Activity, 
  Brain, 
  TrendingUp, 
  Zap, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Clock,
  BarChart3,
  DollarSign
} from 'lucide-react';
import { useAutonomousMonitoring } from '../hooks/useRealTimeData';

const AutonomousMonitor = () => {
  const {
    isActive,
    signalGeneration,
    marketDataFlow,
    tradingActivity,
    systemMetrics,
    loading,
    error,
    refresh
  } = useAutonomousMonitoring();

  const formatTime = (timestamp) => {
    if (!timestamp) return 'Never';
    return new Date(timestamp).toLocaleTimeString();
  };

  const formatTimeAgo = (timestamp) => {
    if (!timestamp) return 'Never';
    const now = new Date();
    const time = new Date(timestamp);
    const diffMs = now - time;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  if (loading) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Activity className="h-5 w-5 text-blue-500 mr-2 animate-pulse" />
            Autonomous System Monitor
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-2 text-slate-400">Loading system status...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <AlertTriangle className="h-5 w-5 text-red-500 mr-2" />
            Autonomous System Monitor
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <AlertTriangle className="h-8 w-8 text-red-500 mr-2" />
            <div>
              <p className="text-red-400 font-medium">Connection Error</p>
              <p className="text-slate-400 text-sm">{error}</p>
              <button 
                onClick={refresh}
                className="mt-2 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overall System Status */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center justify-between">
            <div className="flex items-center">
              <Activity className="h-5 w-5 text-blue-500 mr-2" />
              Autonomous System Status
            </div>
            <Badge 
              variant={isActive ? "default" : "destructive"}
              className={isActive ? "bg-green-600" : "bg-red-600"}
            >
              {isActive ? "ACTIVE" : "INACTIVE"}
            </Badge>
          </CardTitle>
          <CardDescription className="text-slate-400">
            Real-time monitoring of autonomous trading operations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Signal Generation Status */}
            <div className="p-4 bg-slate-700 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <Brain className="h-4 w-4 text-purple-500 mr-2" />
                  <span className="text-sm font-medium text-white">AI Signal Generation</span>
                </div>
                {signalGeneration.active ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500" />
                )}
              </div>
              <div className="space-y-1">
                <p className="text-xs text-slate-400">
                  Status: {signalGeneration.active ? "Generating" : "Inactive"}
                </p>
                <p className="text-xs text-slate-400">
                  Last Signal: {formatTimeAgo(signalGeneration.lastSignal?.created_at)}
                </p>
                <p className="text-xs text-slate-400">
                  Count: {signalGeneration.count} recent
                </p>
              </div>
            </div>

            {/* Market Data Flow */}
            <div className="p-4 bg-slate-700 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <BarChart3 className="h-4 w-4 text-blue-500 mr-2" />
                  <span className="text-sm font-medium text-white">Market Data Flow</span>
                </div>
                {marketDataFlow.active ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-red-500" />
                )}
              </div>
              <div className="space-y-1">
                <p className="text-xs text-slate-400">
                  Status: {marketDataFlow.active ? "Flowing" : "Stopped"}
                </p>
                <p className="text-xs text-slate-400">
                  Last Update: {formatTimeAgo(marketDataFlow.lastUpdate)}
                </p>
                <p className="text-xs text-slate-400">
                  Rate: {marketDataFlow.rate || 0} updates/min
                </p>
              </div>
            </div>

            {/* Trading Activity */}
            <div className="p-4 bg-slate-700 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <DollarSign className="h-4 w-4 text-green-500 mr-2" />
                  <span className="text-sm font-medium text-white">Trading Activity</span>
                </div>
                {tradingActivity.active ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <Clock className="h-4 w-4 text-yellow-500" />
                )}
              </div>
              <div className="space-y-1">
                <p className="text-xs text-slate-400">
                  Status: {tradingActivity.active ? "Active" : "Waiting"}
                </p>
                <p className="text-xs text-slate-400">
                  Last Trade: {formatTimeAgo(tradingActivity.lastTrade?.timestamp)}
                </p>
                <p className="text-xs text-slate-400">
                  Count: {tradingActivity.count} recent
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Metrics */}
      {systemMetrics && (
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center">
              <Zap className="h-5 w-5 text-yellow-500 mr-2" />
              System Performance Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* CPU Usage */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">CPU Usage</span>
                  <span className="text-sm text-white">{systemMetrics.cpu_usage || 0}%</span>
                </div>
                <Progress value={systemMetrics.cpu_usage || 0} className="h-2" />
              </div>

              {/* Memory Usage */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Memory Usage</span>
                  <span className="text-sm text-white">{systemMetrics.memory_usage || 0}%</span>
                </div>
                <Progress value={systemMetrics.memory_usage || 0} className="h-2" />
              </div>

              {/* API Response Time */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">API Response</span>
                  <span className="text-sm text-white">{systemMetrics.api_response_time || 0}ms</span>
                </div>
                <Progress 
                  value={Math.min((systemMetrics.api_response_time || 0) / 10, 100)} 
                  className="h-2" 
                />
              </div>

              {/* Database Connections */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">DB Connections</span>
                  <span className="text-sm text-white">{systemMetrics.db_connections || 0}</span>
                </div>
                <Progress 
                  value={Math.min((systemMetrics.db_connections || 0) * 10, 100)} 
                  className="h-2" 
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Activity Log */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center">
            <Clock className="h-5 w-5 text-cyan-500 mr-2" />
            Recent Autonomous Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {signalGeneration.lastSignal && (
              <div className="flex items-center space-x-3 p-3 bg-slate-700 rounded">
                <Brain className="h-4 w-4 text-purple-500" />
                <div className="flex-1">
                  <p className="text-sm text-white">
                    Generated {signalGeneration.lastSignal.type} signal for {signalGeneration.lastSignal.symbol}
                  </p>
                  <p className="text-xs text-slate-400">
                    Confidence: {signalGeneration.lastSignal.confidence}% • {formatTimeAgo(signalGeneration.lastSignal.created_at)}
                  </p>
                </div>
              </div>
            )}

            {tradingActivity.lastTrade && (
              <div className="flex items-center space-x-3 p-3 bg-slate-700 rounded">
                <TrendingUp className="h-4 w-4 text-green-500" />
                <div className="flex-1">
                  <p className="text-sm text-white">
                    Executed {tradingActivity.lastTrade.side} trade for {tradingActivity.lastTrade.symbol}
                  </p>
                  <p className="text-xs text-slate-400">
                    Size: {tradingActivity.lastTrade.quantity} • {formatTimeAgo(tradingActivity.lastTrade.timestamp)}
                  </p>
                </div>
              </div>
            )}

            {!signalGeneration.lastSignal && !tradingActivity.lastTrade && (
              <div className="text-center py-8">
                <AlertTriangle className="h-8 w-8 text-yellow-500 mx-auto mb-2" />
                <p className="text-slate-400">No recent autonomous activity detected</p>
                <p className="text-xs text-slate-500 mt-1">
                  Check API configuration and system status
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AutonomousMonitor;

