# Stripe-Inspired Style Guide for TastyTrade Tracker App

## Introduction

This style guide provides a comprehensive set of design principles, components, and patterns for the TastyTrade Tracker application, inspired by Stripe's clean and professional aesthetic but implemented using Bootstrap. The goal is to create a consistent, accessible, and visually appealing user interface that feels modern and trustworthy.

## Color System

### Primary Colors

```css
:root {
  /* Primary brand color - used for primary actions, highlights */
  --tt-primary: #635BFF;
  --tt-primary-dark: #4B44C2;
  --tt-primary-light: #857DFF;
  
  /* Secondary brand color - used for secondary actions */
  --tt-secondary: #0A2540;
  --tt-secondary-light: #1D3E5F;
  
  /* Accent color - used sparingly for emphasis */
  --tt-accent: #00D4FF;
}
```

### Neutral Colors

```css
:root {
  /* Background colors */
  --tt-surface: #FFFFFF;
  --tt-container: #F6F9FC;
  --tt-container-dark: #E6EBF1;
  
  /* Text colors */
  --tt-text-primary: #1A1F36;
  --tt-text-secondary: #697386;
  --tt-text-disabled: #A5AFBD;
  
  /* Border colors */
  --tt-border-neutral: #E6EBF1;
  --tt-border-focus: #635BFF;
}
```

### Semantic Colors

```css
:root {
  /* Status colors */
  --tt-success: #32D583;
  --tt-info: #3E7BFA;
  --tt-warning: #FFC107;
  --tt-error: #FF4757;
  
  /* Status background colors (lighter versions) */
  --tt-success-light: #E3F9EF;
  --tt-info-light: #EBF2FF;
  --tt-warning-light: #FFF8E6;
  --tt-error-light: #FFEBEE;
}
```

## Typography

### Font Family

```css
:root {
  --tt-font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
}
```

### Font Sizes

```css
:root {
  --tt-font-size-xs: 0.75rem;    /* 12px */
  --tt-font-size-sm: 0.875rem;   /* 14px */
  --tt-font-size-md: 1rem;       /* 16px */
  --tt-font-size-lg: 1.125rem;   /* 18px */
  --tt-font-size-xl: 1.25rem;    /* 20px */
  --tt-font-size-2xl: 1.5rem;    /* 24px */
  --tt-font-size-3xl: 1.875rem;  /* 30px */
  --tt-font-size-4xl: 2.25rem;   /* 36px */
}
```

### Font Weights

```css
:root {
  --tt-font-weight-normal: 400;
  --tt-font-weight-medium: 500;
  --tt-font-weight-semibold: 600;
  --tt-font-weight-bold: 700;
}
```

### Line Heights

```css
:root {
  --tt-line-height-tight: 1.2;
  --tt-line-height-normal: 1.5;
  --tt-line-height-loose: 1.8;
}
```

### Text Styles

| Style | Usage | CSS Classes |
|-------|-------|------------|
| Heading 1 | Main page titles | `.tt-heading-1` |
| Heading 2 | Section titles | `.tt-heading-2` |
| Heading 3 | Subsection titles | `.tt-heading-3` |
| Body | Default text | `.tt-body` |
| Caption | Small text, labels | `.tt-caption` |
| Code | Code snippets | `.tt-code` |

```css
.tt-heading-1 {
  font-size: var(--tt-font-size-3xl);
  font-weight: var(--tt-font-weight-bold);
  line-height: var(--tt-line-height-tight);
  color: var(--tt-text-primary);
  margin-bottom: 1.5rem;
}

.tt-heading-2 {
  font-size: var(--tt-font-size-2xl);
  font-weight: var(--tt-font-weight-semibold);
  line-height: var(--tt-line-height-tight);
  color: var(--tt-text-primary);
  margin-bottom: 1.25rem;
}

.tt-heading-3 {
  font-size: var(--tt-font-size-xl);
  font-weight: var(--tt-font-weight-semibold);
  line-height: var(--tt-line-height-tight);
  color: var(--tt-text-primary);
  margin-bottom: 1rem;
}

.tt-body {
  font-size: var(--tt-font-size-md);
  font-weight: var(--tt-font-weight-normal);
  line-height: var(--tt-line-height-normal);
  color: var(--tt-text-primary);
}

.tt-caption {
  font-size: var(--tt-font-size-sm);
  font-weight: var(--tt-font-weight-normal);
  line-height: var(--tt-line-height-normal);
  color: var(--tt-text-secondary);
}

.tt-code {
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: var(--tt-font-size-sm);
  background-color: var(--tt-container);
  padding: 0.2em 0.4em;
  border-radius: 3px;
}
```

