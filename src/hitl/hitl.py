"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 12: Confidence Router
  TODO 13: Design 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# TODO 12: Implement ConfidenceRouter
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        # 1. High-risk action → always escalate regardless of confidence
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action '{action_type}' requires mandatory human approval",
                priority="high",
                requires_human=True,
            )

        # 2. High confidence → auto-send, human reviews asynchronously
        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason=f"High confidence ({confidence:.2f}) — approved automatically",
                priority="low",
                requires_human=False,
            )

        # 3. Medium confidence → queue for human review before sending
        if confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason=f"Medium confidence ({confidence:.2f}) — queued for human approval",
                priority="normal",
                requires_human=True,
            )

        # 4. Low confidence → escalate immediately
        return RoutingDecision(
            action="escalate",
            confidence=confidence,
            reason=f"Low confidence ({confidence:.2f}) — human makes final decision",
            priority="high",
            requires_human=True,
        )


# ============================================================
# TODO 13: Design 3 HITL decision points
#
# For each decision point, define:
# - trigger: What condition activates this HITL check?
# - hitl_model: Which model? (human-in-the-loop, human-on-the-loop,
#   human-as-tiebreaker)
# - context_needed: What info does the human reviewer need?
# - example: A concrete scenario
#
# Think about real banking scenarios where human judgment is critical.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "Large Transfer to New Recipient",
        "trigger": (
            "action = transfer_money AND amount > 50,000,000 VND "
            "AND recipient NOT in customer's saved contact list"
        ),
        "hitl_model": "human-in-the-loop",
        "context_needed": (
            "Transaction amount, sender account balance, recipient name & account, "
            "customer transaction history (last 30 days), real-time fraud risk score"
        ),
        "example": (
            "Customer requests a 200M VND transfer to an unknown account number. "
            "Agent proposes but human officer must approve before executing."
        ),
    },
    {
        "id": 2,
        "name": "Suspicious Personal Info Update",
        "trigger": (
            "action = update_personal_info AND "
            "(failed_logins_last_24h >= 3 OR device_trust_score < 0.5)"
        ),
        "hitl_model": "human-as-tiebreaker",
        "context_needed": (
            "Customer ID, last 5 login attempts (timestamp, IP, device), "
            "current vs. requested personal info diff, account creation date"
        ),
        "example": (
            "After 4 failed logins, customer asks to change phone number to an "
            "unrecognized device. Human security officer makes final call."
        ),
    },
    {
        "id": 3,
        "name": "Low-Confidence Policy / Loan Answer",
        "trigger": (
            "confidence_score < 0.70 AND "
            "intent in {loan_eligibility, interest_rate_policy, regulatory_question}"
        ),
        "hitl_model": "human-on-the-loop",
        "context_needed": (
            "Customer question, agent's draft answer, confidence score, "
            "relevant policy document excerpts, customer account tier"
        ),
        "example": (
            "Agent answers a loan eligibility question with 0.58 confidence. "
            "Answer is sent immediately but flagged for async human review within 30 min."
        ),
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
