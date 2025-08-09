import React, { useState, useEffect } from 'react';
import { AlertTriangle, Power, Shield, Clock, Activity } from 'lucide-react';

const EmergencyKillSwitch = ({ onEmergencyStop, isActive, systemStatus }) => {
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  // Countdown timer for confirmation
  useEffect(() => {
    let timer;
    if (countdown > 0) {
      timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    } else if (countdown === 0 && showConfirmation) {
      setShowConfirmation(false);
    }
    return () => clearTimeout(timer);
  }, [countdown, showConfirmation]);

  const handleEmergencyClick = () => {
    if (!isActive) return;
    
    setShowConfirmation(true);
    setCountdown(10); // 10 second confirmation window
  };

  const handleConfirmEmergencyStop = async () => {
    setIsProcessing(true);
    try {
      await onEmergencyStop();
    } catch (error) {
      console.error('Emergency stop failed:', error);
    } finally {
      setIsProcessing(false);
      setShowConfirmation(false);
      setCountdown(0);
    }
  };

  const handleCancel = () => {
    setShowConfirmation(false);
    setCountdown(0);
  };

  return (
    <div className="relative">
      {/* Main Kill Switch Button */}
      <button
        onClick={handleEmergencyClick}
        disabled={!isActive || isProcessing}
        className={`relative p-4 rounded-lg border-2 transition-all duration-200 ${
          isActive
            ? 'border-red-500 bg-red-50 hover:bg-red-100 text-red-700 hover:border-red-600'
            : 'border-gray-300 bg-gray-50 text-gray-400 cursor-not-allowed'
        }`}
        title={isActive ? "Emergency stop all trading" : "System not active"}
      >
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-full ${isActive ? 'bg-red-100' : 'bg-gray-100'}`}>
            <Power className={`h-6 w-6 ${isActive ? 'text-red-600' : 'text-gray-400'}`} />
          </div>
          <div className="text-left">
            <div className="font-semibold">EMERGENCY STOP</div>
            <div className="text-sm opacity-75">
              {isActive ? 'Click to halt all trading' : 'System inactive'}
            </div>
          </div>
          {isActive && (
            <div className="absolute top-2 right-2">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
            </div>
          )}
        </div>
      </button>

      {/* System Status Indicator */}
      <div className="mt-2 flex items-center space-x-2 text-sm">
        <Activity className={`h-4 w-4 ${isActive ? 'text-green-500' : 'text-gray-400'}`} />
        <span className={isActive ? 'text-green-600' : 'text-gray-500'}>
          {systemStatus || (isActive ? 'System Active' : 'System Inactive')}
        </span>
      </div>

      {/* Confirmation Modal */}
      {showConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
            {/* Header */}
            <div className="flex items-center mb-4">
              <AlertTriangle className="h-8 w-8 text-red-500 mr-3" />
              <h2 className="text-xl font-bold text-red-600">
                EMERGENCY STOP CONFIRMATION
              </h2>
            </div>

            {/* Warning Message */}
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-800 font-semibold mb-2">
                ⚠️ THIS WILL IMMEDIATELY STOP ALL TRADING ACTIVITY
              </p>
              <div className="text-red-700 text-sm space-y-1">
                <p>• All pending orders will be canceled</p>
                <p>• All open positions will be closed at market price</p>
                <p>• Autonomous trading will be disabled</p>
                <p>• Manual intervention will be required to restart</p>
              </div>
            </div>

            {/* Current Status */}
            <div className="bg-gray-50 border rounded-lg p-3 mb-4">
              <h3 className="font-semibold text-gray-800 mb-2">Current System Status:</h3>
              <div className="text-sm text-gray-600 space-y-1">
                <p>• Active Positions: {systemStatus?.openPositions || 'Loading...'}</p>
                <p>• Pending Orders: {systemStatus?.pendingOrders || 'Loading...'}</p>
                <p>• Daily P&L: ${systemStatus?.dailyPnl?.toFixed(2) || 'Loading...'}</p>
              </div>
            </div>

            {/* Countdown Timer */}
            <div className="text-center mb-4">
              <div className="text-2xl font-bold text-red-600 mb-1">
                {countdown}
              </div>
              <div className="text-sm text-gray-600">
                Confirmation expires in {countdown} seconds
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex space-x-3">
              <button
                onClick={handleCancel}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors flex items-center justify-center"
              >
                <Shield className="h-4 w-4 mr-2" />
                Cancel
              </button>
              
              <button
                onClick={handleConfirmEmergencyStop}
                disabled={isProcessing}
                className={`flex-1 px-4 py-2 rounded-md transition-colors flex items-center justify-center ${
                  isProcessing
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-red-600 text-white hover:bg-red-700'
                }`}
              >
                {isProcessing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Stopping...
                  </>
                ) : (
                  <>
                    <Power className="h-4 w-4 mr-2" />
                    EMERGENCY STOP
                  </>
                )}
              </button>
            </div>

            {/* Footer Warning */}
            <div className="mt-4 text-xs text-gray-500 text-center">
              <Clock className="h-3 w-3 inline mr-1" />
              This action cannot be undone and requires manual restart
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmergencyKillSwitch;