## Spacing

```css
:root {
  --tt-space-1: 0.25rem;   /* 4px */
  --tt-space-2: 0.5rem;    /* 8px */
  --tt-space-3: 0.75rem;   /* 12px */
  --tt-space-4: 1rem;      /* 16px */
  --tt-space-5: 1.5rem;    /* 24px */
  --tt-space-6: 2rem;      /* 32px */
  --tt-space-7: 2.5rem;    /* 40px */
  --tt-space-8: 3rem;      /* 48px */
  --tt-space-9: 4rem;      /* 64px */
  --tt-space-10: 5rem;     /* 80px */
}
```

## Border Radius

```css
:root {
  --tt-radius-sm: 4px;
  --tt-radius-md: 8px;
  --tt-radius-lg: 12px;
  --tt-radius-full: 9999px;
}
```

## Shadows

```css
:root {
  --tt-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --tt-shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --tt-shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --tt-shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}
```

## Bootstrap Component Customization

### Buttons

```css
/* Primary Button */
.btn-primary {
  background-color: var(--tt-primary);
  border-color: var(--tt-primary);
  border-radius: var(--tt-radius-md);
  font-weight: var(--tt-font-weight-medium);
  padding: 0.625rem 1.25rem;
  transition: all 0.15s ease;
  box-shadow: var(--tt-shadow-sm);
}

.btn-primary:hover, .btn-primary:focus {
  background-color: var(--tt-primary-dark);
  border-color: var(--tt-primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--tt-shadow-md);
}

/* Secondary Button */
.btn-secondary {
  background-color: white;
  border-color: var(--tt-border-neutral);
  color: var(--tt-text-primary);
  border-radius: var(--tt-radius-md);
  font-weight: var(--tt-font-weight-medium);
  padding: 0.625rem 1.25rem;
  transition: all 0.15s ease;
}

.btn-secondary:hover, .btn-secondary:focus {
  background-color: var(--tt-container);
  border-color: var(--tt-border-neutral);
  color: var(--tt-text-primary);
}

/* Outline Button */
.btn-outline-primary {
  color: var(--tt-primary);
  border-color: var(--tt-primary);
  border-radius: var(--tt-radius-md);
  font-weight: var(--tt-font-weight-medium);
  padding: 0.625rem 1.25rem;
}

.btn-outline-primary:hover, .btn-outline-primary:focus {
  background-color: var(--tt-primary);
  color: white;
}
```

### Cards

```css
.card {
  border: 1px solid var(--tt-border-neutral);
  border-radius: var(--tt-radius-lg);
  box-shadow: var(--tt-shadow-sm);
  transition: box-shadow 0.15s ease;
}

.card:hover {
  box-shadow: var(--tt-shadow-md);
}

.card-header {
  background-color: white;
  border-bottom: 1px solid var(--tt-border-neutral);
  padding: var(--tt-space-4) var(--tt-space-5);
}

.card-body {
  padding: var(--tt-space-5);
}

.card-footer {
  background-color: var(--tt-container);
  border-top: 1px solid var(--tt-border-neutral);
  padding: var(--tt-space-4) var(--tt-space-5);
}
```

### Forms

```css
.form-control {
  border: 1px solid var(--tt-border-neutral);
  border-radius: var(--tt-radius-md);
  padding: 0.625rem 0.75rem;
  font-size: var(--tt-font-size-md);
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-control:focus {
  border-color: var(--tt-border-focus);
  box-shadow: 0 0 0 4px rgba(99, 91, 255, 0.15);
}

.form-label {
  font-size: var(--tt-font-size-sm);
  font-weight: var(--tt-font-weight-medium);
  color: var(--tt-text-secondary);
  margin-bottom: var(--tt-space-2);
}

.form-text {
  font-size: var(--tt-font-size-sm);
  color: var(--tt-text-secondary);
  margin-top: var(--tt-space-2);
}
```

### Alerts

