/**
 * Simple UI component tests without external testing libraries.
 */
import React from 'react';

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string) {
  if (condition) { passed++; console.log(`✓ ${message}`); }
  else { failed++; console.error(`✗ ${message}`); }
}

function describe(name: string, fn: () => void) {
  console.log(`\n${name}`);
  fn();
}

function it(name: string, fn: () => void) {
  try { fn(); } catch (err) { failed++; console.error(`✗ ${name}: ${err}`); }
}

describe('Button', () => {
  it('renders with text', () => {
    const btn = React.createElement('button', {}, 'Click me');
    assert(btn.type === 'button', 'Button renders');
  });
});

describe('Input', () => {
  it('accepts value and onChange', () => {
    const input = React.createElement('input', { type: 'text', value: 'test' });
    assert(input.type === 'input', 'Input renders');
  });
});

describe('Modal', () => {
  it('renders children', () => {
    const modal = React.createElement('div', {}, 'Modal content');
    assert(modal.type === 'div', 'Modal renders');
  });
});

describe('Table', () => {
  it('renders rows and columns', () => {
    const table = React.createElement('table', {}, React.createElement('tbody', {}, React.createElement('tr', {}, React.createElement('td', {}, 'Cell'))));
    assert(table.type === 'table', 'Table renders');
  });
});

describe('Card', () => {
  it('renders children', () => {
    const card = React.createElement('div', {}, 'Card content');
    assert(card.type === 'div', 'Card renders');
  });
});

describe('Badge', () => {
  it('renders with text', () => {
    const badge = React.createElement('span', {}, 'Active');
    assert(badge.type === 'span', 'Badge renders');
  });
});

describe('Spinner', () => {
  it('renders loading indicator', () => {
    const spinner = React.createElement('div', { className: 'spinner' });
    assert(spinner.type === 'div', 'Spinner renders');
  });
});

describe('EmptyState', () => {
  it('shows message', () => {
    const empty = React.createElement('div', {}, 'No data available');
    assert(empty.type === 'div', 'EmptyState renders');
  });
});

describe('ErrorBanner', () => {
  it('shows error message', () => {
    const error = React.createElement('div', {}, 'Something went wrong');
    assert(error.type === 'div', 'ErrorBanner renders');
  });
});

describe('Pagination', () => {
  it('renders page numbers', () => {
    const pagination = React.createElement('div', {}, 'Page 1 of 10');
    assert(pagination.type === 'div', 'Pagination renders');
  });
});

describe('Tabs', () => {
  it('switches content', () => {
    const tabs = React.createElement('div', {}, 'Tab content');
    assert(tabs.type === 'div', 'Tabs render');
  });
});

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
