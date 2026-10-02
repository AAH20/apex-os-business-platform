#!/usr/bin/env python3
"""Demo: Workflow creation, steps, execution, error handling, versioning."""

from dataclasses import dataclass, field
from typing import Any, Callable


# --- Core workflow engine ---

@dataclass
class Step:
    name: str
    action: Callable[[], Any]
    retries: int = 0


@dataclass
class Workflow:
    name: str
    version: int = 1
    steps: list[Step] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)

    def add_step(self, name: str, action: Callable[[], Any], retries: int = 0) -> "Workflow":
        self.steps.append(Step(name, action, retries))
        return self

    def execute(self) -> dict:
        results = {"workflow": self.name, "version": self.version, "steps": []}
        for step in self.steps:
            attempt = 0
            while True:
                try:
                    output = step.action()
                    results["steps"].append({"step": step.name, "status": "ok", "output": output})
                    break
                except Exception as exc:
                    attempt += 1
                    if attempt > step.retries:
                        results["steps"].append({"step": step.name, "status": "failed", "error": str(exc)})
                        results["status"] = "failed"
                        self.history.append(results)
                        return results
        results["status"] = "completed"
        self.history.append(results)
        return results

    def bump_version(self) -> "Workflow":
        self.version += 1
        return self


# --- Demo actions ---

def fetch_data() -> str:
    return "data: 42 records"


def transform_data() -> str:
    return "transformed: 42 rows"


def flaky_save() -> str:
    raise RuntimeError("connection timeout")


def save_data() -> str:
    return "saved to /tmp/output.csv"


# --- Demo runner ---

def main() -> None:
    print("=" * 50)
    print("1. CREATE WORKFLOW")
    wf = Workflow(name="etl-pipeline")
    print(f"   Created: {wf.name} (v{wf.version})")

    print("\n2. ADD STEPS")
    wf.add_step("fetch", fetch_data)
    wf.add_step("transform", transform_data)
    wf.add_step("save", save_data)
    for s in wf.steps:
        print(f"   + {s.name}")

    print("\n3. EXECUTE WORKFLOW")
    result = wf.execute()
    for entry in result["steps"]:
        print(f"   [{entry['status']}] {entry['step']}: {entry.get('output', entry.get('error'))}")
    print(f"   Overall: {result['status']}")

    print("\n4. HANDLE ERRORS (retry then fail)")
    wf2 = Workflow(name="flaky-job")
    wf2.add_step("risky-save", flaky_save, retries=2)
    result2 = wf2.execute()
    for entry in result2["steps"]:
        print(f"   [{entry['status']}] {entry['step']}: {entry.get('error')}")
    print(f"   Overall: {result2['status']}")

    print("\n5. VERSION WORKFLOW")
    print(f"   Before: v{wf.version}")
    wf.bump_version()
    print(f"   After:  v{wf.version}")
    print(f"   History entries: {len(wf.history)}")
    print("=" * 50)


if __name__ == "__main__":
    main()