```css
.alert {
  border: none;
  border-radius: var(--tt-radius-md);
  padding: var(--tt-space-4) var(--tt-space-5);
}

.alert-success {
  background-color: var(--tt-success-light);
  color: var(--tt-success);
}

.alert-info {
  background-color: var(--tt-info-light);
  color: var(--tt-info);
}

.alert-warning {
  background-color: var(--tt-warning-light);
  color: var(--tt-warning);
}

.alert-danger {
  background-color: var(--tt-error-light);
  color: var(--tt-error);
}
```

### Badges

```css
.badge {
  font-weight: var(--tt-font-weight-medium);
  padding: 0.35em 0.65em;
  border-radius: var(--tt-radius-full);
}

.badge-primary {
  background-color: var(--tt-primary);
}

.badge-success {
  background-color: var(--tt-success);
}

.badge-info {
  background-color: var(--tt-info);
}

.badge-warning {
  background-color: var(--tt-warning);
  color: var(--tt-text-primary);
}

.badge-danger {
  background-color: var(--tt-error);
}
```

### Tables

```css
.table {
  --bs-table-bg: transparent;
  --bs-table-striped-bg: var(--tt-container);
  --bs-table-striped-color: var(--tt-text-primary);
  --bs-table-active-bg: var(--tt-container-dark);
  --bs-table-active-color: var(--tt-text-primary);
  --bs-table-hover-bg: var(--tt-container);
  --bs-table-hover-color: var(--tt-text-primary);
  
  border-color: var(--tt-border-neutral);
}

.table thead th {
  background-color: var(--tt-container);
  border-bottom: 1px solid var(--tt-border-neutral);
  color: var(--tt-text-secondary);
  font-weight: var(--tt-font-weight-medium);
  text-transform: uppercase;
  font-size: var(--tt-font-size-xs);
  letter-spacing: 0.05em;
}

.table tbody td {
  border-bottom: 1px solid var(--tt-border-neutral);
  padding: var(--tt-space-4);
  vertical-align: middle;
}
```

### Navs and Tabs

```css
.nav-tabs {
  border-bottom: 1px solid var(--tt-border-neutral);
}

.nav-tabs .nav-link {
  border: none;
  color: var(--tt-text-secondary);
  font-weight: var(--tt-font-weight-medium);
  padding: var(--tt-space-3) var(--tt-space-4);
  margin-right: var(--tt-space-4);
  transition: color 0.15s ease-in-out;
}

.nav-tabs .nav-link:hover {
  color: var(--tt-text-primary);
  border: none;
}

.nav-tabs .nav-link.active {
  color: var(--tt-primary);
  background-color: transparent;
  border: none;
  border-bottom: 2px solid var(--tt-primary);
}
```

### Pagination

```css
.pagination .page-link {
  color: var(--tt-text-primary);
  border: 1px solid var(--tt-border-neutral);
  padding: 0.5rem 0.75rem;
}

.pagination .page-link:hover {
  background-color: var(--tt-container);
  border-color: var(--tt-border-neutral);
  color: var(--tt-text-primary);
}

.pagination .page-item.active .page-link {
  background-color: var(--tt-primary);
  border-color: var(--tt-primary);
  color: white;
}
```

### Modals

```css
.modal-content {
  border: none;
  border-radius: var(--tt-radius-lg);
  box-shadow: var(--tt-shadow-xl);
}

.modal-header {
  border-bottom: 1px solid var(--tt-border-neutral);
  padding: var(--tt-space-4) var(--tt-space-5);
}

.modal-body {
  padding: var(--tt-space-5);
}

.modal-footer {
  border-top: 1px solid var(--tt-border-neutral);
  padding: var(--tt-space-4) var(--tt-space-5);
}
```

## Layout Guidelines

### Container Widths

```css
.container-sm {
  max-width: 640px;
}

.container-md {
  max-width: 768px;
}

.container-lg {
  max-width: 1024px;
}

.container-xl {
  max-width: 1280px;
}
```

### Grid System

Use Bootstrap's built-in grid system with custom gutters:

```css
.row {
  --bs-gutter-x: var(--tt-space-5);
  --bs-gutter-y: var(--tt-space-5);
}
```

### Section Spacing

```css
.section {
  padding: var(--tt-space-8) 0;
}

.section-sm {
  padding: var(--tt-space-6) 0;
}

.section-lg {
  padding: var(--tt-space-10) 0;
}
```

