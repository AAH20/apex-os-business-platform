"""Lead nurturing and scoring engine."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.marketing.models import (
    EmailTemplate,
    Lead,
    LeadEnrollment,
    LeadStatus,
    NurtureSequence,
    NurtureStep,
)


class LeadNurturingEngine:
    """Lead nurturing with sequences, scoring, and enrollment."""

    SCORE_OPEN = 1.0
    SCORE_CLICK = 3.0
    SCORE_CONVERSION = 10.0
    SCORE_UNSUBSCRIBE = -5.0

    def __init__(self):
        self._leads: Dict[str, Lead] = {}
        self._sequences: Dict[str, NurtureSequence] = {}
        self._enrollments: Dict[str, LeadEnrollment] = {}

    def create_lead(
        self,
        name: str,
        email: str,
        source: str = "",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> Lead:
        """Create a new lead."""
        lead = Lead(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            source=source,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._leads[lead.id] = lead
        return lead

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get lead by ID."""
        return self._leads.get(lead_id)

    def update_lead_score(self, lead_id: str, points: float) -> None:
        """Update lead score by adding points."""
        lead = self._leads.get(lead_id)
        if not lead:
            raise ValueError(f"Lead not found: {lead_id}")
        lead.score += points
        lead.last_activity = datetime.now()

    def track_engagement(self, lead_id: str, event_type: str) -> None:
        """Track lead engagement and update score."""
        lead = self._leads.get(lead_id)
        if not lead:
            raise ValueError(f"Lead not found: {lead_id}")

        if event_type == "open":
            self.update_lead_score(lead_id, self.SCORE_OPEN)
        elif event_type == "click":
            self.update_lead_score(lead_id, self.SCORE_CLICK)
        elif event_type == "conversion":
            self.update_lead_score(lead_id, self.SCORE_CONVERSION)
            lead.status = LeadStatus.CONVERTED
        elif event_type == "unsubscribe":
            self.update_lead_score(lead_id, self.SCORE_UNSUBSCRIBE)
        else:
            raise ValueError(f"Unknown event type: {event_type}")

        if lead.score >= 10 and lead.status == LeadStatus.NEW:
            lead.status = LeadStatus.ENGAGED
        if lead.score >= 20 and lead.status in (LeadStatus.NEW, LeadStatus.ENGAGED):
            lead.status = LeadStatus.QUALIFIED

    def create_sequence(self, name: str, metadata: Optional[Dict] = None) -> NurtureSequence:
        """Create a new nurture sequence."""
        sequence = NurtureSequence(
            id=str(uuid.uuid4()),
            name=name,
            metadata=metadata or {},
        )
        self._sequences[sequence.id] = sequence
        return sequence

    def add_step_to_sequence(
        self,
        sequence_id: str,
        email_template: EmailTemplate,
        delay_days: int = 0,
        condition: Optional[str] = None,
    ) -> NurtureStep:
        """Add a step to a nurture sequence."""
        sequence = self._sequences.get(sequence_id)
        if not sequence:
            raise ValueError(f"Sequence not found: {sequence_id}")

        step = NurtureStep(
            id=str(uuid.uuid4()),
            sequence_id=sequence_id,
            email_template=email_template,
            delay_days=delay_days,
            condition=condition,
            order=len(sequence.steps),
        )
        sequence.steps.append(step)
        return step

    def enroll_lead(self, lead_id: str, sequence_id: str) -> LeadEnrollment:
        """Enroll a lead in a nurture sequence."""
        if lead_id not in self._leads:
            raise ValueError(f"Lead not found: {lead_id}")
        if sequence_id not in self._sequences:
            raise ValueError(f"Sequence not found: {sequence_id}")

        enrollment = LeadEnrollment(
            id=str(uuid.uuid4()),
            lead_id=lead_id,
            sequence_id=sequence_id,
        )
        self._enrollments[enrollment.id] = enrollment
        return enrollment

    def process_enrollments(self) -> List[Dict]:
        """Process all active enrollments and send due emails."""
        results = []
        now = datetime.now()

        for enrollment in self._enrollments.values():
            if enrollment.status != "active":
                continue

            sequence = self._sequences.get(enrollment.sequence_id)
            if not sequence or not sequence.steps:
                continue

            if enrollment.current_step >= len(sequence.steps):
                enrollment.status = "completed"
                continue

            step = sequence.steps[enrollment.current_step]

            if enrollment.last_sent_at:
                next_send_time = enrollment.last_sent_at + timedelta(days=step.delay_days)
                if now < next_send_time:
                    continue

            enrollment.current_step += 1
            enrollment.last_sent_at = now

            if enrollment.current_step >= len(sequence.steps):
                enrollment.status = "completed"

            results.append(
                {
                    "enrollment_id": enrollment.id,
                    "lead_id": enrollment.lead_id,
                    "sequence_id": sequence.id,
                    "step_sent": step.id,
                    "step_order": step.order,
                    "status": enrollment.status,
                }
            )

        return results

    def get_lead_journey(self, lead_id: str) -> List[Dict]:
        """Get the nurture journey for a lead."""
        journeys = []
        for enrollment in self._enrollments.values():
            if enrollment.lead_id != lead_id:
                continue
            sequence = self._sequences.get(enrollment.sequence_id)
            journeys.append(
                {
                    "enrollment_id": enrollment.id,
                    "sequence_name": sequence.name if sequence else "Unknown",
                    "current_step": enrollment.current_step,
                    "total_steps": len(sequence.steps) if sequence else 0,
                    "status": enrollment.status,
                    "enrolled_at": enrollment.enrolled_at.isoformat(),
                }
            )
        return journeys

    def list_leads(
        self,
        status: Optional[LeadStatus] = None,
        min_score: Optional[float] = None,
    ) -> List[Lead]:
        """List leads with optional filters."""
        leads = list(self._leads.values())
        if status:
            leads = [lead for lead in leads if lead.status == status]
        if min_score is not None:
            leads = [lead for lead in leads if lead.score >= min_score]
        return leads

    def get_lead_score(self, lead_id: str) -> float:
        """Get the current score of a lead."""
        lead = self._leads.get(lead_id)
        if not lead:
            raise ValueError(f"Lead not found: {lead_id}")
        return lead.score
