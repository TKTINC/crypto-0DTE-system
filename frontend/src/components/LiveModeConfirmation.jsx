import React, { useState } from 'react';
import { AlertTriangle, DollarSign, Shield, Clock } from 'lucide-react';

const LiveModeConfirmation = ({ isOpen, onConfirm, onCancel, currentBalance }) => {
  const [confirmationText, setConfirmationText] = useState('');
  const [acknowledgedRisks, setAcknowledgedRisks] = useState({
    realMoney: false,
    lossRisk: false,
    noUndo: false,
    responsibility: false
  });

  const requiredText = "I UNDERSTAND THE RISKS";
  const isConfirmationValid = confirmationText === requiredText && 
    Object.values(acknowledgedRisks).every(Boolean);

  const handleRiskAcknowledgment = (riskType) => {
    setAcknowledgedRisks(prev => ({
      ...prev,
      [riskType]: !prev[riskType]
    }));
  };

  const handleConfirm = () => {
    if (isConfirmationValid) {
      onConfirm();
      // Reset state
      setConfirmationText('');
      setAcknowledgedRisks({
        realMoney: false,
        lossRisk: false,
        noUndo: false,
        responsibility: false
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
        {/* Header */}
        <div className="flex items-center mb-4">
          <AlertTriangle className="h-8 w-8 text-red-500 mr-3" />
          <h2 className="text-xl font-bold text-red-600">
            LIVE TRADING MODE WARNING
          </h2>
        </div>

        {/* Warning Message */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-red-800 font-semibold mb-2">
            ⚠️ YOU ARE ABOUT TO ENABLE LIVE TRADING WITH REAL MONEY
          </p>
          <p className="text-red-700 text-sm">
            This will switch from paper trading (virtual funds) to live trading with your actual account balance.
          </p>
        </div>

        {/* Current Balance Display */}
        <div className="bg-gray-50 border rounded-lg p-3 mb-4">
          <div className="flex items-center">
            <DollarSign className="h-5 w-5 text-green-600 mr-2" />
            <span className="font-semibold">Current Account Balance:</span>
            <span className="ml-2 text-lg font-bold text-green-600">
              ${currentBalance?.toLocaleString() || 'Loading...'}
            </span>
          </div>
        </div>

        {/* Risk Acknowledgments */}
        <div className="space-y-3 mb-4">
          <h3 className="font-semibold text-gray-800">You must acknowledge these risks:</h3>
          
          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledgedRisks.realMoney}
              onChange={() => handleRiskAcknowledgment('realMoney')}
              className="mt-1 h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-700">
              <strong>Real Money at Risk:</strong> All trades will use your actual account funds, not virtual money.
            </span>
          </label>

          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledgedRisks.lossRisk}
              onChange={() => handleRiskAcknowledgment('lossRisk')}
              className="mt-1 h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-700">
              <strong>Loss Risk:</strong> You can lose some or all of your invested capital. Past performance does not guarantee future results.
            </span>
          </label>

          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledgedRisks.noUndo}
              onChange={() => handleRiskAcknowledgment('noUndo')}
              className="mt-1 h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-700">
              <strong>No Undo:</strong> Live trades cannot be undone. All executed orders are final and binding.
            </span>
          </label>

          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledgedRisks.responsibility}
              onChange={() => handleRiskAcknowledgment('responsibility')}
              className="mt-1 h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
            />
            <span className="text-sm text-gray-700">
              <strong>Full Responsibility:</strong> I take full responsibility for all trading decisions and outcomes.
            </span>
          </label>
        </div>

        {/* Confirmation Text Input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Type "{requiredText}" to confirm:
          </label>
          <input
            type="text"
            value={confirmationText}
            onChange={(e) => setConfirmationText(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
            placeholder="Type the confirmation text..."
          />
        </div>

        {/* Action Buttons */}
        <div className="flex space-x-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors flex items-center justify-center"
          >
            <Shield className="h-4 w-4 mr-2" />
            Stay in Paper Trading
          </button>
          
          <button
            onClick={handleConfirm}
            disabled={!isConfirmationValid}
            className={`flex-1 px-4 py-2 rounded-md transition-colors flex items-center justify-center ${
              isConfirmationValid
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            <AlertTriangle className="h-4 w-4 mr-2" />
            Enable Live Trading
          </button>
        </div>

        {/* Footer Warning */}
        <div className="mt-4 text-xs text-gray-500 text-center">
          <Clock className="h-3 w-3 inline mr-1" />
          This confirmation expires in 5 minutes for security
        </div>
      </div>
    </div>
  );
};

export default LiveModeConfirmation;

