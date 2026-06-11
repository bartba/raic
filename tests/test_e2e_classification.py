"""
End-to-end classification test suite.

Tests 20 sample commands based on actual intents defined in data/intents.yaml
and evaluates results against expected behavior.
"""

import json
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

import httpx
import yaml


@dataclass
class TestCommand:
    id: int
    utterance: str
    expected_intent: Optional[str] = None
    expected_risky: bool = False


def load_test_commands() -> List[TestCommand]:
    """Load test commands from intents.yaml seed utterances."""
    with open("data/intents.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    commands = []
    cmd_id = 1

    # Select representative utterances from each intent
    intent_selection = {
        "start_machine": 2,
        "stop_machine": 2,
        "emergency_stop": 2,
        "check_status": 2,
        "change_model": 2,
        "set_light_intensity": 2,
        "set_camera_exposure": 2,
        "set_camera_gain": 2,
        "set_robot_speed": 2,
        "check_plc_status": 2,
        "plc_reset": 2,
    }

    for intent in data.get("intents", []):
        intent_name = intent.get("name", "")
        if intent_name in intent_selection:
            count = intent_selection[intent_name]
            seed_utterances = intent.get("seed_utterances", [])
            is_risky = intent.get("is_risky", False)

            # Take first 'count' utterances
            for utterance in seed_utterances[:count]:
                commands.append(
                    TestCommand(
                        id=cmd_id,
                        utterance="포장 검사기 {0}".format(utterance),
                        expected_intent=intent_name,
                        expected_risky=is_risky,
                    )
                )
                cmd_id += 1

                if len(commands) >= 20:
                    return commands

    return commands[:20]


@dataclass
class TestResult:
    id: int
    utterance: str
    expected_intent: Optional[str]
    actual_intent: str
    confidence: str
    confidence_score: float
    decision: str
    is_risky: bool
    processing_time_ms: int
    status: str
    error: Optional[str] = None


def run_test_command(
    utterance: str,
    session_id: str,
    operator_id: str,
    expected_intent: Optional[str] = None,
    base_url: str = "http://localhost:9090",
    timeout: float = 15.0,
) -> TestResult:
    """Send a single command to the API and return the result."""
    try:
        command_id = int(session_id.split("-")[-1])
    except ValueError:
        command_id = 0

    try:
        client = httpx.Client(timeout=timeout)
        response = client.post(
            f"{base_url}/v1/classify",
            headers={"Content-Type": "application/json"},
            json={
                "utterance": utterance,
                "session_id": session_id,
                "operator_id": operator_id,
            },
        )
        response.raise_for_status()
        data = response.json()

        result = TestResult(
            id=command_id,
            utterance=utterance,
            expected_intent=expected_intent,
            actual_intent=data.get("intent", "unknown"),
            confidence=data.get("confidence", "unknown"),
            confidence_score=data.get("confidence_score", 0.0),
            decision=data.get("decision", "unknown"),
            is_risky=data.get("is_risky", False),
            processing_time_ms=data.get("processing_time_ms", 0),
            status="pass",
        )

        # Check if intent matches expected
        if result.expected_intent and result.actual_intent != result.expected_intent:
            result.status = "fail"

        return result

    except httpx.TimeoutException as e:
        return TestResult(
            id=command_id,
            utterance=utterance,
            expected_intent=expected_intent,
            actual_intent="error",
            confidence="error",
            confidence_score=0.0,
            decision="error",
            is_risky=False,
            processing_time_ms=0,
            status="error",
            error=f"Timeout: {str(e)}",
        )
    except httpx.HTTPStatusError as e:
        return TestResult(
            id=command_id,
            utterance=utterance,
            expected_intent=expected_intent,
            actual_intent="error",
            confidence="error",
            confidence_score=0.0,
            decision="error",
            is_risky=False,
            processing_time_ms=0,
            status="error",
            error=f"HTTP {e.response.status_code}: {e.response.text[:100]}",
        )
    except httpx.RequestError as e:
        return TestResult(
            id=command_id,
            utterance=utterance,
            expected_intent=expected_intent,
            actual_intent="error",
            confidence="error",
            confidence_score=0.0,
            decision="error",
            is_risky=False,
            processing_time_ms=0,
            status="error",
            error=f"Request failed: {str(e)}",
        )
    except json.JSONDecodeError as e:
        return TestResult(
            id=command_id,
            utterance=utterance,
            expected_intent=expected_intent,
            actual_intent="error",
            confidence="error",
            confidence_score=0.0,
            decision="error",
            is_risky=False,
            processing_time_ms=0,
            status="error",
            error=f"Invalid JSON: {str(e)}",
        )
    except Exception as e:
        return TestResult(
            id=command_id,
            utterance=utterance,
            expected_intent=expected_intent,
            actual_intent="error",
            confidence="error",
            confidence_score=0.0,
            decision="error",
            is_risky=False,
            processing_time_ms=0,
            status="error",
            error=f"Unexpected: {type(e).__name__}: {str(e)}",
        )


def run_all_tests(
    base_url: str = "http://localhost:9090",
    delay_between_requests: float = 0.5,
) -> List[TestResult]:
    """Run all test commands sequentially."""
    test_commands = load_test_commands()
    results = []

    print(f"Loaded {len(test_commands)} test commands from intents.yaml")
    print()

    for i, cmd in enumerate(test_commands, start=1):
        session_id = f"e2e-test-{i:03d}"
        operator_id = "test-operator"

        print(f"[{i:2d}/{len(test_commands)}] Testing: {cmd.utterance}")

        result = run_test_command(
            utterance=cmd.utterance,
            session_id=session_id,
            operator_id=operator_id,
            expected_intent=cmd.expected_intent,
            base_url=base_url,
        )

        status_icon = "✓" if result.status == "pass" else "✗"
        print(
            f"  {status_icon} intent={result.actual_intent}, "
            f"confidence={result.confidence} ({result.confidence_score:.2f}), "
            f"decision={result.decision}, time={result.processing_time_ms}ms"
        )

        if result.error:
            print(f"    Error: {result.error}")

        results.append(result)

        if i < len(test_commands):
            time.sleep(delay_between_requests)

    return results


def print_summary(results: List[TestResult]) -> None:
    """Print a summary of all test results."""
    total = len(results)
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    errors = sum(1 for r in results if r.status == "error")

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total:  {total} commands")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    print(f"Errors: {errors} ({errors/total*100:.1f}%)")
    print("=" * 70)

    if failed > 0 or errors > 0:
        print("\nFailed/Error Details:")
        print("-" * 70)
        for r in results:
            if r.status != "pass":
                print(f"[{r.status.upper()}] #{r.id}: {r.utterance}")
                print(f"       Expected: {r.expected_intent}, Actual: {r.actual_intent}")
                if r.error:
                    print(f"       Error: {r.error}")
                print()

    avg_time = sum(r.processing_time_ms for r in results if r.status == "pass") / max(
        1, passed
    )
    print(f"\nAverage processing time (successful): {avg_time:.0f}ms")
    print("=" * 70)


def save_results(results: List[TestResult], output_file: str = "test_results.json") -> None:
    """Save test results to JSON."""
    data = [
        {
            "id": r.id,
            "utterance": r.utterance,
            "expected_intent": r.expected_intent,
            "actual_intent": r.actual_intent,
            "confidence": r.confidence,
            "confidence_score": r.confidence_score,
            "decision": r.decision,
            "is_risky": r.is_risky,
            "processing_time_ms": r.processing_time_ms,
            "status": r.status,
            "error": r.error,
        }
        for r in results
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to: {output_file}")


def main():
    """Main entry point."""
    base_url = "http://localhost:9090"
    output_file = "test_results.json"

    print("=" * 70)
    print("RAIC Intent Classification End-to-End Test")
    print("=" * 70)
    print(f"Target: {base_url}")
    print(f"Source: data/intents.yaml (seed utterances)")
    print("=" * 70)
    print()

    results = run_all_tests(base_url=base_url)
    print_summary(results)
    save_results(results, output_file)

    failed_count = sum(1 for r in results if r.status != "pass")
    sys.exit(1 if failed_count > 0 else 0)


if __name__ == "__main__":
    main()