## Dashboard-Specific Components

### Dashboard Header

```html
<header class="tt-dashboard-header">
  <div class="container-fluid">
    <div class="d-flex justify-content-between align-items-center">
      <h1 class="tt-heading-2 mb-0">Dashboard</h1>
      <div class="tt-dashboard-actions">
        <button class="btn btn-outline-primary me-2">Export</button>
        <button class="btn btn-primary">Sync Data</button>
      </div>
    </div>
  </div>
</header>
```

```css
.tt-dashboard-header {
  background-color: white;
  border-bottom: 1px solid var(--tt-border-neutral);
  padding: var(--tt-space-4) 0;
  margin-bottom: var(--tt-space-6);
}
```

### Stat Cards

```html
<div class="tt-stat-card">
  <div class="tt-stat-card-label">Total P&L</div>
  <div class="tt-stat-card-value">$2,458.32</div>
  <div class="tt-stat-card-change tt-positive">+12.5%</div>
</div>
```

```css
.tt-stat-card {
  background-color: white;
  border-radius: var(--tt-radius-lg);
  padding: var(--tt-space-5);
  box-shadow: var(--tt-shadow-sm);
  transition: box-shadow 0.15s ease;
}

.tt-stat-card:hover {
  box-shadow: var(--tt-shadow-md);
}

.tt-stat-card-label {
  font-size: var(--tt-font-size-sm);
  color: var(--tt-text-secondary);
  margin-bottom: var(--tt-space-2);
}

.tt-stat-card-value {
  font-size: var(--tt-font-size-2xl);
  font-weight: var(--tt-font-weight-bold);
  color: var(--tt-text-primary);
  margin-bottom: var(--tt-space-2);
}

.tt-stat-card-change {
  font-size: var(--tt-font-size-sm);
  font-weight: var(--tt-font-weight-medium);
}

.tt-positive {
  color: var(--tt-success);
}

.tt-negative {
  color: var(--tt-error);
}
```

### Data Table

```html
<div class="tt-data-table-container">
  <div class="tt-data-table-header">
    <h3 class="tt-heading-3 mb-0">Recent Trades</h3>
    <div class="tt-data-table-actions">
      <button class="btn btn-sm btn-outline-primary">Filter</button>
    </div>
  </div>
  <div class="table-responsive">
    <table class="table tt-data-table">
      <!-- Table content -->
    </table>
  </div>
  <div class="tt-data-table-footer">
    <nav aria-label="Table navigation">
      <ul class="pagination">
        <!-- Pagination content -->
      </ul>
    </nav>
  </div>
</div>
```

```css
.tt-data-table-container {
  background-color: white;
  border-radius: var(--tt-radius-lg);
  box-shadow: var(--tt-shadow-sm);
  overflow: hidden;
}

.tt-data-table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--tt-space-4) var(--tt-space-5);
  border-bottom: 1px solid var(--tt-border-neutral);
}

.tt-data-table {
  margin-bottom: 0;
}

.tt-data-table-footer {
  padding: var(--tt-space-4) var(--tt-space-5);
  border-top: 1px solid var(--tt-border-neutral);
  background-color: var(--tt-container);
}
```

### Chart Cards

```html
<div class="tt-chart-card">
  <div class="tt-chart-card-header">
    <h3 class="tt-heading-3 mb-0">P&L Over Time</h3>
    <div class="tt-chart-card-controls">
      <select class="form-select form-select-sm">
        <option>Last 7 days</option>
        <option>Last 30 days</option>
        <option>Last 90 days</option>
      </select>
    </div>
  </div>
  <div class="tt-chart-card-body">
    <!-- Chart content -->
  </div>
</div>
```

```css
.tt-chart-card {
  background-color: white;
  border-radius: var(--tt-radius-lg);
  box-shadow: var(--tt-shadow-sm);
  overflow: hidden;
}

.tt-chart-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--tt-space-4) var(--tt-space-5);
  border-bottom: 1px solid var(--tt-border-neutral);
}

.tt-chart-card-body {
  padding: var(--tt-space-5);
  height: 300px;
}
```

## Utility Classes

