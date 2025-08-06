import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, Activity, DollarSign, Bitcoin, Zap, Brain, Target, AlertTriangle, BarChart3, RefreshCw, Wifi, WifiOff } from 'lucide-react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Progress } from '@/components/ui/progress.jsx'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area, BarChart, Bar } from 'recharts'
import { useRealTimeData, useMarketData } from './hooks/useRealTimeData'
import AutonomousMonitor from './components/AutonomousMonitor'
import './App.css'

function Dashboard() {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [activeTab, setActiveTab] = useState('overview')
  
  // Real-time data hooks
  const {
    systemHealth,
    marketData,
    signals,
    portfolio,
    trades,
    autonomous,
    connectionStatus,
    loading,
    error,
    lastUpdated,
    refreshData
  } = useRealTimeData(30000) // Update every 30 seconds

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const formatCurrency = (value) => {
    if (!value && value !== 0) return '$0'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  const formatPercent = (value) => {
    if (!value && value !== 0) return '0.00%'
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  // Transform market data for charts
  const transformMarketDataForChart = (data) => {
    if (!data || !Array.isArray(data)) return []
    return data.slice(-24).map((item, index) => ({
      time: new Date(item.timestamp).toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit' 
      }),
      price: item.close,
      volume: item.volume
    }))
  }

  const btcChartData = transformMarketDataForChart(marketData.BTC)
  const ethChartData = transformMarketDataForChart(marketData.ETH)

  // Get latest prices
  const btcPrice = marketData.BTC?.[marketData.BTC.length - 1]?.close || 0
  const ethPrice = marketData.ETH?.[marketData.ETH.length - 1]?.close || 0

  // Calculate price changes (simplified)
  const btcChange = marketData.BTC?.length >= 2 ? 
    ((marketData.BTC[marketData.BTC.length - 1]?.close - marketData.BTC[marketData.BTC.length - 2]?.close) / marketData.BTC[marketData.BTC.length - 2]?.close * 100) : 0
  const ethChange = marketData.ETH?.length >= 2 ? 
    ((marketData.ETH[marketData.ETH.length - 1]?.close - marketData.ETH[marketData.ETH.length - 2]?.close) / marketData.ETH[marketData.ETH.length - 2]?.close * 100) : 0

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-900/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <Bitcoin className="h-8 w-8 text-orange-500" />
                <Zap className="h-6 w-6 text-yellow-500" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Crypto-0DTE-System</h1>
                <p className="text-sm text-slate-400">AI-Powered Autonomous Trading</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* Connection Status */}
              <div className="text-right">
                <p className="text-sm text-slate-400">Backend</p>
                <div className="flex items-center space-x-2">
                  {connectionStatus.backend ? (
                    <>
                      <Wifi className="h-4 w-4 text-green-500" />
                      <span className="text-sm font-medium text-green-400">CONNECTED</span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="h-4 w-4 text-red-500" />
                      <span className="text-sm font-medium text-red-400">DISCONNECTED</span>
                    </>
                  )}
                </div>
              </div>

              {/* System Status */}
              <div className="text-right">
                <p className="text-sm text-slate-400">System Status</p>
                <div className="flex items-center space-x-2">
                  <div className={`h-2 w-2 rounded-full ${systemHealth?.status === 'healthy' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                  <span className={`text-sm font-medium ${systemHealth?.status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
                    {systemHealth?.status?.toUpperCase() || 'UNKNOWN'}
                  </span>
                </div>
              </div>

              {/* Refresh Button */}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={refreshData}
                disabled={loading}
                className="border-slate-600 text-slate-300 hover:bg-slate-700"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>

              {/* Current Time */}
              <div className="text-right">
                <p className="text-sm text-slate-400">Current Time</p>
                <p className="text-sm font-medium text-white">
                  {currentTime.toLocaleTimeString('en-US')}
                </p>
              </div>
            </div>
          </div>

          {/* Last Updated */}
          {lastUpdated && (
            <div className="mt-2 text-xs text-slate-500">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="mt-2 p-2 bg-red-900/50 border border-red-700 rounded text-red-300 text-sm">
              <AlertTriangle className="h-4 w-4 inline mr-2" />
              {error}
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-6 bg-slate-800 border-slate-700">
            <TabsTrigger value="overview" className="data-[state=active]:bg-purple-600">
              <BarChart3 className="h-4 w-4 mr-2" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="autonomous" className="data-[state=active]:bg-purple-600">
              <Activity className="h-4 w-4 mr-2" />
              Autonomous
            </TabsTrigger>
            <TabsTrigger value="signals" className="data-[state=active]:bg-purple-600">
              <Brain className="h-4 w-4 mr-2" />
              AI Signals
            </TabsTrigger>
            <TabsTrigger value="portfolio" className="data-[state=active]:bg-purple-600">
              <DollarSign className="h-4 w-4 mr-2" />
              Portfolio
            </TabsTrigger>
            <TabsTrigger value="performance" className="data-[state=active]:bg-purple-600">
              <TrendingUp className="h-4 w-4 mr-2" />
              Performance
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-purple-600">
              <Target className="h-4 w-4 mr-2" />
              Settings
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-slate-200">Portfolio Value</CardTitle>
                  <DollarSign className="h-4 w-4 text-green-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-white">
                    {formatCurrency(portfolio?.total_value || 0)}
                  </div>
                  <p className={`text-xs flex items-center ${(portfolio?.daily_pnl_percent || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {(portfolio?.daily_pnl_percent || 0) >= 0 ? 
                      <TrendingUp className="h-3 w-3 mr-1" /> : 
                      <TrendingDown className="h-3 w-3 mr-1" />
                    }
                    {formatPercent(portfolio?.daily_pnl_percent || 0)} today
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-slate-800 border-slate-700">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-slate-200">Daily P&L</CardTitle>
                  {(portfolio?.daily_pnl || 0) >= 0 ? 
                    <TrendingUp className="h-4 w-4 text-green-500" /> : 
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  }
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold ${(portfolio?.daily_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {(portfolio?.daily_pnl || 0) >= 0 ? '+' : ''}{formatCurrency(portfolio?.daily_pnl || 0)}
                  </div>
                  <p className="text-xs text-slate-400">
                    {signals?.length || 0} signals executed
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-slate-800 border-slate-700">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-slate-200">Win Rate</CardTitle>
                  <Target className="h-4 w-4 text-blue-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-white">
                    {portfolio?.win_rate ? `${portfolio.win_rate}%` : 'N/A'}
                  </div>
                  <p className="text-xs text-blue-400">
                    {portfolio?.profitable_trades || 0}/{portfolio?.total_trades || 0} profitable trades
                  </p>
                </CardContent>
              </Card>

              <Card className="bg-slate-800 border-slate-700">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-slate-200">AI Confidence</CardTitle>
                  <Brain className="h-4 w-4 text-purple-500" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-white">
                    {signals?.length > 0 ? 
                      `${Math.round(signals.reduce((acc, signal) => acc + (signal.confidence || 0), 0) / signals.length)}%` : 
                      'N/A'
                    }
                  </div>
                  <Progress 
                    value={signals?.length > 0 ? 
                      signals.reduce((acc, signal) => acc + (signal.confidence || 0), 0) / signals.length : 
                      0
                    } 
                    className="mt-2 h-2" 
                  />
                </CardContent>
              </Card>
            </div>

            {/* Price Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center">
                    <Bitcoin className="h-5 w-5 text-orange-500 mr-2" />
                    BTC/USDT
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Current: ${btcPrice.toLocaleString()} ({formatPercent(btcChange)})
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {btcChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={200}>
                      <AreaChart data={btcChartData}>
                        <defs>
                          <linearGradient id="btcGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f97316" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9ca3af" />
                        <YAxis stroke="#9ca3af" />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#1f2937', 
                            border: '1px solid #374151',
                            borderRadius: '8px'
                          }}
                        />
                        <Area 
                          type="monotone" 
                          dataKey="price" 
                          stroke="#f97316" 
                          fillOpacity={1} 
                          fill="url(#btcGradient)" 
                          strokeWidth={2}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-[200px]">
                      <div className="text-center">
                        <AlertTriangle className="h-8 w-8 text-yellow-500 mx-auto mb-2" />
                        <p className="text-slate-400">No market data available</p>
                        <p className="text-xs text-slate-500">Check API connection</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white flex items-center">
                    <div className="h-5 w-5 bg-blue-500 rounded mr-2"></div>
                    ETH/USDT
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    Current: ${ethPrice.toLocaleString()} ({formatPercent(ethChange)})
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {ethChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={200}>
                      <AreaChart data={ethChartData}>
                        <defs>
                          <linearGradient id="ethGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="time" stroke="#9ca3af" />
                        <YAxis stroke="#9ca3af" />
                        <Tooltip 
                          contentStyle={{ 
                            backgroundColor: '#1f2937', 
                            border: '1px solid #374151',
                            borderRadius: '8px'
                          }}
                        />
                        <Area 
                          type="monotone" 
                          dataKey="price" 
                          stroke="#3b82f6" 
                          fillOpacity={1} 
                          fill="url(#ethGradient)" 
                          strokeWidth={2}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex items-center justify-center h-[200px]">
                      <div className="text-center">
                        <AlertTriangle className="h-8 w-8 text-yellow-500 mx-auto mb-2" />
                        <p className="text-slate-400">No market data available</p>
                        <p className="text-xs text-slate-500">Check API connection</p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Recent Signals */}
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">Recent AI Signals</CardTitle>
                <CardDescription className="text-slate-400">
                  Latest trading signals from AI strategies
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {signals && signals.length > 0 ? (
                    signals.slice(0, 3).map((signal, index) => (
                      <div key={signal.id || index} className="flex items-center justify-between p-4 bg-slate-700 rounded-lg">
                        <div className="flex items-center space-x-4">
                          <Badge 
                            variant={signal.type === 'BUY' ? 'default' : 'destructive'}
                            className={signal.type === 'BUY' ? 'bg-green-600' : 'bg-red-600'}
                          >
                            {signal.type || signal.side}
                          </Badge>
                          <div>
                            <p className="font-medium text-white">{signal.symbol}</p>
                            <p className="text-sm text-slate-400">{signal.strategy || 'AI Strategy'}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-white">{signal.confidence || 0}% confidence</p>
                          <p className="text-sm text-slate-400">
                            Entry: ${signal.entry_price || signal.price || 'N/A'}
                          </p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-8">
                      <Brain className="h-8 w-8 text-purple-500 mx-auto mb-2" />
                      <p className="text-slate-400">No recent signals available</p>
                      <p className="text-xs text-slate-500 mt-1">
                        {connectionStatus.backend ? 'AI signal generation may be inactive' : 'Check backend connection'}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Autonomous System Monitoring Tab */}
          <TabsContent value="autonomous" className="space-y-6">
            <AutonomousMonitor />
          </TabsContent>

          {/* AI Signals Tab */}
          <TabsContent value="signals" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card className="bg-slate-800 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center">
                      <Brain className="h-5 w-5 text-purple-500 mr-2" />
                      Active AI Signals
                    </CardTitle>
                    <CardDescription className="text-slate-400">
                      Real-time trading signals from 5 AI strategies
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {mockSignals.map((signal) => (
                        <div key={signal.id} className="p-4 bg-slate-700 rounded-lg">
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center space-x-3">
                              <Badge 
                                variant={signal.type === 'BUY' ? 'default' : 'destructive'}
                                className={signal.type === 'BUY' ? 'bg-green-600' : 'bg-red-600'}
                              >
                                {signal.type}
                              </Badge>
                              <span className="font-medium text-white">{signal.symbol}</span>
                              <Badge variant="outline" className="text-purple-400 border-purple-400">
                                {signal.strategy}
                              </Badge>
                            </div>
                            <Badge 
                              variant={signal.status === 'active' ? 'default' : 'secondary'}
                              className={signal.status === 'active' ? 'bg-blue-600' : 'bg-gray-600'}
                            >
                              {signal.status}
                            </Badge>
                          </div>
                          
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                            <div>
                              <p className="text-xs text-slate-400">Confidence</p>
                              <p className="font-medium text-white">{signal.confidence}%</p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-400">Entry</p>
                              <p className="font-medium text-white">${signal.entry}</p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-400">Target</p>
                              <p className="font-medium text-green-400">${signal.target}</p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-400">Stop Loss</p>
                              <p className="font-medium text-red-400">${signal.stopLoss}</p>
                            </div>
                          </div>
                          
                          <div className="mb-3">
                            <p className="text-xs text-slate-400 mb-1">AI Reasoning</p>
                            <p className="text-sm text-slate-300">{signal.reasoning}</p>
                          </div>
                          
                          <div className="flex items-center justify-between text-xs text-slate-400">
                            <span>Generated: {signal.timestamp}</span>
                            <Progress value={signal.confidence} className="w-20 h-2" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-6">
                <Card className="bg-slate-800 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white">Strategy Performance</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-400">BTC Lightning Scalp</span>
                        <span className="text-sm font-medium text-green-400">+2.8%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-400">ETH DeFi Correlation</span>
                        <span className="text-sm font-medium text-green-400">+3.2%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-400">Cross-Asset Arbitrage</span>
                        <span className="text-sm font-medium text-green-400">+1.9%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-400">Funding Rate Arbitrage</span>
                        <span className="text-sm font-medium text-green-400">+2.1%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-slate-400">Fear & Greed Contrarian</span>
                        <span className="text-sm font-medium text-green-400">+1.5%</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-slate-800 border-slate-700">
                  <CardHeader>
                    <CardTitle className="text-white">Market Sentiment</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between mb-2">
                          <span className="text-sm text-slate-400">Fear & Greed Index</span>
                          <span className="text-sm font-medium text-orange-400">72 (Greed)</span>
                        </div>
                        <Progress value={72} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between mb-2">
                          <span className="text-sm text-slate-400">Social Sentiment</span>
                          <span className="text-sm font-medium text-green-400">Bullish</span>
                        </div>
                        <Progress value={68} className="h-2" />
                      </div>
                      <div>
                        <div className="flex justify-between mb-2">
                          <span className="text-sm text-slate-400">DeFi TVL Change</span>
                          <span className="text-sm font-medium text-green-400">+8.2%</span>
                        </div>
                        <Progress value={82} className="h-2" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* Portfolio Tab */}
          <TabsContent value="portfolio" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Portfolio Allocation</CardTitle>
                  <CardDescription className="text-slate-400">
                    Current position distribution
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {mockPortfolio.positions.map((position, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-slate-700 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className={`h-3 w-3 rounded-full ${
                            position.symbol === 'BTCUSDT' ? 'bg-orange-500' :
                            position.symbol === 'ETHUSDT' ? 'bg-blue-500' : 'bg-green-500'
                          }`}></div>
                          <div>
                            <p className="font-medium text-white">{position.symbol}</p>
                            <p className="text-sm text-slate-400">Size: {position.size}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-white">{formatCurrency(position.value)}</p>
                          <p className={`text-sm ${position.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatPercent(position.pnlPercent)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Risk Metrics</CardTitle>
                  <CardDescription className="text-slate-400">
                    Portfolio risk analysis
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">Portfolio Beta</span>
                      <span className="text-sm font-medium text-white">1.23</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">Sharpe Ratio</span>
                      <span className="text-sm font-medium text-green-400">2.84</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">Max Drawdown</span>
                      <span className="text-sm font-medium text-red-400">-3.2%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">VaR (95%)</span>
                      <span className="text-sm font-medium text-yellow-400">-2.1%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-slate-400">Correlation (BTC/ETH)</span>
                      <span className="text-sm font-medium text-white">0.78</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Performance Tab */}
          <TabsContent value="performance" className="space-y-6">
            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">Portfolio Performance</CardTitle>
                <CardDescription className="text-slate-400">
                  8-day performance history
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={mockPerformance}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1f2937', 
                        border: '1px solid #374151',
                        borderRadius: '8px'
                      }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#10b981" 
                      strokeWidth={3}
                      dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Daily Signals</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={mockPerformance}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="date" stroke="#9ca3af" />
                      <YAxis stroke="#9ca3af" />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#1f2937', 
                          border: '1px solid #374151',
                          borderRadius: '8px'
                        }}
                      />
                      <Bar dataKey="signals" fill="#8b5cf6" />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Win Rate Trend</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={mockPerformance}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="date" stroke="#9ca3af" />
                      <YAxis stroke="#9ca3af" domain={[60, 100]} />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#1f2937', 
                          border: '1px solid #374151',
                          borderRadius: '8px'
                        }}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="winRate" 
                        stroke="#f59e0b" 
                        strokeWidth={2}
                        dot={{ fill: '#f59e0b', strokeWidth: 2, r: 3 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Trading Settings</CardTitle>
                  <CardDescription className="text-slate-400">
                    Configure AI trading parameters
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">Auto Trading</span>
                    <Button variant="outline" size="sm" className="bg-green-600 text-white border-green-600">
                      ENABLED
                    </Button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">Max Position Size</span>
                    <span className="text-sm font-medium text-white">25%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">Risk Level</span>
                    <span className="text-sm font-medium text-yellow-400">Moderate</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">Signal Confidence Threshold</span>
                    <span className="text-sm font-medium text-white">70%</span>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-800 border-slate-700">
                <CardHeader>
                  <CardTitle className="text-white">Strategy Configuration</CardTitle>
                  <CardDescription className="text-slate-400">
                    Enable/disable AI strategies
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">BTC Lightning Scalp</span>
                    <Button variant="outline" size="sm" className="bg-green-600 text-white border-green-600">
                      ON
                    </Button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">ETH DeFi Correlation</span>
                    <Button variant="outline" size="sm" className="bg-green-600 text-white border-green-600">
                      ON
                    </Button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">Cross-Asset Arbitrage</span>
                    <Button variant="outline" size="sm" className="bg-green-600 text-white border-green-600">
                      ON
                    </Button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">Funding Rate Arbitrage</span>
                    <Button variant="outline" size="sm" className="bg-gray-600 text-white border-gray-600">
                      OFF
                    </Button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-300">Fear & Greed Contrarian</span>
                    <Button variant="outline" size="sm" className="bg-green-600 text-white border-green-600">
                      ON
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="bg-slate-800 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white flex items-center">
                  <AlertTriangle className="h-5 w-5 text-yellow-500 mr-2" />
                  System Information
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <p className="text-sm text-slate-400 mb-1">System Version</p>
                    <p className="font-medium text-white">v1.0.0-beta</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400 mb-1">Last Update</p>
                    <p className="font-medium text-white">2024-01-15 10:30</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400 mb-1">Uptime</p>
                    <p className="font-medium text-white">2d 14h 23m</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App

