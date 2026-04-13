# backend/layers/layer2_scoring/voting_logic.py
"""
Layer 2.5: Decision Voting Logic
Combines 3 scoring channels into final severity decision
"""

from shared.enums import Severity
from shared.constants import (
    DECISION_CRITICAL_MATH_ML,
    DECISION_CRITICAL_STAT_ML,
    DECISION_WARNING_MATH,
    DECISION_WARNING_STAT,
    DECISION_WARNING_ML,
    DECISION_UNKNOWN_ML_MIN,
    DECISION_UNKNOWN_ML_MAX,
)
from shared.logger import setup_logger

logger = setup_logger(__name__)


class VotingEngine:
    """Layer 2.5: Decision Voting Logic"""
    
    @staticmethod
    def decide_severity(
        has_injection: bool,
        has_amsi_disable: bool,
        score_2a: float,
        score_2b: float,
        score_2c: float
    ) -> Severity:
        """
        Voting logic for severity decision.
        
        Inputs:
        - has_injection: INJECTED_INTO edge detected
        - has_amsi_disable: DISABLED_AMSI edge detected
        - score_2a: Math certainty (0.0-1.0)
        - score_2b: Statistical impossibility (0.0-1.0)
        - score_2c: ML graph anomaly (0.0-1.0)
        
        Output: BENIGN | UNKNOWN | WARNING | CRITICAL
        
        Logic:
        1. If injection → CRITICAL (instant)
        2. If AMSI disabled → CRITICAL (instant)
        3. If (2A high AND 2C high) → CRITICAL
        4. If ((2A OR 2B) high AND 2C medium) → CRITICAL
        5. If (2A alone high) → WARNING
        6. If (2B alone high) → WARNING
        7. If (2C high) → WARNING
        8. If (multiple moderate) → UNKNOWN
        9. If (single weak signal) → UNKNOWN
        10. Else → BENIGN
        """
        
        logger.debug(f"🤖 Voting: injection={has_injection}, amsi={has_amsi_disable}, 2A={score_2a:.2f}, 2B={score_2b:.2f}, 2C={score_2c:.2f}")
        
        # CRITICAL: Injection detected (instant)
        if has_injection:
            logger.warning("🔴 CRITICAL: Code injection detected")
            return Severity.CRITICAL
        
        # CRITICAL: AMSI disabled (instant)
        if has_amsi_disable:
            logger.warning("🔴 CRITICAL: AMSI disabled (tampering)")
            return Severity.CRITICAL
        
        # CRITICAL: Math AND ML high
        if score_2a > DECISION_CRITICAL_MATH_ML[0] and score_2c > DECISION_CRITICAL_MATH_ML[1]:
            logger.warning(f"🔴 CRITICAL: 2A={score_2a:.2f} AND 2C={score_2c:.2f} both high")
            return Severity.CRITICAL
        
        # CRITICAL: (Math OR Stats) AND ML high
        if (score_2a > DECISION_CRITICAL_STAT_ML[0] or score_2b > DECISION_CRITICAL_STAT_ML[0]) and score_2c > DECISION_CRITICAL_STAT_ML[1]:
            logger.warning(f"🔴 CRITICAL: (2A={score_2a:.2f} OR 2B={score_2b:.2f}) AND 2C={score_2c:.2f}")
            return Severity.CRITICAL
        
        # WARNING: Math signal alone
        if score_2a > DECISION_WARNING_MATH:
            logger.warning(f"🟡 WARNING: Math signal alone (2A={score_2a:.2f})")
            return Severity.WARNING
        
        # WARNING: Stats signal alone
        if score_2b > DECISION_WARNING_STAT:
            logger.warning(f"🟡 WARNING: Stats signal alone (2B={score_2b:.2f})")
            return Severity.WARNING
        
        # WARNING: ML high alone
        if score_2c > DECISION_WARNING_ML:
            logger.warning(f"🟡 WARNING: ML signal alone (2C={score_2c:.2f})")
            return Severity.WARNING
        
        # UNKNOWN: Multiple moderate signals
        high_signals = sum([
            1 for s in [score_2a, score_2b, score_2c]
            if s > 0.5
        ])
        if high_signals >= 2:
            logger.info(f"🟠 UNKNOWN: {high_signals} moderate signals")
            return Severity.UNKNOWN
        
        # UNKNOWN: Some signal detected (but weak)
        if any(s > DECISION_UNKNOWN_ML_MIN for s in [score_2a, score_2b, score_2c]):
            logger.info(f"🟠 UNKNOWN: Weak signal detected")
            return Severity.UNKNOWN
        
        # BENIGN: No signals
        logger.info("🟢 BENIGN: No anomaly detected")
        return Severity.BENIGN
    
    @staticmethod
    def calculate_confidence(score_2a: float, score_2b: float, score_2c: float) -> float:
        """
        Calculate overall confidence in the decision.
        
        Args:
            score_2a, score_2b, score_2c: Individual channel scores
            
        Returns:
            Confidence 0.0-1.0
        """
        try:
            # Simple: average of all 3 channels
            confidence = (score_2a + score_2b + score_2c) / 3
            
            # Boost confidence if multiple channels agree
            signals = sum([1 for s in [score_2a, score_2b, score_2c] if s > 0.6])
            if signals >= 2:
                confidence = min(confidence * 1.2, 1.0)  # +20% if 2+ channels agree
            
            logger.debug(f"📊 Confidence: {confidence:.2f}")
            return confidence
        
        except Exception as e:
            logger.error(f"❌ Failed to calculate confidence: {e}")
            return 0.0