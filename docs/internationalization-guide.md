# Internationalization (i18n) Guide

## 1. i18n Strategy

APEX-OS uses a **message-catalog** approach with ICU MessageFormat for all user-facing strings.

- **Library**: `formatjs` / `react-intl` (React) or `vue-i18n` (Vue) — pick per app.
- **Message IDs**: Stable, dot-namespaced keys (e.g., `dashboard.header.title`). Never use raw English strings as keys.
- **Interpolation**: Use ICU syntax — `{count, plural, one {# item} other {# items}}`.
- **Extraction**: Run `formatjs extract` (or equivalent) to auto-generate catalogs from source.
- **Fallback chain**: `requested-locale` → `language-only` → `default-locale` (en-US).
- **No hardcoded strings**: All UI text must come from catalogs. Dates, numbers, and currencies use `Intl.*` APIs.

## 2. Locale Management

### Supported Locales

| Code  | Language   | Direction | Status     |
|-------|-----------|-----------|------------|
| en-US | English   | LTR       | Source     |
| ar-SA | Arabic    | RTL       | Supported  |
| he-IL | Hebrew    | RTL       | Supported  |
| de-DE | German    | LTR       | Supported  |
| fr-FR | French    | LTR       | Supported  |
| ja-JP | Japanese  | LTR       | Supported  |

### Locale Resolution Order

1. User preference (stored in profile / localStorage)
2. `?lang=` query parameter
3. `Accept-Language` header
4. Default: `en-US`

### Locale Storage

- Persist user choice in `localStorage` key `apexos.locale`.
- Sync to backend user profile on change.
- SSR: read from cookie or header.

### Adding a New Locale

1. Add locale code to `src/i18n/locales.ts`.
2. Create `src/i18n/messages/<locale>.json`.
3. Add to CI extraction pipeline.
4. Update locale picker component.
5. Add locale-specific formatting rules (date, number, currency).

## 3. Translation Workflow

### Source of Truth

- English (`en-US`) catalog is the **source of truth**.
- All other locales are translations of this catalog.

### Process

1. **Extract**: `pnpm i18n:extract` — scans source for `<FormattedMessage>` / `defineMessages` calls, updates `en-US.json`.
2. **Push to TMS**: `pnpm i18n:push` — sends new/changed keys to translation management system (e.g., Crowdin, Lokalise).
3. **Translate**: Translators work in TMS. Context screenshots and developer notes are attached per key.
4. **Pull**: `pnpm i18n:pull` — downloads completed translations into `src/i18n/messages/<locale>.json`.
5. **Verify**: `pnpm i18n:verify` — checks for missing keys, ICU syntax errors, and placeholder mismatches.
6. **Review**: PR review includes diff of message catalogs.

### Developer Guidelines

- Always provide `description` in `defineMessages` for translator context.
- Use `<FormattedMessage>` with `id` and `description` props.
- Never concatenate strings — use ICU plural/select instead.
- Keep messages under 500 characters; split if longer.
- Avoid gender-specific phrasing unless using ICU `select`.

### CI Checks

- Block PRs with missing translations for supported locales.
- Block PRs with ICU syntax errors.
- Warn on untranslated keys (non-blocking for new features).

## 4. RTL Support

### Detection

- Use `Intl.Locale` to determine text direction: `new Intl.Locale(locale).textInfo.direction`.
- Or maintain a static set: `const RTL_LOCALES = new Set(['ar', 'he', 'fa', 'ur'])`.

### Implementation

- **CSS**: Use logical properties (`margin-inline-start`, `padding-inline-end`, `border-inline-start`) instead of physical (`margin-left`, `padding-right`).
- **Tailwind**: Use `ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*` utilities.
- **Icons**: Mirror directional icons (arrows, chevrons) with `[dir="rtl"] .icon-arrow { transform: scaleX(-1); }`.
- **Layout**: Flexbox and Grid auto-flip with logical properties. Avoid absolute positioning with `left`/`right`.
- **Text alignment**: Use `text-start` / `text-end` instead of `text-left` / `text-right`.

### Testing RTL

- Run visual regression tests with `dir="rtl"` on `<html>`.
- Manually verify: navigation, modals, forms, tables, charts.
- Check number formatting and date display in RTL context.

### Common Pitfalls

- **Mixed content**: Embedding LTR text (URLs, code) in RTL paragraphs — use `<bdi>` or `unicode-bidi: isolate`.
- **Tables**: Column order should flip in RTL.
- **Charts**: Axis direction and legend placement need RTL variants.
- **Animations**: Slide directions must mirror.

## 5. Testing Strategy

### Unit Tests

- **Message rendering**: Test that components render correct strings for each locale.
- **ICU formatting**: Test plural, select, and date/number formatting with various inputs.
- **Locale resolution**: Test the fallback chain logic.

```tsx
// Example: testing plural formatting
const messages = { items: '{count, plural, one {# item} other {# items}}' };
expect(formatMessage(messages.items, { count: 1 })).toBe('1 item');
expect(formatMessage(messages.items, { count: 5 })).toBe('5 items');
```

### Integration Tests

- **Locale switching**: Test that changing locale updates all visible strings.
- **Persistence**: Test that locale choice survives page reload.
- **SSR**: Test that server-rendered HTML has correct `lang` and `dir` attributes.

### E2E Tests

- **Visual regression**: Screenshot key pages in each supported locale + RTL.
- **Functional**: Complete critical flows (login, create project, checkout) in each locale.
- **Accessibility**: Run axe-core with locale-specific rules.

### CI Pipeline

| Stage              | What                          | Blocking |
|--------------------|-------------------------------|----------|
| Lint               | No hardcoded strings          | Yes      |
| Unit tests         | ICU formatting, rendering     | Yes      |
| i18n:verify        | Missing keys, syntax errors   | Yes      |
| Visual regression  | Screenshot diff per locale    | Yes      |
| E2E smoke          | Critical flow per locale      | Yes      |

### Manual QA Checklist

- [ ] All pages render without missing-key warnings
- [ ] No layout overflow from longer translations (German, Finnish)
- [ ] RTL pages: layout, icons, tables, charts correct
- [ ] Dates, times, numbers, currencies format correctly
- [ ] Locale switcher works and persists
- [ ] Screen readers announce content in correct language