```css
/* Text colors */
.tt-text-primary { color: var(--tt-text-primary); }
.tt-text-secondary { color: var(--tt-text-secondary); }
.tt-text-disabled { color: var(--tt-text-disabled); }
.tt-text-brand { color: var(--tt-primary); }
.tt-text-success { color: var(--tt-success); }
.tt-text-info { color: var(--tt-info); }
.tt-text-warning { color: var(--tt-warning); }
.tt-text-error { color: var(--tt-error); }

/* Background colors */
.tt-bg-surface { background-color: var(--tt-surface); }
.tt-bg-container { background-color: var(--tt-container); }
.tt-bg-container-dark { background-color: var(--tt-container-dark); }
.tt-bg-brand { background-color: var(--tt-primary); }
.tt-bg-success-light { background-color: var(--tt-success-light); }
.tt-bg-info-light { background-color: var(--tt-info-light); }
.tt-bg-warning-light { background-color: var(--tt-warning-light); }
.tt-bg-error-light { background-color: var(--tt-error-light); }

/* Border utilities */
.tt-border { border: 1px solid var(--tt-border-neutral); }
.tt-border-top { border-top: 1px solid var(--tt-border-neutral); }
.tt-border-right { border-right: 1px solid var(--tt-border-neutral); }
.tt-border-bottom { border-bottom: 1px solid var(--tt-border-neutral); }
.tt-border-left { border-left: 1px solid var(--tt-border-neutral); }

/* Border radius */
.tt-rounded-sm { border-radius: var(--tt-radius-sm); }
.tt-rounded-md { border-radius: var(--tt-radius-md); }
.tt-rounded-lg { border-radius: var(--tt-radius-lg); }
.tt-rounded-full { border-radius: var(--tt-radius-full); }

/* Shadows */
.tt-shadow-sm { box-shadow: var(--tt-shadow-sm); }
.tt-shadow-md { box-shadow: var(--tt-shadow-md); }
.tt-shadow-lg { box-shadow: var(--tt-shadow-lg); }
.tt-shadow-xl { box-shadow: var(--tt-shadow-xl); }
```

## Implementation Guide

### Bootstrap Integration

1. Include Bootstrap CSS and JS in your project:

```html
<!-- Bootstrap CSS -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

<!-- Custom CSS with TastyTrade styles -->
<link href="/css/tastytrade-styles.css" rel="stylesheet">

<!-- Bootstrap JS Bundle with Popper -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
```

2. Create a custom CSS file (`tastytrade-styles.css`) that includes all the custom styles defined in this guide.

3. Use Bootstrap's grid system and components with the custom TastyTrade classes to achieve the desired look and feel.

### Example Page Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TastyTrade Tracker</title>
  
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  
  <!-- Custom CSS with TastyTrade styles -->
  <link href="/css/tastytrade-styles.css" rel="stylesheet">
