#!/usr/bin/env python3
"""
Simple test script to verify model imports work correctly.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_individual_models():
    """Test importing each model file individually."""
    models_to_test = [
        'market_data',
        'signal', 
        'portfolio',
        'user',
        'compliance',
        'risk_profile'
    ]
    
    results = {}
    
    for model_name in models_to_test:
        try:
            module = __import__(f'app.models.{model_name}', fromlist=[model_name])
            results[model_name] = "✅ SUCCESS"
            print(f"✅ {model_name}.py - Import successful")
        except Exception as e:
            results[model_name] = f"❌ ERROR: {str(e)}"
            print(f"❌ {model_name}.py - Import failed: {str(e)}")
    
    return results

def test_models_init():
    """Test importing from models __init__.py"""
    try:
        # This will test if all imports in __init__.py work
        from app.models import (
            MarketData, CryptoPrice, OrderBook, Trade,
            Signal, SignalExecution, SignalPerformance,
            Portfolio, Position, Transaction,
            User, UserProfile, UserSettings,
            TaxRecord, TDSRecord, ComplianceLog,
            RiskProfile, RiskMetrics
        )
        print("✅ All models imported successfully from __init__.py")
        return True
    except Exception as e:
        print(f"❌ Failed to import from __init__.py: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Testing individual model files...")
    individual_results = test_individual_models()
    
    print("\n🔍 Testing models __init__.py...")
    init_success = test_models_init()
    
    print("\n📊 SUMMARY:")
    for model, result in individual_results.items():
        print(f"  {model}: {result}")
    
    print(f"  __init__.py: {'✅ SUCCESS' if init_success else '❌ FAILED'}")
    
    if init_success:
        print("\n🎉 ALL MODEL IMPORTS WORKING! Ready for Docker build.")
    else:
        print("\n🚨 Some imports failed. Need to fix before Docker build.")
