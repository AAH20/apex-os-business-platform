"""Expert finder engine."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from apex_os_bp.knowledge.models import Expert, ExpertiseLevel


class ExpertFinder:
    """Find experts by skills and availability."""

    def __init__(self):
        self._experts: Dict[str, Expert] = {}

    def add_expert(
        self,
        name: str,
        email: str,
        skills: Optional[List[str]] = None,
        expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE,
        department: str = "",
        available: bool = True,
        **kwargs,
    ) -> Expert:
        """Add an expert."""
        expert = Expert(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            skills=skills or [],
            expertise_level=expertise_level,
            department=department,
            available=available,
            **kwargs,
        )
        self._experts[expert.id] = expert
        return expert

    def get_expert(self, expert_id: str) -> Optional[Expert]:
        """Get expert by ID."""
        return self._experts.get(expert_id)

    def update_expert(self, expert_id: str, **kwargs) -> Optional[Expert]:
        """Update expert fields."""
        expert = self._experts.get(expert_id)
        if not expert:
            return None
        for key, value in kwargs.items():
            if hasattr(expert, key):
                setattr(expert, key, value)
        return expert

    def delete_expert(self, expert_id: str) -> bool:
        """Delete expert by ID."""
        if expert_id in self._experts:
            del self._experts[expert_id]
            return True
        return False

    def find_by_skill(self, skill: str, available_only: bool = True) -> List[Expert]:
        """Find experts by skill."""
        skill_lower = skill.lower()
        results = []
        for expert in self._experts.values():
            if available_only and not expert.available:
                continue
            for s in expert.skills:
                if skill_lower in s.lower():
                    results.append(expert)
                    break
        return results

    def find_by_skills(self, skills: List[str], match_all: bool = False, available_only: bool = True) -> List[Expert]:
        """Find experts by multiple skills."""
        if not skills:
            return []

        skill_set = set(s.lower() for s in skills)
        results = []

        for expert in self._experts.values():
            if available_only and not expert.available:
                continue
            expert_skills = set(s.lower() for s in expert.skills)
            if match_all:
                if skill_set.issubset(expert_skills):
                    results.append(expert)
            else:
                if skill_set & expert_skills:
                    results.append(expert)

        return results

    def find_by_department(self, department: str, available_only: bool = True) -> List[Expert]:
        """Find experts by department."""
        dept_lower = department.lower()
        results = []
        for expert in self._experts.values():
            if available_only and not expert.available:
                continue
            if dept_lower in expert.department.lower():
                results.append(expert)
        return results

    def find_by_expertise(self, level: ExpertiseLevel, available_only: bool = True) -> List[Expert]:
        """Find experts by expertise level."""
        results = []
        for expert in self._experts.values():
            if available_only and not expert.available:
                continue
            if expert.expertise_level == level:
                results.append(expert)
        return results

    def get_all_experts(self) -> List[Expert]:
        """Get all experts."""
        return list(self._experts.values())

    def get_available_experts(self) -> List[Expert]:
        """Get all available experts."""
        return [e for e in self._experts.values() if e.available]

    def count(self) -> int:
        """Get total expert count."""
        return len(self._experts)

    def all_skills(self) -> List[str]:
        """Get all unique skills."""
        skills: set = set()
        for expert in self._experts.values():
            skills.update(expert.skills)
        return list(skills)

    def all_departments(self) -> List[str]:
        """Get all unique departments."""
        return list(set(e.department for e in self._experts.values() if e.department))
