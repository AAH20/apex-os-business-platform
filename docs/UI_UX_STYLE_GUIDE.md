# APEX-OS Business Platform — UI/UX Style Guide

## 1. Color Palette

### Base Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `bg-gray-900` | `#111827` | Primary background, app shell |
| `bg-gray-800` | `#1F2937` | Card surfaces, panels, elevated elements |
| `bg-gray-700` | `#374151` | Borders, dividers, subtle separators |
| `text-gray-100` | `#F3F4F6` | Primary text, headings |
| `text-gray-300` | `#D1D5DB` | Secondary text, descriptions |
| `text-gray-400` | `#9CA3AF` | Muted text, placeholders, disabled |
| `text-gray-500` | `#6B7280` | Tertiary text, timestamps |

### Accent Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `accent-blue` | `#3B82F6` | Primary actions, links, active states |
| `accent-blue-hover` | `#2563EB` | Hover state for primary actions |
| `accent-green` | `#10B981` | Success, positive metrics, confirmations |
| `accent-red` | `#EF4444` | Errors, destructive actions, alerts |
| `accent-amber` | `#F59E0B` | Warnings, pending states |
| `accent-purple` | `#8B5CF6` | Highlights, special features, badges |

### Semantic Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `success-bg` | `#064E3B` | Success message backgrounds |
| `error-bg` | `#7F1D1D` | Error message backgrounds |
| `warning-bg` | `#78350F` | Warning message backgrounds |
| `info-bg` | `#1E3A8A` | Info message backgrounds |

### Opacity & Overlays

- Modal overlay: `rgba(0, 0, 0, 0.7)`
- Hover overlay: `rgba(255, 255, 255, 0.05)`
- Active overlay: `rgba(255, 255, 255, 0.1)`
- Disabled overlay: `rgba(0, 0, 0, 0.4)`

---

## 2. Typography Scale

### Font Family

- **Primary**: `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- **Monospace**: `"JetBrains Mono", "Fira Code", "SF Mono", Consolas, monospace`

### Scale

| Level | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `text-xs` | 12px | 400 | 16px | Timestamps, metadata, badges |
| `text-sm` | 14px | 400 | 20px | Body text, table cells, descriptions |
| `text-base` | 16px | 400 | 24px | Default body, form inputs |
| `text-lg` | 18px | 500 | 28px | Section headings, card titles |
| `text-xl` | 20px | 600 | 28px | Page titles, modal headers |
| `text-2xl` | 24px | 600 | 32px | Dashboard headers |
| `text-3xl` | 30px | 700 | 36px | Hero sections, landing pages |
| `text-4xl` | 36px | 700 | 40px | Marketing pages, empty states |

### Font Weights

- `400` — Regular (body text)
- `500` — Medium (emphasis, subheadings)
- `600` — SemiBold (headings, buttons)
- `700` — Bold (page titles, strong emphasis)

### Letter Spacing

- Default: `0`
- Uppercase labels: `0.05em`
- Wide headings: `-0.02em`

---

## 3. Spacing System

Base unit: **4px**

| Token | Value | Usage |
|-------|-------|-------|
| `space-0` | 0 | No spacing |
| `space-1` | 4px | Icon padding, tight gaps |
| `space-2` | 8px | Inline element gaps, badge padding |
| `space-3` | 12px | Button padding (vertical), list item gaps |
| `space-4` | 16px | Card padding, form field gaps |
| `space-5` | 20px | Section internal spacing |
| `space-6` | 24px | Card gaps, section padding |
| `space-8` | 32px | Section spacing, modal padding |
| `space-10` | 40px | Page section spacing |
| `space-12` | 48px | Large section spacing |
| `space-16` | 64px | Page-level spacing |

### Layout Constants

- **Max content width**: `1280px`
- **Sidebar width**: `256px` (collapsed: `64px`)
- **Header height**: `64px`
- **Border radius**: `6px` (cards, inputs), `4px` (buttons, badges), `9999px` (pills, avatars)
- **Border width**: `1px` (default), `2px` (focus rings)

---

## 4. Component Patterns

### Cards

```
Background: bg-gray-800
Border: 1px solid bg-gray-700
Border radius: 6px
Padding: 24px (space-6)
Shadow: none (use border for separation)
```

- **Hover**: Subtle border lightening to `#4B5563`
- **Elevated variant**: `box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3)`
- **Header**: `text-lg` font, `text-gray-100`, bottom border `bg-gray-700`, padding-bottom `space-4`
- **Body**: `text-sm`, `text-gray-300`

