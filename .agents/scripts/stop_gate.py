#!/usr/bin/env python3
"""Stop hook: prevent the agent from stopping when background tasks are running.

If `fullyIdle` is false (tasks still running), returns "continue" to keep
the agent loop alive. Also continues if the termination reason indicates
an error that might be recoverable.

Contract: Stop → input has executionNum, terminationReason, fullyIdle, error.
           Output: { "decision": "continue"|"stop", "reason": "..." }
"""
import json
import sys


# Reasons where we should NOT force continuation
TERMINAL_REASONS = {
    "USER_CANCELED",
    "MAX_TOKEN_BUDGET_EXCEEDED",
    "MAX_FORCED_INVOCATIONS",
    "TERMINAL_CUSTOM_HOOK",
}


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        print(json.dumps({"decision": "stop"}))
        return

    fully_idle = payload.get("fullyIdle", True)
    termination_reason = payload.get("terminationReason", "")
    execution_num = payload.get("executionNum", 0)

    # Never override user cancellation or hard limits
    if termination_reason in TERMINAL_REASONS:
        print(json.dumps({"decision": "stop"}))
        return

    # If background tasks are still running, keep going
    if not fully_idle:
        print(
            json.dumps(
                {
                    "decision": "continue",
                    "reason": (
                        "⏳ Background tasks are still running. "
                        "Waiting for completion before stopping."
                    ),
                }
            )
        )
        return

    # Safety: don't loop forever — cap forced continuations
    if execution_num > 10:
        print(
            json.dumps(
                {
                    "decision": "stop",
                    "reason": "Reached max execution count (10). Stopping.",
                }
            )
        )
        return

    # Normal completion — allow stop
    print(json.dumps({"decision": "stop"}))


if __name__ == "__main__":
    main()
