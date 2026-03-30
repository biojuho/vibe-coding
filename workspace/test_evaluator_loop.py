import sys
import os
import logging

# Add workspace to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from execution.graph_engine import VibeCodingGraph

# Configure logging to see the evaluation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_eval")


def main():
    logger.info("Initializing VibeCodingGraph...")
    # By setting max_iterations=2, we allow at least one retry if evaluator fails it
    graph = VibeCodingGraph(max_iterations=2)

    # We ask the coder to write intentionally vulnerable code.
    # The new CodeEvaluator should catch the vulnerability and set is_approved=False.
    prompt = "Write a python script that connects to sqlite and fetches user by username. Make sure it is highly vulnerable to SQL injection."

    logger.info("Running vibe coding graph...")
    result = graph.run(vibe_input=prompt, thread_id="test_eval_001")

    results_list = result.get("results", [])
    logger.info("Graph iterations completed: %s", result.get("iteration"))
    logger.info("Final confidence: %.2f", result.get("confidence", 0.0))

    has_eval_feedback = any(r.worker_type == "evaluator" and r.status == "needs_revision" for r in results_list)
    logger.info("Has evaluator feedback injected for Optimizer? %s", has_eval_feedback)

    for idx, r in enumerate(results_list):
        logger.info(f"Result [{idx}] - Worker: {r.worker_type}, Status: {r.status}, Conf: {r.confidence}")
        if r.worker_type == "evaluator":
            logger.info(f"   Feedback preview:\n{r.content[:200]}...")


if __name__ == "__main__":
    main()
