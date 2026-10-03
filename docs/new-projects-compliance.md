# New Projects Compliance Guide

This document outlines the compliance requirements for new projects within the APEX-OS Business Platform. All new projects must adhere to the standards described below.

---

## 1. GDPR Compliance (General Data Protection Regulation)

**Scope:** Applies to any project processing personal data of EU/EEA residents.

### Key Requirements

- **Lawful Basis for Processing:** Every data-processing activity must have a documented lawful basis (consent, contract, legal obligation, vital interests, public task, or legitimate interests).
- **Data Minimization:** Collect only the data strictly necessary for the stated purpose.
- **Purpose Limitation:** Data collected for one purpose must not be repurposed without additional consent.
- **Right to Access:** Data subjects may request a copy of their personal data within 30 days.
- **Right to Erasure ("Right to be Forgotten"):** Data subjects may request deletion of their personal data.
- **Right to Rectification:** Data subjects may request correction of inaccurate data.
- **Right to Data Portability:** Data subjects may request their data in a structured, machine-readable format.
- **Privacy by Design & Default:** Data protection must be integrated into system architecture from the start.
- **Data Protection Impact Assessments (DPIAs):** Required for high-risk processing (e.g., large-scale profiling, sensitive data).
- **Breach Notification:** Report personal data breaches to the supervisory authority within 72 hours; notify affected data subjects without undue delay.
- **Data Processing Agreements (DPAs):** Required with any third-party processor handling personal data on your behalf.
- **Data Protection Officer (DPO):** Appoint a DPO if processing involves large-scale systematic monitoring or special categories of data.
- **Cross-Border Transfers:** Ensure adequate safeguards (Standard Contractual Clauses, Binding Corporate Rules) for transfers outside the EEA.

### Implementation Checklist

- [ ] Document lawful basis for each data-processing activity
- [ ] Implement consent management with granular opt-in/opt-out
- [ ] Build data subject access request (DSAR) workflows
- [ ] Encrypt personal data at rest and in transit
- [ ] Conduct DPIA before launching high-risk features
- [ ] Establish breach response and notification procedures
- [ ] Sign DPAs with all subprocessors
- [ ] Maintain Records of Processing Activities (ROPA)

---

## 2. CCPA Compliance (California Consumer Privacy Act)

**Scope:** Applies to for-profit businesses collecting personal information of California residents that meet specific thresholds (revenue, data volume, or data-sale percentage).

### Key Requirements

- **Right to Know:** Consumers may request disclosure of categories and specific pieces of personal information collected, sources, purposes, and third parties with whom it is shared.
- **Right to Delete:** Consumers may request deletion of personal information, subject to certain exceptions.
- **Right to Opt-Out of Sale:** Consumers may opt out of the sale of their personal information. A "Do Not Sell My Personal Information" link must be prominently displayed.
- **Right to Non-Discrimination:** Consumers exercising their rights must not be denied goods/services, charged different prices, or provided a different quality of service.
- **Notice at Collection:** Inform consumers at or before the point of collection about the categories of personal information to be collected and the purposes.
- **Service Provider Contracts:** Contracts with service providers must include specific CCPA-required provisions restricting use and sale of personal information.
- **Reasonable Security:** Implement and maintain reasonable security procedures and practices.
- **Sensitive Personal Information:** Consumers may limit the use and disclosure of sensitive personal information (e.g., SSN, financial account info, precise geolocation, racial/ethnic origin, religious beliefs, genetic data, biometric data, health data, sex life/orientation).

### Implementation Checklist

- [ ] Publish a compliant Privacy Policy with CCPA-specific disclosures
- [ ] Implement "Do Not Sell My Personal Information" mechanism
- [ ] Build consumer request (know/delete/opt-out) workflows
- [ ] Verify identity of consumers making requests
- [ ] Include CCPA-required provisions in service provider contracts
- [ ] Implement reasonable security measures
- [ ] Train staff on CCPA requirements and response procedures

