"""
Model Manager for AI Signal Generation

Manages machine learning models for cryptocurrency trading signals.
"""

import logging
import pickle
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages AI/ML models for signal generation"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.model_metadata: Dict[str, Dict] = {}
        
    def load_model(self, model_name: str, model_path: str) -> bool:
        """Load a trained model from file"""
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                
            self.models[model_name] = model_data['model']
            self.scalers[model_name] = model_data.get('scaler')
            self.model_metadata[model_name] = model_data.get('metadata', {})
            
            logger.info(f"Loaded model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False
    
    def save_model(self, model_name: str, model: Any, scaler: Optional[StandardScaler] = None, 
                   metadata: Optional[Dict] = None, model_path: str = None) -> bool:
        """Save a trained model to file"""
        try:
            model_data = {
                'model': model,
                'scaler': scaler,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            if model_path is None:
                model_path = f"models/{model_name}.pkl"
                
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
                
            self.models[model_name] = model
            if scaler:
                self.scalers[model_name] = scaler
            self.model_metadata[model_name] = metadata or {}
            
            logger.info(f"Saved model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model {model_name}: {e}")
            return False
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """Get a loaded model"""
        return self.models.get(model_name)
    
    def get_scaler(self, model_name: str) -> Optional[StandardScaler]:
        """Get the scaler for a model"""
        return self.scalers.get(model_name)
    
    def predict(self, model_name: str, features: np.ndarray) -> Optional[np.ndarray]:
        """Make predictions using a loaded model"""
        model = self.get_model(model_name)
        if model is None:
            logger.warning(f"Model {model_name} not found")
            return None
            
        try:
            # Scale features if scaler is available
            scaler = self.get_scaler(model_name)
            if scaler is not None:
                features = scaler.transform(features)
                
            predictions = model.predict(features)
            return predictions
            
        except Exception as e:
            logger.error(f"Prediction failed for model {model_name}: {e}")
            return None
    
    def predict_proba(self, model_name: str, features: np.ndarray) -> Optional[np.ndarray]:
        """Get prediction probabilities using a loaded model"""
        model = self.get_model(model_name)
        if model is None or not hasattr(model, 'predict_proba'):
            return None
            
        try:
            # Scale features if scaler is available
            scaler = self.get_scaler(model_name)
            if scaler is not None:
                features = scaler.transform(features)
                
            probabilities = model.predict_proba(features)
            return probabilities
            
        except Exception as e:
            logger.error(f"Probability prediction failed for model {model_name}: {e}")
            return None
    
    def create_default_model(self, model_name: str, model_type: str = "random_forest") -> bool:
        """Create a default model for testing"""
        try:
            if model_type == "random_forest":
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42
                )
            elif model_type == "gradient_boosting":
                model = GradientBoostingClassifier(
                    n_estimators=100,
                    max_depth=6,
                    random_state=42
                )
            else:
                logger.error(f"Unknown model type: {model_type}")
                return False
                
            scaler = StandardScaler()
            
            self.models[model_name] = model
            self.scalers[model_name] = scaler
            self.model_metadata[model_name] = {
                'type': model_type,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'untrained'
            }
            
            logger.info(f"Created default {model_type} model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create default model {model_name}: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """List all loaded models"""
        return list(self.models.keys())
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get information about a model"""
        if model_name not in self.models:
            return None
            
        return {
            'name': model_name,
            'type': type(self.models[model_name]).__name__,
            'has_scaler': model_name in self.scalers,
            'metadata': self.model_metadata.get(model_name, {})
        }