### Tables

```
Header row: bg-gray-900, text-xs, uppercase, text-gray-400, font-weight 600
Row: bg-gray-800, text-sm, text-gray-100
Row hover: bg-gray-700/50
Row border-bottom: 1px solid bg-gray-700
Cell padding: 12px 16px (space-3 space-4)
```

- **Sticky header**: `position: sticky; top: 0; z-index: 10`
- **Numeric columns**: Right-aligned, monospace font
- **Sortable headers**: Show arrow icon on hover, highlight active sort
- **Row selection**: Left border `3px solid accent-blue`, background `rgba(59, 130, 246, 0.1)`

### Modals

```
Overlay: rgba(0, 0, 0, 0.7)
Container: bg-gray-800, border-radius 8px, max-width 560px
Header: text-xl, text-gray-100, padding 24px, border-bottom bg-gray-700
Body: padding 24px, text-sm, text-gray-300
Footer: padding 16px 24px, border-top bg-gray-700, flex row, gap 12px
```

- **Entrance animation**: Fade in overlay (150ms), scale modal from 0.95 to 1.0 (200ms)
- **Exit animation**: Reverse of entrance (150ms)
- **Close on overlay click**: Yes
- **Close on Escape**: Yes
- **Focus trap**: Yes, cycle within modal

### Forms

```
Label: text-sm, text-gray-300, font-weight 500, margin-bottom 6px
Input: bg-gray-900, border 1px solid bg-gray-700, border-radius 4px,
       padding 10px 12px, text-base, text-gray-100, width 100%
Input placeholder: text-gray-500
Input focus: border-color accent-blue, box-shadow 0 0 0 3px rgba(59, 130, 246, 0.2)
Input error: border-color accent-red, box-shadow 0 0 0 3px rgba(239, 68, 68, 0.2)
Helper text: text-xs, text-gray-400, margin-top 4px
Error text: text-xs, text-accent-red, margin-top 4px
```

- **Disabled inputs**: `opacity: 0.5; cursor: not-allowed`
- **Select**: Same as input, custom chevron icon
- **Checkbox/Radio**: `accent-blue` color, `text-gray-100` label
- **Toggle switch**: Track `bg-gray-700`, active `bg-blue`, thumb `bg-white`

### Buttons

```
Primary: bg-accent-blue, text-white, hover bg-accent-blue-hover,
         padding 10px 16px, border-radius 4px, font-weight 500, text-sm
Secondary: bg-gray-700, text-gray-100, hover bg-gray-600
Ghost: bg-transparent, text-gray-300, hover bg-gray-700/50, hover text-gray-100
Danger: bg-accent-red, text-white, hover bg-red-700
Disabled: opacity 0.5, cursor not-allowed
```

- **Icon buttons**: 36px × 36px, transparent background, hover `bg-gray-700/50`
- **Button groups**: Shared border, no gap, first/last child rounded

### Badges

```
Default: bg-gray-700, text-gray-300, padding 2px 8px, border-radius 9999px, text-xs
Success: bg-green-900/30, text-green-400
Error: bg-red-900/30, text-red-400
Warning: bg-amber-900/30, text-amber-400
Info: bg-blue-900/30, text-blue-400
```

### Navigation

```
Sidebar item: text-gray-400, hover text-gray-100, hover bg-gray-700/50,
              padding 10px 16px, border-radius 4px
Active item: text-accent-blue, bg-accent-blue/10, border-left 3px solid accent-blue
Breadcrumb: text-sm, text-gray-400, separator text-gray-600
```

---

## 5. Interaction Patterns

### Hover States

- **Buttons**: Background darkens/lightens by one shade
- **Links**: Color shifts to `accent-blue`, underline on hover
- **Cards**: Border lightens, subtle lift (`translateY(-1px)`)
- **Table rows**: Background `bg-gray-700/50`
- **Interactive elements**: Cursor changes to `pointer`

### Focus States

- **Focus ring**: `box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.4)`
- **Focus ring (error)**: `box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.4)`
- **Keyboard-only**: Use `:focus-visible` to show rings only for keyboard navigation
- **Focus order**: Logical DOM order, skip links for main content

