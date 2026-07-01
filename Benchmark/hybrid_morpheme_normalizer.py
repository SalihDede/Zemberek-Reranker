"""
Hybrid backend aday string'lerini normalize eder.
Format: "kök+ek+ek [GRAMER ETİKETİ]"  →  "kök+ek+ek"
"""


def normalize(analysis: str) -> str:
    """'kök+ek+ek [...]' → 'kök+ek+ek' (köşeli parantezi soy)."""
    idx = analysis.rfind(' [')
    return analysis[:idx] if idx != -1 else analysis