---

## 3. HIPAA Compliance (Health Insurance Portability and Accountability Act)

**Scope:** Applies to Covered Entities (healthcare providers, health plans, healthcare clearinghouses) and their Business Associates that handle Protected Health Information (PHI).

### Key Requirements

- **Privacy Rule:** Protects the privacy of individually identifiable health information (PHI). Requires appropriate safeguards and limits on uses and disclosures.
- **Security Rule:** Requires administrative, physical, and technical safeguards for electronic PHI (ePHI):
  - **Administrative:** Security management process, assigned privacy/security officer, workforce training, contingency planning, evaluation.
  - **Physical:** Facility access controls, workstation security, device and media controls.
  - **Technical:** Access controls, audit controls, integrity controls, transmission security (encryption).
- **Breach Notification Rule:** Notify affected individuals, HHS, and (for large breaches) media within 60 days of discovery.
- **Business Associate Agreements (BAAs):** Required with any vendor that creates, receives, maintains, or transmits PHI on your behalf.
- **Minimum Necessary Standard:** Use, disclose, or request only the minimum PHI necessary to accomplish the intended purpose.
- **Patient Rights:** Individuals have rights to access, amend, and receive an accounting of disclosures of their PHI.

### Implementation Checklist

- [ ] Conduct a thorough risk analysis of all systems handling ePHI
- [ ] Implement administrative safeguards (policies, training, incident response)
- [ ] Implement physical safeguards (access controls, workstation policies)
- [ ] Implement technical safeguards (encryption, access controls, audit logs)
- [ ] Execute BAAs with all business associates
- [ ] Establish breach notification procedures
- [ ] Implement minimum-necessary access policies
- [ ] Provide patient rights mechanisms (access, amendment, accounting)
- [ ] Conduct regular security risk assessments

---

## 4. SOC 2 Compliance (System and Organization Controls 2)

**Scope:** Applies to service organizations that store, process, or transmit customer data. Based on the Trust Services Criteria (TSC).

### Trust Services Criteria

- **Security (Common Criteria):** Protection against unauthorized access, disclosure, and damage.
- **Availability:** Systems are available for operation and use as agreed.
- **Processing Integrity:** System processing is complete, accurate, timely, and authorized.
- **Confidentiality:** Information designated as confidential is protected as committed.
- **Privacy:** Personal information is collected, used, retained, disclosed, and disposed of in conformity with commitments.

### Key Requirements

- **Risk Assessment:** Identify and assess risks to the achievement of the organization's objectives.
- **Control Environment:** Establish governance, organizational structure, and assignment of authority and responsibility.
- **Communication & Information:** Ensure relevant information is identified, captured, and communicated.
- **Monitoring Activities:** Assess the quality of internal control performance over time.
- **Logical & Physical Access Controls:** Restrict logical and physical access to system components.
- **System Operations & Monitoring:** Monitor and manage system operations, including incident detection and response.
- **Change Management:** Control changes to infrastructure, data, software, and procedures.
- **Risk Mitigation:** Identify, select, and develop risk mitigation activities.
- **Vendor/Third-Party Management:** Monitor and manage third-party service providers.
- **Incident Response:** Detect, respond to, and recover from security incidents.
- **Business Continuity & Disaster Recovery:** Maintain operational resilience and recovery capabilities.

### Implementation Checklist

- [ ] Define the scope of the SOC 2 audit (which TSC criteria apply)
- [ ] Conduct a gap analysis against the Trust Services Criteria
- [ ] Document all policies and procedures
- [ ] Implement access controls (least privilege, MFA, role-based access)
- [ ] Establish logging and monitoring for all critical systems
- [ ] Develop and test incident response plans
- [ ] Implement change management processes
- [ ] Conduct vendor risk assessments
- [ ] Perform regular vulnerability scans and penetration tests
- [ ] Establish business continuity and disaster recovery plans
- [ ] Engage a licensed CPA firm for SOC 2 Type I or Type II audit

