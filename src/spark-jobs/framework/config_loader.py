"""
Configuration loading from YAML files and AWS SSM Parameter Store.

Reads:
1. config/features.yaml — which tier and modules to run
2. config/tiers/{tier}.yaml — module mappings for that tier
3. SSM parameters — runtime overrides for symbols, thresholds, etc.

Exposes a ConfigLoader interface for the PipelineRunner and ModuleRegistry.
"""

from typing import Any


class ConfigLoader:
    """
    Loads and merges configuration from multiple sources.

    Configuration hierarchy (highest to lowest priority):
    1. SSM Parameter Store (runtime overrides)
    2. YAML tier configuration (config/tiers/{tier}.yaml)
    3. Base features configuration (config/features.yaml)
    """

    def __init__(self, config_path: str = "config/features.yaml"):
        """
        Initialize the config loader.

        Args:
            config_path: Path to features.yaml (relative to project root)
        """
        self.config_path = config_path
        self._config = None
        self._tier_config = None

    def load(self) -> dict[str, Any]:
        """
        Load configuration from all sources.

        Returns:
            Merged configuration dict
        """
        # TODO: Implement YAML loading
        # 1. Load config/features.yaml
        # 2. Extract feature_tier
        # 3. Load config/tiers/{tier}.yaml
        # 4. Check for SSM overrides (via Terraform SSM parameters)
        # 5. Merge and return
        pass

    def get_active_tier(self) -> str:
        """
        Get the active feature tier.

        Returns: One of "small", "medium", "large"
        """
        # TODO: Extract from config
        pass

    def get_active_modules(self) -> list[str]:
        """
        Get list of active module IDs.

        Returns:
            List of module IDs (e.g., ["MOD-001", "MOD-002", "MOD-003"])
        """
        # TODO: Extract from tier configuration
        pass

    def get_module_config(self, module_id: str) -> dict[str, Any]:
        """
        Get configuration for a specific module.

        Returns:
            Module-specific config (e.g., {"threshold": 2.5, "window_seconds": 60})
        """
        # TODO: Extract module config from merged config
        pass

    def get_symbols(self) -> list[str]:
        """
        Get list of trading symbols to monitor.

        Returns:
            List of symbols (e.g., ["btcusdt", "ethusdt", "solusdt"])
        """
        # TODO: Extract from config, with SSM override support
        pass

    def get_connectors(self) -> list[str]:
        """
        Get list of active exchange connectors.

        Returns:
            List of connector names (e.g., ["binance-ws", "coinbase-ws"])
        """
        # TODO: Extract from config
        pass
