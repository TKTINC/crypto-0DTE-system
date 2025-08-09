import React, { useState, useEffect } from 'react';
import { Clock, TrendingUp, TrendingDown, AlertCircle, CheckCircle, XCircle, Filter, Download, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx';
import { Badge } from '@/components/ui/badge.jsx';
import { Button } from '@/components/ui/button.jsx';

const OrdersJournal = ({ environment }) => {
  const [orders, setOrders] = useState([]);
  const [filteredOrders, setFilteredOrders] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    status: 'all',
    symbol: 'all',
    side: 'all',
    timeRange: '24h'
  });
  const [sortBy, setSortBy] = useState('timestamp');
  const [sortOrder, setSortOrder] = useState('desc');

  // Fetch orders from API
  const fetchOrders = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/trading/orders/history');
      if (!response.ok) throw new Error('Failed to fetch orders');
      
      const data = await response.json();
      setOrders(data.orders || []);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching orders:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Apply filters and sorting
  useEffect(() => {
    let filtered = [...orders];

    // Apply filters
    if (filters.status !== 'all') {
      filtered = filtered.filter(order => order.status.toLowerCase() === filters.status);
    }
    
    if (filters.symbol !== 'all') {
      filtered = filtered.filter(order => order.symbol === filters.symbol);
    }
    
    if (filters.side !== 'all') {
      filtered = filtered.filter(order => order.side.toLowerCase() === filters.side);
    }

    // Apply time range filter
    const now = new Date();
    const timeRangeMs = {
      '1h': 60 * 60 * 1000,
      '24h': 24 * 60 * 60 * 1000,
      '7d': 7 * 24 * 60 * 60 * 1000,
      '30d': 30 * 24 * 60 * 60 * 1000,
      'all': Infinity
    };
    
    if (filters.timeRange !== 'all') {
      const cutoff = new Date(now.getTime() - timeRangeMs[filters.timeRange]);
      filtered = filtered.filter(order => new Date(order.timestamp) >= cutoff);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      if (sortBy === 'timestamp') {
        aVal = new Date(aVal);
        bVal = new Date(bVal);
      }
      
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    setFilteredOrders(filtered);
  }, [orders, filters, sortBy, sortOrder]);

  // Load orders on component mount and environment change
  useEffect(() => {
    fetchOrders();
    
    // Set up real-time updates every 10 seconds
    const interval = setInterval(fetchOrders, 10000);
    return () => clearInterval(interval);
  }, [environment]);

  // Get unique symbols for filter dropdown
  const uniqueSymbols = [...new Set(orders.map(order => order.symbol))];

  // Status badge styling
  const getStatusBadge = (status) => {
    const statusConfig = {
      filled: { color: 'bg-green-500', icon: CheckCircle, text: 'Filled' },
      pending: { color: 'bg-yellow-500', icon: Clock, text: 'Pending' },
      cancelled: { color: 'bg-gray-500', icon: XCircle, text: 'Cancelled' },
      rejected: { color: 'bg-red-500', icon: AlertCircle, text: 'Rejected' },
      partial: { color: 'bg-blue-500', icon: Clock, text: 'Partial' }
    };
    
    const config = statusConfig[status.toLowerCase()] || statusConfig.pending;
    const Icon = config.icon;
    
    return (
      <Badge className={`${config.color} text-white flex items-center gap-1`}>
        <Icon className="h-3 w-3" />
        {config.text}
      </Badge>
    );
  };

  // Side badge styling
  const getSideBadge = (side) => {
    return (
      <Badge className={`${side.toLowerCase() === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'} flex items-center gap-1`}>
        {side.toLowerCase() === 'buy' ? (
          <TrendingUp className="h-3 w-3" />
        ) : (
          <TrendingDown className="h-3 w-3" />
        )}
        {side.toUpperCase()}
      </Badge>
    );
  };

  // Calculate fill quality (slippage)
  const getFillQuality = (order) => {
    if (!order.fill_price || !order.expected_price) return null;
    
    const slippage = ((order.fill_price - order.expected_price) / order.expected_price) * 100;
    const absSlippage = Math.abs(slippage);
    
    let quality = 'good';
    let color = 'text-green-600';
    
    if (absSlippage > 0.5) {
      quality = 'poor';
      color = 'text-red-600';
    } else if (absSlippage > 0.1) {
      quality = 'fair';
      color = 'text-yellow-600';
    }
    
    return {
      slippage: slippage.toFixed(3),
      quality,
      color
    };
  };

  // Export orders to CSV
  const exportToCSV = () => {
    const headers = ['Timestamp', 'Symbol', 'Side', 'Type', 'Size', 'Price', 'Fill Price', 'Status', 'Slippage %'];
    const csvData = [
      headers.join(','),
      ...filteredOrders.map(order => [
        new Date(order.timestamp).toISOString(),
        order.symbol,
        order.side,
        order.type,
        order.size,
        order.price || '',
        order.fill_price || '',
        order.status,
        getFillQuality(order)?.slippage || ''
      ].join(','))
    ].join('\n');
    
    const blob = new Blob([csvData], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `orders_${environment}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Orders Journal
            <Badge variant="outline" className="ml-2">
              {filteredOrders.length} orders
            </Badge>
          </CardTitle>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={exportToCSV}
              disabled={filteredOrders.length === 0}
            >
              <Download className="h-4 w-4 mr-1" />
              Export
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={fetchOrders}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-4 p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-500" />
            <span className="text-sm font-medium">Filters:</span>
          </div>
          
          <select
            value={filters.status}
            onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
            className="px-2 py-1 border rounded text-sm"
          >
            <option value="all">All Status</option>
            <option value="filled">Filled</option>
            <option value="pending">Pending</option>
            <option value="cancelled">Cancelled</option>
            <option value="rejected">Rejected</option>
          </select>
          
          <select
            value={filters.symbol}
            onChange={(e) => setFilters(prev => ({ ...prev, symbol: e.target.value }))}
            className="px-2 py-1 border rounded text-sm"
          >
            <option value="all">All Symbols</option>
            {uniqueSymbols.map(symbol => (
              <option key={symbol} value={symbol}>{symbol}</option>
            ))}
          </select>
          
          <select
            value={filters.side}
            onChange={(e) => setFilters(prev => ({ ...prev, side: e.target.value }))}
            className="px-2 py-1 border rounded text-sm"
          >
            <option value="all">All Sides</option>
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </select>
          
          <select
            value={filters.timeRange}
            onChange={(e) => setFilters(prev => ({ ...prev, timeRange: e.target.value }))}
            className="px-2 py-1 border rounded text-sm"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24h</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="all">All Time</option>
          </select>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <div className="flex items-center gap-2 text-red-800">
              <AlertCircle className="h-4 w-4" />
              <span className="font-medium">Error loading orders:</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && orders.length === 0 && (
          <div className="text-center py-8">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-gray-400" />
            <p className="text-gray-500">Loading orders...</p>
          </div>
        )}

        {/* Orders Table */}
        {filteredOrders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="text-left p-3 cursor-pointer hover:bg-gray-100" onClick={() => {
                    setSortBy('timestamp');
                    setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
                  }}>
                    Time {sortBy === 'timestamp' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="text-left p-3">Symbol</th>
                  <th className="text-left p-3">Side</th>
                  <th className="text-left p-3">Type</th>
                  <th className="text-right p-3">Size</th>
                  <th className="text-right p-3">Price</th>
                  <th className="text-right p-3">Fill Price</th>
                  <th className="text-center p-3">Status</th>
                  <th className="text-right p-3">Slippage</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.map((order, index) => {
                  const fillQuality = getFillQuality(order);
                  return (
                    <tr key={order.id || index} className="border-b hover:bg-gray-50">
                      <td className="p-3">
                        <div className="text-xs text-gray-500">
                          {new Date(order.timestamp).toLocaleDateString()}
                        </div>
                        <div className="text-xs text-gray-400">
                          {new Date(order.timestamp).toLocaleTimeString()}
                        </div>
                      </td>
                      <td className="p-3 font-medium">{order.symbol}</td>
                      <td className="p-3">{getSideBadge(order.side)}</td>
                      <td className="p-3">
                        <Badge variant="outline" className="text-xs">
                          {order.type}
                        </Badge>
                      </td>
                      <td className="p-3 text-right font-mono">{order.size}</td>
                      <td className="p-3 text-right font-mono">
                        {order.price ? `$${parseFloat(order.price).toFixed(2)}` : '-'}
                      </td>
                      <td className="p-3 text-right font-mono">
                        {order.fill_price ? `$${parseFloat(order.fill_price).toFixed(2)}` : '-'}
                      </td>
                      <td className="p-3 text-center">{getStatusBadge(order.status)}</td>
                      <td className="p-3 text-right">
                        {fillQuality ? (
                          <span className={`font-mono text-xs ${fillQuality.color}`}>
                            {fillQuality.slippage}%
                          </span>
                        ) : (
                          <span className="text-gray-400 text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : !isLoading && (
          <div className="text-center py-8">
            <Clock className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-500 mb-2">No orders found</p>
            <p className="text-gray-400 text-sm">
              {orders.length === 0 
                ? "No orders have been placed yet" 
                : "Try adjusting your filters to see more orders"
              }
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default OrdersJournal;

