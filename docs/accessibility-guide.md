# Accessibility Guide

## 1. Accessibility Standards

- **WCAG 2.2** (Web Content Accessibility Guidelines) — primary standard
- **Section 508** — US federal requirement
- **EN 301 549** — European accessibility standard
- **ADA Title III** — US civil rights law
- **ARIA 1.2** — Accessible Rich Internet Applications

Core principles (POUR): Perceivable, Operable, Understandable, Robust.

## 2. WCAG Compliance

Target conformance: **WCAG 2.2 Level AA**.

| Criterion | Level | Requirement |
|-----------|-------|-------------|
| 1.1.1 Text Alternatives | A | All non-text content has text alternatives |
| 1.3.1 Info and Relationships | A | Structure conveyed programmatically |
| 1.4.3 Contrast (Minimum) | AA | 4.5:1 text, 3:1 large text |
| 1.4.4 Resize Text | AA | 200% zoom without loss of function |
| 1.4.10 Reflow | AA | No two-column layout at 320px width |
| 1.4.11 Non-text Contrast | AA | 3:1 for UI components and graphics |
| 2.1.1 Keyboard | A | All functionality via keyboard |
| 2.1.2 No Keyboard Trap | A | Focus can be moved away |
| 2.4.3 Focus Order | A | Logical navigation sequence |
| 2.4.6 Headings and Labels | AA | Descriptive headings and labels |
| 2.4.7 Focus Visible | AA | Visible focus indicator |
| 2.5.3 Label in Name | A | Accessible name contains visible label |
| 3.1.1 Language of Page | A | Page language declared |
| 3.2.1 On Focus | A | No context change on focus |
| 3.3.1 Error Identification | A | Errors identified in text |
| 3.3.3 Error Suggestion | AA | Suggestions for correction |
| 4.1.2 Name, Role, Value | A | Programmatic name/role/state |

## 3. Testing Procedures

### Automated Testing
- Run **axe-core** in CI pipeline on every PR
- **Lighthouse** accessibility audit (target score ≥ 90)
- **WAVE** browser extension for manual spot checks
- **Pa11y** for automated regression testing

### Manual Testing
- Keyboard-only navigation (Tab, Shift+Tab, Enter, Space, Arrow keys)
- Screen reader testing (NVDA, JAWS, VoiceOver)
- Zoom to 200% and 400% — verify no content loss
- Color contrast verification with **Stark** or **Colour Contrast Analyser**
- Reduced motion preference testing
- Touch target size verification (minimum 44×44px)

### User Testing
- Include users with disabilities in usability studies
- Test with assistive technologies in real workflows
- Collect feedback via accessible forms

### Test Checklist
- [ ] All images have alt text
- [ ] Form inputs have associated labels
- [ ] Focus indicators visible
- [ ] Color is not sole means of conveying information
- [ ] Tables have proper headers
- [ ] Links have descriptive text
- [ ] Videos have captions and transcripts
- [ ] Animations respect `prefers-reduced-motion`
- [ ] No keyboard traps
- [ ] Error messages are descriptive and announced

## 4. Remediation Strategies

### Critical (Fix Immediately)
- Missing alt text on informative images
- Missing form labels
- Keyboard traps
- Insufficient color contrast
- Missing page language declaration

### High Priority (Fix in Current Sprint)
- Missing ARIA landmarks and roles
- Inaccessible custom components
- Missing focus management in modals/dialogs
- Inaccessible data tables
- Missing captions on videos

### Medium Priority (Fix in Next Sprint)
- Improper heading hierarchy
- Non-descriptive link text
- Missing skip navigation links
- Inaccessible PDFs
- Complex gestures without alternatives

### Low Priority (Backlog)
- Enhanced screen reader announcements
- Advanced ARIA patterns
- User preference customization

### Remediation Workflow
1. Identify issue via automated or manual testing
2. Classify severity (critical/high/medium/low)
3. Assign owner and target sprint
4. Fix using accessible patterns
5. Verify fix with automated + manual testing
6. Document resolution

## 5. Tools and Resources

### Automated Tools
| Tool | Purpose |
|------|---------|
| axe-core | Automated accessibility testing |
| Lighthouse | Auditing (Chrome DevTools) |
| WAVE | Visual accessibility evaluation |
| Pa11y | CLI automated testing |
| jest-axe | Jest integration for axe-core |

### Browser Extensions
- **axe DevTools** — Chrome/Firefox
- **WAVE** — Chrome/Firefox
- **Stark** — Contrast and accessibility
- **Accessibility Insights** — Microsoft

### Screen Readers
- **NVDA** — Windows (free)
- **JAWS** — Windows (commercial)
- **VoiceOver** — macOS/iOS (built-in)
- **TalkBack** — Android (built-in)

### Color and Contrast
- **Colour Contrast Analyser** — Desktop app
- **Stark** — Figma/Sketch plugin
- **WebAIM Contrast Checker** — Online

### Documentation
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [MDN Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [A11y Project](https://www.a11yproject.com/)
- [WebAIM](https://webaim.org/)

### Design Resources
- **Inclusive Design Principles** — University of Cambridge
- **A11y Project Checklist** — Practical checklist
- **GOV.UK Design System** — Accessible component patterns
- **Material Design Accessibility** — Google's guidelines
