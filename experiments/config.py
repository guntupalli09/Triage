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
DATA_BASE_DIR = EXPERIMENTS_DIR / "data"
DATA_DIR = DATA_BASE_DIR / "ndas"  # Default for backward compatibility
ARTIFACTS_DIR = EXPERIMENTS_DIR / "artifacts"
RESULTS_DIR = EXPERIMENTS_DIR / "results"

# Dataset - Multiple contract types (EXPANDED FOR 80%+ ACCEPTANCE)
NUM_PUBLIC_NDAS = 30  # Expanded from 15
NUM_SYNTHETIC_NDAS = 30  # Expanded from 15
NUM_SYNTHETIC_MSAS = 20  # Expanded from 5
NUM_SYNTHETIC_EMPLOYMENT = 20  # Expanded from 5
NUM_SYNTHETIC_LICENSING = 15  # NEW contract type
NUM_SYNTHETIC_PURCHASE = 15  # NEW contract type (for Phase 2)
TOTAL_DOCS = NUM_PUBLIC_NDAS + NUM_SYNTHETIC_NDAS  # 60 NDAs
TOTAL_DOCS_EXPANDED = TOTAL_DOCS + NUM_SYNTHETIC_MSAS + NUM_SYNTHETIC_EMPLOYMENT + NUM_SYNTHETIC_LICENSING  # 115 total (Phase 1)
TOTAL_DOCS_FULL = TOTAL_DOCS_EXPANDED + NUM_SYNTHETIC_PURCHASE  # 130 total (Phase 2)

# Contract type directories
NDA_DIR = DATA_BASE_DIR / "ndas"
MSA_DIR = DATA_BASE_DIR / "msas"
EMPLOYMENT_DIR = DATA_BASE_DIR / "employment"
LICENSING_DIR = DATA_BASE_DIR / "licensing"

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
