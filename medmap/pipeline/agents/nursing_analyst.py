"""Nursing Analyst: NLP analysis of nursing notes (BONUS).

Delegates to pipeline/nlp.py for text extraction.
Groups results by patient and adds to pipeline context.
"""

import logging

from pipeline.agents.base_agent import BaseAgent, AgentResult
from pipeline.nlp import NursingNLPAnalyzer

logger = logging.getLogger(__name__)


class NursingAnalystAgent(BaseAgent):
    """Agent that runs NLP extraction on all nursing note DataFrames."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        super().__init__("NursingAnalyst")
        self.analyzer = NursingNLPAnalyzer(model_name=model_name)

    def run(self, context: dict) -> AgentResult:
        """Run NLP analysis on nursing DataFrames in context.

        Reads context["dataframes"], writes context["nlp_results"].
        """
        dataframes = context.get("dataframes", {})
        if not dataframes:
            return self._fail("No dataframes in context")

        try:
            grouped = self.analyzer.analyze_all(dataframes)
            stats = self.analyzer.get_summary_stats(grouped)

            # Store in context
            context["nlp_results"] = grouped

            self.logger.info(
                "NLP analysis complete: %d notes, %d patients, %.1f%% extraction rate",
                stats["total_notes_analyzed"],
                stats["total_patients"],
                stats["extraction_rate"],
            )

            return self._ok(
                data=grouped,
                total_notes=stats["total_notes_analyzed"],
                total_patients=stats["total_patients"],
                pain_extracted=stats["pain_extracted"],
                mobility_extracted=stats["mobility_extracted"],
                wound_extracted=stats["wound_extracted"],
                deterioration_flagged=stats["deterioration_flagged"],
                extraction_rate=stats["extraction_rate"],
            )

        except Exception as e:
            self.logger.error("NLP analysis failed: %s", e, exc_info=True)
            return self._fail(str(e))