</head>
<body class="tt-bg-container">
  <!-- Navigation -->
  <nav class="navbar navbar-expand-lg navbar-light bg-white border-bottom">
    <div class="container-fluid">
      <a class="navbar-brand" href="#">
        <img src="/img/logo.svg" alt="TastyTrade Tracker" height="30">
      </a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav me-auto">
          <li class="nav-item">
            <a class="nav-link active" href="#">Dashboard</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#">Trades</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#">Analytics</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#">Settings</a>
          </li>
        </ul>
        <div class="d-flex">
          <button class="btn btn-primary">Sync Data</button>
        </div>
      </div>
    </div>
  </nav>

  <!-- Dashboard Header -->
  <header class="tt-dashboard-header">
    <div class="container-fluid">
      <div class="d-flex justify-content-between align-items-center">
        <h1 class="tt-heading-2 mb-0">Dashboard</h1>
        <div class="tt-dashboard-actions">
          <button class="btn btn-outline-primary me-2">Export</button>
          <button class="btn btn-primary">Sync Data</button>
        </div>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="container-fluid">
    <!-- Stats Row -->
    <div class="row mb-5">
      <div class="col-md-3">
        <div class="tt-stat-card">
          <div class="tt-stat-card-label">Total P&L</div>
          <div class="tt-stat-card-value">$2,458.32</div>
          <div class="tt-stat-card-change tt-positive">+12.5%</div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="tt-stat-card">
          <div class="tt-stat-card-label">Win Rate</div>
          <div class="tt-stat-card-value">68%</div>
          <div class="tt-stat-card-change tt-positive">+3.2%</div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="tt-stat-card">
          <div class="tt-stat-card-label">Open Positions</div>
          <div class="tt-stat-card-value">12</div>
          <div class="tt-stat-card-change">No change</div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="tt-stat-card">
          <div class="tt-stat-card-label">Total Trades</div>
          <div class="tt-stat-card-value">156</div>
          <div class="tt-stat-card-change tt-positive">+8</div>
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="row mb-5">
      <div class="col-md-8">
        <div class="tt-chart-card">
          <div class="tt-chart-card-header">
            <h3 class="tt-heading-3 mb-0">P&L Over Time</h3>
            <div class="tt-chart-card-controls">
              <select class="form-select form-select-sm">
                <option>Last 7 days</option>
                <option>Last 30 days</option>
                <option>Last 90 days</option>
              </select>
            </div>
          </div>
          <div class="tt-chart-card-body">
            <!-- Chart content would go here -->
            <div style="height: 300px; display: flex; align-items: center; justify-content: center;">
              [P&L Chart Placeholder]
            </div>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="tt-chart-card">
          <div class="tt-chart-card-header">
            <h3 class="tt-heading-3 mb-0">Strategy Breakdown</h3>
          </div>
          <div class="tt-chart-card-body">
            <!-- Chart content would go here -->
            <div style="height: 300px; display: flex; align-items: center; justify-content: center;">
              [Pie Chart Placeholder]
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Data Table -->
    <div class="row">
      <div class="col-12">
        <div class="tt-data-table-container">
          <div class="tt-data-table-header">
            <h3 class="tt-heading-3 mb-0">Recent Trades</h3>
            <div class="tt-data-table-actions">
              <button class="btn btn-sm btn-outline-primary">Filter</button>
            </div>
          </div>
          <div class="table-responsive">
            <table class="table tt-data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Symbol</th>
                  <th>Strategy</th>
                  <th>Entry Price</th>
                  <th>Exit Price</th>
                  <th>P&L</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>2025-05-25</td>
                  <td>AAPL</td>
                  <td>Iron Condor</td>
                  <td>$2.45</td>
                  <td>$0.85</td>
                  <td class="tt-positive">+$160.00</td>
                  <td><span class="badge bg-success">Closed</span></td>
                </tr>
                <tr>
                  <td>2025-05-24</td>
                  <td>SPY</td>
                  <td>Vertical Spread</td>
                  <td>$1.25</td>
                  <td>$2.10</td>
                  <td class="tt-negative">-$85.00</td>
                  <td><span class="badge bg-success">Closed</span></td>
                </tr>
                <tr>
                  <td>2025-05-23</td>
                  <td>TSLA</td>
                  <td>Covered Call</td>
                  <td>$4.50</td>
                  <td>--</td>
                  <td>--</td>
                  <td><span class="badge bg-primary">Open</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="tt-data-table-footer">
            <nav aria-label="Table navigation">
              <ul class="pagination mb-0">
                <li class="page-item disabled">
                  <a class="page-link" href="#" tabindex="-1">Previous</a>
                </li>
                <li class="page-item active"><a class="page-link" href="#">1</a></li>
                <li class="page-item"><a class="page-link" href="#">2</a></li>
                <li class="page-item"><a class="page-link" href="#">3</a></li>
                <li class="page-item">
                  <a class="page-link" href="#">Next</a>
                </li>
              </ul>
            </nav>
          </div>
        </div>
      </div>
    </div>
  </main>

  <!-- Bootstrap JS Bundle with Popper -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

## Accessibility Considerations

- Maintain a minimum contrast ratio of 4.5:1 for normal text and 3:1 for large text
- Use semantic HTML elements
- Include proper ARIA attributes where necessary
- Ensure keyboard navigation works for all interactive elements
- Provide text alternatives for non-text content
- Design focus states that are clearly visible

## Responsive Design Guidelines

- Use Bootstrap's responsive grid system
- Design for mobile-first, then enhance for larger screens
- Use responsive utility classes for spacing and sizing
- Test on multiple device sizes and orientations
- Consider touch targets (minimum 44x44px) for mobile users

## Animation Guidelines

- Use subtle animations for state changes
- Keep animations short (150-300ms)
- Avoid animations that could cause motion sickness
- Respect user preferences for reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  * {
    transition-duration: 0.001ms !important;
    animation-duration: 0.001ms !important;
  }
}
```
