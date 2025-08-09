import React, { useState, useEffect } from 'react'
import { Switch } from '@/components/ui/switch.jsx'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Button } from '@/components/ui/button.jsx'
import { AlertTriangle, TestTube, DollarSign, Wifi, WifiOff, RefreshCw } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'

const EnvironmentSwitcher = ({ onEnvironmentChange }) => {
  const [environment, setEnvironment] = useState({
    environment: 'TESTNET',
    paper_trading: true,
    exchange_url: '',
    websocket_url: '',
    last_updated: new Date(),
    portfolio_balance: 0,
    active_positions: 0
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [switchResult, setSwitchResult] = useState(null)

  // Fetch current environment status
  const fetchEnvironmentStatus = async () => {
    try {
      const response = await fetch('/api/v1/autonomous/environment')
      if (!response.ok) throw new Error('Failed to fetch environment status')
      const data = await response.json()
      setEnvironment(data)
      setError(null)
    } catch (err) {
      setError('Failed to load environment status')
      console.error('Environment status error:', err)
    }
  }

  // Switch environment
  const switchEnvironment = async (paperTrading) => {
    setIsLoading(true)
    setSwitchResult(null)
    setError(null)

    try {
      const response = await fetch('/api/v1/autonomous/environment/switch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          paper_trading: paperTrading
        })
      })

      if (!response.ok) throw new Error('Failed to switch environment')
      
      const result = await response.json()
      setSwitchResult(result)
      
      // Refresh environment status
      await fetchEnvironmentStatus()
      
      // Notify parent component
      if (onEnvironmentChange) {
        onEnvironmentChange(result.new_environment, paperTrading)
      }

    } catch (err) {
      setError('Failed to switch environment')
      console.error('Environment switch error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // Handle switch toggle
  const handleSwitchChange = (checked) => {
    // checked = true means paper trading (TESTNET)
    // checked = false means live trading (LIVE)
    switchEnvironment(checked)
  }

  // Load environment status on component mount
  useEffect(() => {
    fetchEnvironmentStatus()
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchEnvironmentStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const isPaperTrading = environment.paper_trading
  const environmentColor = isPaperTrading ? 'bg-blue-500' : 'bg-red-500'
  const environmentTextColor = isPaperTrading ? 'text-blue-600' : 'text-red-600'
  const environmentBgColor = isPaperTrading ? 'bg-blue-50' : 'bg-red-50'

  return (
    <Card className={`border-2 ${isPaperTrading ? 'border-blue-200' : 'border-red-200'} ${environmentBgColor}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            {isPaperTrading ? (
              <TestTube className="h-5 w-5 text-blue-600" />
            ) : (
              <DollarSign className="h-5 w-5 text-red-600" />
            )}
            Trading Environment
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchEnvironmentStatus}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Environment Status Badge */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge 
              variant={isPaperTrading ? "secondary" : "destructive"}
              className={`${environmentColor} text-white font-semibold px-3 py-1`}
            >
              {environment.environment}
            </Badge>
            <div className="flex items-center gap-1 text-sm text-gray-600">
              {isPaperTrading ? (
                <Wifi className="h-4 w-4 text-blue-500" />
              ) : (
                <WifiOff className="h-4 w-4 text-red-500" />
              )}
              {isPaperTrading ? 'Testnet' : 'Live Trading'}
            </div>
          </div>
          
          {/* Environment Switch */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Paper</span>
            <Switch
              checked={isPaperTrading}
              onCheckedChange={handleSwitchChange}
              disabled={isLoading}
              className="data-[state=checked]:bg-blue-500 data-[state=unchecked]:bg-red-500"
            />
            <span className="text-sm font-medium">Live</span>
          </div>
        </div>

        {/* Environment Details */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="font-medium text-gray-700">Exchange URL</div>
            <div className="text-gray-600 truncate" title={environment.exchange_url}>
              {environment.exchange_url}
            </div>
          </div>
          <div>
            <div className="font-medium text-gray-700">Portfolio Balance</div>
            <div className={`font-semibold ${environmentTextColor}`}>
              {environment.portfolio_balance !== null 
                ? `$${environment.portfolio_balance.toLocaleString()}` 
                : 'Not Available'
              }
            </div>
          </div>
        </div>

        {/* Active Positions */}
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700">Active Positions</span>
          <span className={`font-semibold ${environmentTextColor}`}>
            {environment.active_positions}
          </span>
        </div>

        {/* Warning for Live Trading */}
        {!isPaperTrading && (
          <Alert className="border-red-200 bg-red-50">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              <strong>Live Trading Mode:</strong> Real money is at risk. All trades will be executed with actual funds.
            </AlertDescription>
          </Alert>
        )}

        {/* Paper Trading Info */}
        {isPaperTrading && (
          <Alert className="border-blue-200 bg-blue-50">
            <TestTube className="h-4 w-4 text-blue-600" />
            <AlertDescription className="text-blue-800">
              <strong>Paper Trading Mode:</strong> Safe testing environment with virtual funds. No real money at risk.
            </AlertDescription>
          </Alert>
        )}

        {/* Switch Result Message */}
        {switchResult && (
          <Alert className={`border-green-200 bg-green-50`}>
            <AlertDescription className="text-green-800">
              {switchResult.message}
            </AlertDescription>
          </Alert>
        )}

        {/* Error Message */}
        {error && (
          <Alert className="border-red-200 bg-red-50">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              {error}
            </AlertDescription>
          </Alert>
        )}

        {/* Last Updated */}
        <div className="text-xs text-gray-500 text-center">
          Last updated: {new Date(environment.last_updated).toLocaleString()}
        </div>
      </CardContent>
    </Card>
  )
}

export default EnvironmentSwitcher

