#!/usr/bin/env python3
"""PostToolUse hook: auto-check run_command exit codes.

Reads the tool call from stdin. If the command failed (error field present),
outputs an empty JSON object — the agent sees the error in the tool result
and auto-corrects. This hook exists to ensure the agent ALWAYS processes
errors rather than silently continuing.

Contract: PostToolUse → input has toolCall, stepIdx, error (optional).
           Output: empty JSON object {}.
"""
import json
import sys


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        # If we can't parse input, just pass through
        print(json.dumps({}))
        return

    error = payload.get("error", "")

    if error:
        # Log to stderr for diagnostics (agent won't see this, but it's
        # useful for debugging hooks themselves)
        tool_call = payload.get("toolCall", {})
        command = tool_call.get("args", {}).get("CommandLine", "<unknown>")
        print(
            f"[hook:auto-error-recovery] Command failed: {command!r} → {error}",
            file=sys.stderr,
        )

    # PostToolUse contract: always return empty object
    print(json.dumps({}))


if __name__ == "__main__":
    main()
