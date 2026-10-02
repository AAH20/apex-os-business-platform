"""Demo: Project lifecycle — create, tasks, resources, progress, report.

Run: python demos/demo_projects.py
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class Task:
    name: str
    assignee: "str | None" = None
    status: str = "todo"  # todo | in_progress | done
    progress: int = 0  # 0-100


@dataclass
class Project:
    name: str
    tasks: list = field(default_factory=list)

    def add_task(self, name: str) -> Task:
        task = Task(name=name)
        self.tasks.append(task)
        return task

    def assign(self, task_name: str, resource: str) -> bool:
        for t in self.tasks:
            if t.name == task_name:
                t.assignee = resource
                return True
        return False

    def update_progress(self, task_name: str, progress: int) -> bool:
        for t in self.tasks:
            if t.name == task_name:
                t.progress = max(0, min(100, progress))
                t.status = "done" if t.progress == 100 else "in_progress"
                return True
        return False

    @property
    def overall_progress(self) -> float:
        if not self.tasks:
            return 0.0
        return sum(t.progress for t in self.tasks) / len(self.tasks)

    def report(self) -> str:
        lines = [f"Project: {self.name}", f"Overall progress: {self.overall_progress:.0f}%", "-" * 40]
        for t in self.tasks:
            bar = "█" * (t.progress // 10) + "░" * (10 - t.progress // 10)
            lines.append(f"  [{bar}] {t.progress:3d}%  {t.status:11s}  {t.name}  → {t.assignee or 'unassigned'}")
        return "\n".join(lines)


def demo_create_project():
    print("=== 1. CREATE PROJECT ===")
    p = Project("Website Redesign")
    print(f"Created project: {p.name}")
    print()
    return p


def demo_add_tasks(p):
    print("=== 2. ADD TASKS ===")
    for name in ["Design mockups", "Implement frontend", "Write tests", "Deploy to staging"]:
        p.add_task(name)
        print(f"  + {name}")
    print(f"Total tasks: {len(p.tasks)}")
    print()


def demo_assign_resources(p):
    print("=== 3. ASSIGN RESOURCES ===")
    assignments = {
        "Design mockups": "Alice",
        "Implement frontend": "Bob",
        "Write tests": "Carol",
        "Deploy to staging": "Bob",
    }
    for task, person in assignments.items():
        p.assign(task, person)
        print(f"  {task} → {person}")
    print()


def demo_track_progress(p):
    print("=== 4. TRACK PROGRESS ===")
    updates = {
        "Design mockups": 100,
        "Implement frontend": 60,
        "Write tests": 30,
        "Deploy to staging": 0,
    }
    for task, pct in updates.items():
        p.update_progress(task, pct)
        print(f"  {task}: {pct}%")
    print()


def demo_generate_report(p):
    print("=== 5. GENERATE REPORT ===")
    print(p.report())
    print()


def main():
    print("APEX-OS Business Platform — Project Management Demo")
    print("=" * 50)
    print()
    p = demo_create_project()
    demo_add_tasks(p)
    demo_assign_resources(p)
    demo_track_progress(p)
    demo_generate_report(p)
    print("Demo complete.")


if __name__ == "__main__":
    main()
