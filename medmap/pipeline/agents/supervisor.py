"""Supervisor: arbitrates between Schema Detective and Validation Agent.

Receives mapping proposals from the detective and validation challenges,
then makes final decisions: CONSENSUS (auto-accept), CONFLICT (escalate),
or UNCERTAIN (auto-escalate).
"""

import logging
from typing import Optional

from pipeline.agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Decision thresholds
CONSENSUS_THRESHOLD = 0.85   # Auto-accept if adjusted confidence >= this
CONFLICT_THRESHOLD = 0.50    # Escalate to human if below this
# Between CONFLICT and CONSENSUS = UNCERTAIN (auto-escalate)


def decide_mapping(mapping: dict) -> dict:
    """Make a supervisor decision on a single column mapping.

    Returns the mapping enriched with supervisor_decision and status.
    """
    confidence = mapping.get("adjusted_confidence", mapping.get("confidence", 0))
    validation = mapping.get("validation_result", "SKIP")
    target = mapping.get("target_column")

    result = {**mapping}

    # No target proposed
    if not target:
        result["supervisor_decision"] = "UNMAPPED"
        result["status"] = "REVIEW"
        result["supervisor_reasoning"] = "No target column proposed by detective"
        return result

    # Validation failed hard
    if validation == "FAIL":
        result["supervisor_decision"] = "CONFLICT"
        result["status"] = "CONFLICT"
        result["supervisor_reasoning"] = (
            f"Validation failed: {', '.join(mapping.get('validation_notes', []))}"
        )
        return result

    # High confidence + passed validation
    if confidence >= CONSENSUS_THRESHOLD and validation in ("PASS", "SKIP"):
        result["supervisor_decision"] = "CONSENSUS"
        result["status"] = "CONSENSUS"
        result["supervisor_reasoning"] = (
            f"High confidence ({confidence:.2f}) with validation {validation}"
        )
        return result

    # Low confidence
    if confidence < CONFLICT_THRESHOLD:
        result["supervisor_decision"] = "CONFLICT"
        result["status"] = "CONFLICT"
        result["supervisor_reasoning"] = (
            f"Low confidence ({confidence:.2f}) — needs human review"
        )
        return result

    # Middle ground: uncertain
    result["supervisor_decision"] = "UNCERTAIN"
    result["status"] = "UNCERTAIN"
    result["supervisor_reasoning"] = (
        f"Moderate confidence ({confidence:.2f}) with {validation} validation"
    )
    return result


class SupervisorAgent(BaseAgent):
    """Agent that arbitrates detective + validation results."""

    def __init__(self):
        super().__init__("Supervisor")

    def run(self, context: dict) -> AgentResult:
        """Make final decisions on all column mappings.

        Reads and updates context["column_mappings"].
        Writes context["agent_stats"] with summary.
        """
        mappings = context.get("column_mappings", [])
        if not mappings:
            return self._fail("No column mappings to supervise")

        decided = []
        consensus_count = 0
        conflict_count = 0
        uncertain_count = 0
        unmapped_count = 0

        for mapping in mappings:
            result = decide_mapping(mapping)
            decided.append(result)

            decision = result.get("supervisor_decision")
            if decision == "CONSENSUS":
                consensus_count += 1
            elif decision == "CONFLICT":
                conflict_count += 1
            elif decision == "UNCERTAIN":
                uncertain_count += 1
            elif decision == "UNMAPPED":
                unmapped_count += 1

        context["column_mappings"] = decided

        total = len(decided)
        context["agent_stats"] = {
            "total_columns": total,
            "auto_mapped": consensus_count,
            "conflicts": conflict_count,
            "escalated": uncertain_count + conflict_count,
            "unmapped": unmapped_count,
        }

        self.logger.info(
            "Supervisor: %d consensus, %d conflict, %d uncertain, %d unmapped (total %d)",
            consensus_count, conflict_count, uncertain_count, unmapped_count, total,
        )

        return self._ok(
            data=decided,
            total_columns=total,
            auto_mapped=consensus_count,
            conflicts=conflict_count,
            uncertain=uncertain_count,
            unmapped=unmapped_count,
        )
