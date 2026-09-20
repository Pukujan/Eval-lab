import asyncio
import json

from eval_lab.jev import evaluate_jev


async def main() -> None:
    result = await evaluate_jev(
        state=(
            "User question: What is 2 + 2?\n"
            "Candidate answer: 5"
        ),
        questions={
            "is_correct": {
                "type": "noul",
                "instructions": "Is the candidate answer correct for the user question?",
            },
            "verdict": {
                "type": "choice",
                "instructions": "Classify the candidate answer.",
                "criteria": {
                    "pass": "The answer is correct.",
                    "fail": "The answer is materially incorrect.",
                },
            },
        },
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
