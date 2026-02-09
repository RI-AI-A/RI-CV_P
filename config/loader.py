from pathlib import Path
import yaml
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

class BusinessRulesConfig:
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BusinessRulesConfig, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Loads business rules from YAML file."""
        config_path = Path(__file__).parent / "business_rules.yaml"
        if not config_path.exists():
            # Fallback for local dev path differences if needed
            config_path = Path("config/business_rules.yaml")
            
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Loaded business rules from {config_path}")
            else:
                logger.warning(f"Business rules config not found at {config_path}, using defaults")
                self._config = {}
        except Exception as e:
            logger.error(f"Failed to load business rules config: {e}")
            self._config = {}

    @property
    def situation_thresholds(self) -> Dict[str, Any]:
        return self._config.get("situation_thresholds", {})
        
    @property
    def recommendation_rules(self) -> Dict[str, Any]:
        return self._config.get("recommendations", {})

# Global instance
business_rules = BusinessRulesConfig()
