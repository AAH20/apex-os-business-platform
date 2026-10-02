# APEX-OS UI/UX Guidelines

## 1. Design Principles

- **Clarity over cleverness** — every element must communicate its purpose instantly.
- **Consistency** — identical patterns, spacing, and terminology across all modules.
- **Progressive disclosure** — show only what is needed; hide advanced options behind expandable sections.
- **Feedback loops** — every action produces visible feedback (loading, success, error states).
- **Minimal cognitive load** — limit choices per view; group related items; use familiar mental models.
- **Mobile-first** — design for small screens first, then scale up.
- **Dark-mode ready** — all components must work in both light and dark themes.

## 2. Color Palette

### Primary
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-primary` | `#2563EB` | Primary actions, links, active states |
| `--color-primary-hover` | `#1D4ED8` | Hover state for primary elements |
| `--color-primary-light` | `#DBEAFE` | Subtle backgrounds, highlights |

### Secondary
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-secondary` | `#7C3AED` | Secondary actions, accents |
| `--color-secondary-light` | `#EDE9FE` | Secondary backgrounds |

### Neutral
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-bg-primary` | `#FFFFFF` | Main background (light) / `#0F172A` (dark) |
| `--color-bg-secondary` | `#F8FAFC` | Card/panel background (light) / `#1E293B` (dark) |
| `--color-bg-tertiary` | `#F1F5F9` | Subtle fills (light) / `#334155` (dark) |
| `--color-text-primary` | `#0F172A` | Headings, body text (light) / `#F8FAFC` (dark) |
| `--color-text-secondary` | `#475569` | Captions, metadata (light) / `#94A3B8` (dark) |
| `--color-text-muted` | `#94A3B8` | Placeholders, disabled (light) / `#64748B` (dark) |
| `--color-border` | `#E2E8F0` | Borders, dividers (light) / `#334155` (dark) |

### Semantic
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-success` | `#16A34A` | Success states, confirmations |
| `--color-warning` | `#F59E0B` | Warnings, pending states |
| `--color-error` | `#DC2626` | Errors, destructive actions |
| `--color-info` | `#0891B2` | Informational messages |

## 3. Typography

