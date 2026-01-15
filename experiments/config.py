"""
Experiment configuration constants.
"""
import os
from pathlib import Path

# Load .env file if available
try:
    from dotenv import load_dotenv
    # Try to load .env from project root (parent of experiments/)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
    else:
        # Fallback to default load_dotenv() behavior
        load_dotenv(override=False)
except ImportError:
    # python-dotenv not installed, skip
    pass

# Paths
EXPERIMENTS_DIR = Path(__file__).parent
DATA_DIR = EXPERIMENTS_DIR / "data" / "ndas"
ARTIFACTS_DIR = EXPERIMENTS_DIR / "artifacts"
RESULTS_DIR = EXPERIMENTS_DIR / "results"

# Dataset
NUM_PUBLIC_NDAS = 15
NUM_SYNTHETIC_NDAS = 15
TOTAL_DOCS = 30

# Run counts
RUNS_PER_DOC_EXP1 = 5
RUNS_PER_DOC_EXP2 = 10
STRESS_TEST_DOCS = 10

# LLM Baseline - load from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
BASELINE_MODEL = "gpt-4o-mini"  # Use cheaper model for experiments
BASELINE_TEMPERATURE = 0.7
BASELINE_MAX_TOKENS = 2000

# Output paths
HYBRID_ARTIFACTS = ARTIFACTS_DIR / "hybrid"
BASELINE_ARTIFACTS = ARTIFACTS_DIR / "baseline"
STRESS_ARTIFACTS = ARTIFACTS_DIR / "hybrid_stress"
