"""Compatibility exports for the draft generation stage."""

from pipeline.process_stages.generate_review_stage import run_generate_review_stage as run_generate_stage

__all__ = ["run_generate_stage"]