### Font Stack
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
```

### Scale (1.25 ratio — Major Third)
| Token | Size | Line Height | Weight | Usage |
|-------|------|-------------|--------|-------|
| `--text-xs` | 12px | 16px | 400 | Captions, badges |
| `--text-sm` | 14px | 20px | 400 | Secondary text, table cells |
| `--text-base` | 16px | 24px | 400 | Body text |
| `--text-lg` | 18px | 28px | 500 | Lead paragraphs |
| `--text-xl` | 20px | 28px | 500 | Section headings |
| `--text-2xl` | 24px | 32px | 600 | Page headings |
| `--text-3xl` | 30px | 36px | 600 | Hero headings |
| `--text-4xl` | 36px | 40px | 700 | Display headings |

### Rules
- Maximum line length: 75 characters for body text.
- Minimum line height: 1.5× font size for readability.
- Use font weight 400–700 only; avoid thin weights below 400.
- Monospace for code, IDs, and numeric data.

## 4. Component Patterns

### Buttons
- **Primary**: filled `--color-primary`, white text, 8px radius, 40px height.
- **Secondary**: outlined, `--color-border` border, `--color-text-primary` text.
- **Ghost**: no border, transparent background, `--color-primary` text.
- **Destructive**: `--color-error` background, white text.
- **Sizes**: sm (32px), md (40px), lg (48px).
- **States**: default, hover (darken 10%), active (darken 15%), disabled (opacity 50%, no pointer).

### Forms
- Labels above inputs, 14px, weight 500, `--color-text-primary`.
- Inputs: 8px radius, 1px `--color-border`, 40px height, 16px padding.
- Focus ring: 2px `--color-primary` with 2px offset.
- Error state: `--color-border` → `--color-error`, error message below in `--color-error`.
- Placeholder: `--color-text-muted`.

### Cards
- Background: `--color-bg-secondary`, 12px radius, 1px `--color-border`.
- Padding: 24px (desktop), 16px (mobile).
- Shadow: `0 1px 3px rgba(0,0,0,0.08)` (light) / `0 1px 3px rgba(0,0,0,0.3)` (dark).
- Hover: subtle lift `translateY(-2px)` with transition 200ms.

### Navigation
- Sidebar: 240px wide (collapsible to 64px), `--color-bg-secondary`.
- Top bar: 56px height, breadcrumb + user menu.
- Active item: `--color-primary-light` background, `--color-primary` text.
- Icons: 20px, paired with 14px labels.

### Tables
- Header: `--color-bg-tertiary`, 14px, weight 600, uppercase.
- Rows: 48px height, 1px `--color-border` dividers.
- Hover: `--color-bg-tertiary` background.
- Numeric columns: right-aligned, monospace font.
- Sticky header on scroll.

### Modals
- Overlay: `rgba(0,0,0,0.5)` backdrop.
- Container: `--color-bg-primary`, 12px radius, max-width 560px.
- Header: 20px title, close button top-right.
- Footer: right-aligned action buttons, 16px gap.

### Badges / Tags
- 12px font, 4px vertical / 8px horizontal padding, 999px radius.
- Variants: neutral, success, warning, error, info.

## 5. Accessibility Guidelines

- **WCAG 2.1 AA compliance** minimum for all components.
- **Color contrast**: 4.5:1 for body text, 3:1 for large text (18px+ or 14px bold).
- **Focus indicators**: visible 2px outline on all interactive elements; never remove without replacement.
- **Keyboard navigation**: all interactive elements reachable via Tab; logical order matching visual layout.
- **ARIA labels**: icon-only buttons must have `aria-label`; decorative icons get `aria-hidden="true"`.
- **Form accessibility**: every input has an associated `<label>`; errors linked via `aria-describedby`.
- **Screen reader support**: use semantic HTML (`<nav>`, `<main>`, `<article>`); avoid div-soup.
- **Motion**: respect `prefers-reduced-motion`; disable animations for users who opt out.
- **Touch targets**: minimum 44×44px for all interactive elements.
- **Alt text**: all images must have descriptive alt text or empty alt if decorative.

## 6. Responsive Design Rules

### Breakpoints
| Token | Width | Target |
|-------|-------|--------|
| `--bp-sm` | 640px | Large phones |
| `--bp-md` | 768px | Tablets |
| `--bp-lg` | 1024px | Laptops |
| `--bp-xl` | 1280px | Desktops |
| `--bp-2xl` | 1536px | Large screens |

### Layout Rules
- **Container**: max-width 1280px, centered, 24px horizontal padding (16px on mobile).
- **Grid**: 12-column grid on desktop, 8-column on tablet, 4-column on mobile.
- **Sidebar**: hidden below 768px; replaced by bottom nav or hamburger menu.
- **Tables**: horizontal scroll below 768px; or transform to card layout.
- **Modals**: full-screen on mobile, centered on desktop.
- **Typography**: scale down one step on mobile (e.g., `--text-3xl` → `--text-2xl`).

### Spacing Scale (8px base)
| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Tight gaps, icon-to-text |
| `--space-2` | 8px | Inline element gaps |
| `--space-3` | 12px | Compact component padding |
| `--space-4` | 16px | Default component padding |
| `--space-6` | 24px | Section padding |
| `--space-8` | 32px | Large section gaps |
| `--space-12` | 48px | Page-level spacing |

### Interaction Rules
- Hover states only on devices with fine pointer (desktop).
- Tap targets expand to full-width on mobile for primary actions.
- Sticky headers: reduce height on scroll (56px → 48px).
- Bottom sheets instead of modals on mobile for forms.