### Active States

- **Buttons**: Slight scale down (`scale(0.98)`), darker background
- **Toggle/Switch**: Immediate visual state change
- **Tabs**: Bottom border `2px solid accent-blue`, text `text-gray-100`

### Transitions

- **Duration**: 150ms (hover, color), 200ms (modals, dropdowns), 300ms (page transitions)
- **Easing**: `ease-out` for entrances, `ease-in` for exits
- **Properties**: `color, background-color, border-color, box-shadow, transform, opacity`

### Loading States

- **Spinner**: `border: 2px solid bg-gray-700; border-top-color: accent-blue; border-radius: 50%`
- **Skeleton**: `bg-gray-700` with shimmer animation
- **Button loading**: Replace text with spinner, disable button

### Empty States

- **Icon**: Large (48px), `text-gray-600`
- **Title**: `text-lg`, `text-gray-300`
- **Description**: `text-sm`, `text-gray-400`
- **Action**: Primary button centered below

---

## 6. Accessibility Guidelines

### Contrast Ratios

- **Normal text**: Minimum 4.5:1 against background
- **Large text (18px+)**: Minimum 3:1 against background
- **UI components**: Minimum 3:1 against adjacent colors
- **Current palette verified**: `text-gray-100` on `bg-gray-900` = 14.7:1 (AAA)

### Keyboard Navigation

- All interactive elements must be focusable
- Tab order follows visual/DOM order
- Escape closes modals, dropdowns, popovers
- Enter/Space activates buttons and toggles
- Arrow keys navigate within lists, tabs, menus

### ARIA Requirements

- Modals: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- Tabs: `role="tablist"`, `role="tab"`, `aria-selected`
- Alerts: `role="alert"` for errors, `role="status"` for updates
- Navigation: `role="navigation"`, `aria-label` for sections
- Forms: `aria-describedby` for helper/error text, `aria-invalid` for errors

### Motion & Animation

- Respect `prefers-reduced-motion`: Disable all non-essential animations
- No flashing content (max 3 flashes per second)
- Provide pause/stop for auto-playing content

### Screen Readers

- Meaningful alt text for all images
- `aria-label` for icon-only buttons
- `sr-only` class for visually hidden but screen-reader-visible text
- Announce dynamic content changes via `aria-live` regions

---

## 7. Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| `sm` | 640px | Single column, stacked cards |
| `md` | 768px | Two-column grids, sidebar visible |
| `lg` | 1024px | Full layout, multi-column dashboards |
| `xl` | 1280px | Max content width, expanded tables |
| `2xl` | 1536px | Ultra-wide, optional side panels |

### Mobile-First Approach

- Base styles target mobile (`< 640px`)
- Use `min-width` media queries for larger breakpoints
- Touch targets minimum 44px × 44px
- Sidebar collapses to hamburger menu below `md`
- Tables become card lists below `md`
- Modals become full-screen sheets below `sm`

### Breakpoint Usage

```css
/* Mobile-first example */
.card-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

@media (min-width: 768px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .card-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

---

## 8. Iconography

- **Library**: Lucide Icons (consistent stroke-based set)
- **Size**: 16px (inline), 20px (buttons), 24px (nav), 32px (empty states)
- **Stroke width**: 2px
- **Color**: Inherits `currentColor`
- **Spacing**: 8px gap between icon and text

---

## 9. Z-Index Scale

| Layer | Value | Usage |
|-------|-------|-------|
| Base | 0 | Normal content |
| Dropdown | 1000 | Dropdown menus, popovers |
| Sticky | 1100 | Sticky headers, table headers |
| Fixed | 1200 | Fixed navigation, sidebars |
| Modal overlay | 1300 | Modal backdrop |
| Modal | 1400 | Modal content |
| Toast | 1500 | Toast notifications |
| Tooltip | 1600 | Tooltips |

---

## 10. Design Principles

1. **Clarity over decoration** — Every element serves a purpose
2. **Consistency** — Same patterns across all views
3. **Efficiency** — Minimize clicks and cognitive load
4. **Feedback** — Every action has a visible response
5. **Forgiveness** — Undo destructive actions, confirm irreversible ones
6. **Accessibility** — Design for all users from the start
