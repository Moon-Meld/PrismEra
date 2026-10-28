"""PrismEra Machine Learning & Alignment Subsystem.

Provides:
- Prism-AdmitNet: Admission probability prediction with feature attribution.
- LLM Fine-Tuning Suite: DPO / SFT dataset generators and LoRA training pipeline.
"""

from prismera.ml.admit_predictor import PrismAdmitPredictor, get_admit_predictor

__all__ = ["PrismAdmitPredictor", "get_admit_predictor"]
