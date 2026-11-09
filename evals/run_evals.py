from dataclasses import dataclass

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from app.ai.decide import decide_async
from app.ai.schemas import Decision
from evals.golden_emails import GOLDEN_EMAILS


@dataclass
class SectionMatches(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return ctx.output.section == ctx.expected_output["section"]


@dataclass
class ActionMatches(Evaluator):
    def evaluate(self, ctx: EvaluatorContext) -> bool:
        return ctx.output.action == ctx.expected_output["action"]


# Async, so every case runs on one event loop. A sync task runs each case in its own thread
# with its own loop, and the agents' shared connections then fail with ModelConnectionError.
async def run_pipeline(email: str) -> Decision:
    return await decide_async(email)


dataset = Dataset(
    name="golden-emails",
    cases=[
        Case(
            name=case["name"],
            inputs=case["email"],
            expected_output={"section": case["section"], "action": case["action"]},
        )
        for case in GOLDEN_EMAILS
    ],
    evaluators=[SectionMatches(), ActionMatches()],
)

if __name__ == "__main__":
    report = dataset.evaluate_sync(run_pipeline, max_concurrency=4)
    report.print(include_input=False, include_output=True, include_durations=False)