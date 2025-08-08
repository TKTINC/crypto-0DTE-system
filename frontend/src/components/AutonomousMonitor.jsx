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

      {/* Recent Activity Log - Enhanced */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <CardTitle className="text-white flex items-center justify-between">
            <div className="flex items-center">
              <Clock className="h-5 w-5 text-cyan-500 mr-2" />
              Recent Autonomous Activity
            </div>
            <Badge variant="outline" className="text-cyan-400 border-cyan-400">
              Live Updates
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Signal Generation Activity */}
            {signalGeneration.lastSignal && (
              <div className="border border-slate-600 rounded-lg p-4 bg-slate-700/50">
                <div className="flex items-start space-x-3">
                  <Brain className="h-5 w-5 text-purple-500 mt-0.5" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-white">AI Signal Generated</h4>
                      <Badge 
                        variant={signalGeneration.lastSignal.type === 'BUY' ? 'default' : 'destructive'}
                        className="text-xs"
                      >
                        {signalGeneration.lastSignal.type}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div>
                        <span className="text-slate-400">Symbol:</span>
                        <span className="text-white ml-1">{signalGeneration.lastSignal.symbol}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Confidence:</span>
                        <span className="text-white ml-1">{signalGeneration.lastSignal.confidence}%</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Entry Price:</span>
                        <span className="text-white ml-1">${signalGeneration.lastSignal.entry_price?.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Target:</span>
                        <span className="text-green-400 ml-1">${signalGeneration.lastSignal.target_price?.toLocaleString()}</span>
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-slate-400">
                      Strategy: {signalGeneration.lastSignal.strategy} • {formatTimeAgo(signalGeneration.lastSignal.created_at)}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Trading Activity */}
            {tradingActivity.lastTrade && (
              <div className="border border-slate-600 rounded-lg p-4 bg-slate-700/50">
                <div className="flex items-start space-x-3">
                  <TrendingUp className="h-5 w-5 text-green-500 mt-0.5" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-white">Trade Executed</h4>
                      <Badge 
                        variant={tradingActivity.lastTrade.side === 'buy' ? 'default' : 'destructive'}
                        className="text-xs"
                      >
                        {tradingActivity.lastTrade.side?.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div>
                        <span className="text-slate-400">Symbol:</span>
                        <span className="text-white ml-1">{tradingActivity.lastTrade.symbol}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Quantity:</span>
                        <span className="text-white ml-1">{tradingActivity.lastTrade.quantity}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Price:</span>
                        <span className="text-white ml-1">${tradingActivity.lastTrade.price?.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Value:</span>
                        <span className="text-white ml-1">${(tradingActivity.lastTrade.quantity * tradingActivity.lastTrade.price)?.toLocaleString()}</span>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center justify-between text-xs">
                      <span className="text-slate-400">
                        Order ID: {tradingActivity.lastTrade.order_id} • {formatTimeAgo(tradingActivity.lastTrade.timestamp)}
                      </span>
                      <Badge 
                        variant="outline" 
                        className={`text-xs ${tradingActivity.lastTrade.status === 'filled' ? 'text-green-400 border-green-400' : 'text-yellow-400 border-yellow-400'}`}
                      >
                        {tradingActivity.lastTrade.status?.toUpperCase()}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Market Data Activity */}
            {marketDataFlow.lastUpdate && (
              <div className="border border-slate-600 rounded-lg p-4 bg-slate-700/50">
                <div className="flex items-start space-x-3">
                  <BarChart3 className="h-5 w-5 text-blue-500 mt-0.5" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-white">Market Data Update</h4>
                      <Badge variant="outline" className="text-blue-400 border-blue-400 text-xs">
                        {marketDataFlow.active ? 'ACTIVE' : 'INACTIVE'}
                      </Badge>
                    </div>
                    <div className="text-xs text-slate-400">
                      Last update: {formatTimeAgo(marketDataFlow.lastUpdate)} • Rate: {marketDataFlow.rate || 'N/A'} updates/min
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!signalGeneration.lastSignal && !tradingActivity.lastTrade && !marketDataFlow.lastUpdate && (
              <div className="text-center py-8">
                <AlertTriangle className="h-8 w-8 text-yellow-500 mx-auto mb-2" />
                <p className="text-slate-400">No recent autonomous activity detected</p>
                <p className="text-xs text-slate-500 mt-1">System is monitoring markets and waiting for trading opportunities</p>
              </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AutonomousMonitor;