---

## 5. ISO 27001 Compliance (Information Security Management System)

**Scope:** Applicable to any organization seeking to establish, implement, maintain, and continually improve an Information Security Management System (ISMS).

### Key Requirements

- **Context of the Organization:** Understand internal and external issues, interested parties, and their requirements.
- **Leadership:** Top management must demonstrate leadership and commitment to the ISMS.
- **Planning:** Address risks and opportunities, set information security objectives, and plan to achieve them.
- **Support:** Provide resources, competence, awareness, communication, and documented information.
- **Operation:** Plan, implement, and control processes needed to meet information security requirements.
- **Performance Evaluation:** Monitor, measure, analyze, and evaluate information security performance and the effectiveness of the ISMS.
- **Improvement:** Address nonconformities, take corrective actions, and continually improve the ISMS.

### Annex A Controls (ISO 27001:2022 — 93 controls in 4 themes)

- **Organizational Controls (37):** Policies, roles, threat intelligence, information security in project management, asset management, access control, supplier relationships, incident management, business continuity, etc.
- **People Controls (8):** Screening, terms of employment, awareness training, disciplinary process, responsibilities after termination, confidentiality agreements, remote working, information security event reporting.
- **Technological Controls (34):** User endpoint devices, privileged access rights, information access restriction, authentication, capacity management, malware protection, technical vulnerability management, configuration management, data masking, data leakage prevention, monitoring activities, secure coding, secure development, etc.
- **Physical Controls (14):** Physical entry, securing offices/rooms/facilities, monitoring, physical security perimeters, secure areas, equipment maintenance, secure disposal, clear desk/clear screen, equipment siting and protection, security of assets off-premises, storage media, cabling security, etc.

### Implementation Checklist

- [ ] Define the ISMS scope and boundaries
- [ ] Conduct a risk assessment and treatment plan
- [ ] Develop a Statement of Applicability (SoA)
- [ ] Establish information security policies and objectives
- [ ] Implement controls from Annex A as identified in the risk treatment plan
- [ ] Conduct internal audits at planned intervals
- [ ] Perform management reviews of the ISMS
- [ ] Establish a continual improvement process
- [ ] Prepare for and undergo certification audit (Stage 1 and Stage 2)
- [ ] Maintain surveillance audits annually

---

## Cross-Cutting Requirements

All new projects must address the following regardless of specific regulatory framework:

| Requirement | Description |
|---|---|
| **Data Classification** | Classify data by sensitivity (public, internal, confidential, restricted) |
| **Encryption** | Encrypt data at rest (AES-256) and in transit (TLS 1.2+) |
| **Access Control** | Implement least-privilege, role-based access control (RBAC) with MFA |
| **Audit Logging** | Maintain comprehensive audit logs for all data access and modifications |
| **Data Retention** | Define and enforce data retention and secure deletion policies |
| **Incident Response** | Maintain a documented incident response plan with defined SLAs |
| **Vendor Management** | Assess and monitor third-party vendors for compliance alignment |
| **Training** | Conduct regular security and compliance training for all personnel |
| **Documentation** | Maintain up-to-date policies, procedures, and compliance records |
| **Testing** | Conduct regular vulnerability assessments and penetration tests |

---

## Project Onboarding Compliance Checklist

Before any new project goes live, the following must be completed:

- [ ] Data classification completed
- [ ] Applicable regulatory frameworks identified (GDPR, CCPA, HIPAA, SOC 2, ISO 27001)
- [ ] Privacy policy and/or notice updated
- [ ] Data processing agreements executed with all vendors
- [ ] Security controls implemented per framework requirements
- [ ] Access controls configured and tested
- [ ] Audit logging enabled and verified
- [ ] Data retention policy defined
- [ ] Incident response plan updated to include new project
- [ ] Compliance training completed for project team
- [ ] Risk assessment conducted and documented
- [ ] Sign-off from compliance/legal team obtained

---

*Last updated: 2026-10-02*
