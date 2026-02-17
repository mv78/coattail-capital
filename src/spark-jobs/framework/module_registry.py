"""
Module registry for dynamic detector discovery and instantiation.

Reads the list of active modules from ConfigLoader and dynamically imports
and instantiates the corresponding detector classes. This enables:
- Config-driven feature toggles (no code changes to activate/deactivate modules)
- Plugin architecture (add new detectors without modifying the framework)
"""

from base_detector import BaseDetector
from config_loader import ConfigLoader


class ModuleRegistry:
    """
    Registry for dynamically loading and instantiating detectors.

    Maps module IDs to detector classes and manages lifecycle.
    """

    # Mapping of module ID to detector class path
    # This is the source of truth for available modules
    MODULE_MAPPING = {
        "MOD-001": "detectors.volume_anomaly.VolumeAnomalyDetector",
        "MOD-002": "detectors.whale_detector.WhaleDetector",
        "MOD-003": "detectors.spread_calculator.SpreadCalculator",
        "MOD-004": "detectors.wallet_scorer.WalletScorer",
        "MOD-005": "detectors.labeled_whales.LabeledWhalers",
        "MOD-006": "detectors.flow_direction.FlowDirection",
        "MOD-007": "detectors.consensus.ConsensusScorer",
        "MOD-008": "detectors.onchain_ingester.OnchainIngester",
        "MOD-009": "detectors.dex_tracker.DexTracker",
        "MOD-010": "detectors.predictive_scorer.PredictiveScorer",
        "MOD-011": "detectors.backtester.Backtester",
    }

    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize the registry.

        Args:
            config_loader: ConfigLoader instance (provides active module list)
        """
        self.config_loader = config_loader
        self._detectors: dict[str, BaseDetector] = {}

    def load_active_modules(self) -> dict[str, BaseDetector]:
        """
        Load and instantiate all active detectors.

        Reads the list of active modules from ConfigLoader, dynamically imports
        the corresponding detector classes, and instantiates them.

        Returns:
            Dict mapping module_id to detector instance
                {
                    "MOD-001": VolumeAnomalyDetector(),
                    "MOD-002": WhaleDetector(),
                    ...
                }

        Raises:
            ImportError: If detector class cannot be imported
            TypeError: If detector class doesn't inherit from BaseDetector
        """
        # TODO: Implement dynamic loading
        # 1. Get active modules from config_loader.get_active_modules()
        # 2. For each module_id in MODULE_MAPPING:
        #    - Import the detector class (use importlib)
        #    - Verify it inherits from BaseDetector
        #    - Instantiate it
        # 3. Return dict of instantiated detectors
        return {}

    def get_detector(self, module_id: str) -> BaseDetector:
        """
        Get a detector by module ID.

        Detectors are lazily loaded on first access.

        Args:
            module_id: Module ID (e.g., "MOD-001")

        Returns:
            BaseDetector instance

        Raises:
            KeyError: If module not in active set
            ImportError: If detector class cannot be imported
        """
        if module_id not in self._detectors:
            self._detectors[module_id] = self._load_single_module(module_id)
        return self._detectors[module_id]

    def _load_single_module(self, module_id: str) -> BaseDetector:
        """
        Dynamically load and instantiate a single detector.

        Args:
            module_id: Module ID (e.g., "MOD-001")

        Returns:
            BaseDetector instance

        Raises:
            KeyError: If module_id not in MODULE_MAPPING
            ImportError: If class import fails
        """
        # TODO: Implement single module loading
        # 1. Look up class path in MODULE_MAPPING
        # 2. Use importlib.import_module and getattr to load the class
        # 3. Instantiate with no arguments (or get __init__ signature)
        # 4. Return instance
        pass

    def list_active_modules(self) -> list[str]:
        """
        List all active module IDs.

        Returns:
            List of module IDs (e.g., ["MOD-001", "MOD-002", "MOD-003"])
        """
        return self.config_loader.get_active_modules()
