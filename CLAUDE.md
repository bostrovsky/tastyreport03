# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TastyTrade Tracker is a Django monolith application for syncing, tracking, and analyzing TastyTrade trading activity. The application uses Django for both backend and frontend with PostgreSQL database and Bootstrap UI.

## Technology Stack

- **Framework**: Django (latest stable)
- **Database**: PostgreSQL
- **Frontend**: Django Templates with Bootstrap
- **Authentication**: Django Authentication + django-allauth (Google, Apple OAuth)
- **API Integration**: TastyTrade SDK
- **Deployment**: Heroku

## Project Structure

```
tastytrade_tracker/
├── config/                  # Project settings (base.py, development.py, production.py)
├── apps/                    # Django applications
│   ├── accounts/            # User authentication and profiles
│   ├── dashboard/           # Main dashboard views
│   ├── tastytrade_sync/     # TastyTrade API integration and sync logic
│   ├── trades/              # Trade tracking, analysis, and data models
│   ├── reports/             # P&L calculations and reporting
│   └── core/                # Shared functionality
├── templates/               # HTML templates with Bootstrap
├── static/                  # Static files (CSS, JS, images)
├── utils/                   # Utility functions
└── requirements/            # Dependencies (base.txt, development.txt, production.txt)
```

## Key Implementation Requirements

### Authentication & Security
- Custom user model extending AbstractUser
- OAuth integration for Google/Apple using django-allauth
- Encrypted credential storage for TastyTrade API tokens (Django encrypted fields)
- Session-based authentication with CSRF protection
- HTTPS enforcement in production

### TastyTrade Sync Architecture
- **Manual sync only** - no scheduled/automatic syncing
- Optional sync-on-launch (user configurable)
- Bulletproof deduplication mechanisms using unique IDs
- Comprehensive error handling with retry logic and exponential backoff
- Sync status tracking and error reporting to users
- Data validation and integrity checks for all synced data

### Data Models
- **UserAccount**: Links Django users to TastyTrade accounts
- **Transaction**: All trading transactions with categorization
- **Position**: Current and historical position tracking
- **AccountBalance**: Balance history tracking
- **Strategy**: User-defined and system-inferred trading strategies
- **SyncStatus/SyncError**: Sync operation tracking and error logging

### Strategy Management
- System inference of common options strategies (covered calls, iron condors, etc.)
- User-defined custom strategies
- Create, split, merge, and reassign trades to strategies
- Edit history/audit log with undo/redo functionality

### Dashboard & Reporting
- Responsive Bootstrap-based UI
- Account summaries, P&L widgets, position overviews
- Realized and unrealized P&L calculations
- Export functionality (CSV for transactions and P&L)
- Chart.js for visualizations

## Testing Philosophy

- **Test-Driven Development (TDD)** - write tests before/with code
- Minimum 90% automated test coverage
- Unit tests for all models, services, and utilities
- Integration tests for sync flows, authentication, and reporting
- End-to-end tests for user journeys (login, sync, dashboard)
- Mock TastyTrade API for testing

## Development Commands

Since this is a planning repository with no actual code yet, specific commands will be determined during implementation. Expected commands will include:

- `python manage.py runserver` - Run development server
- `python manage.py test` - Run test suite
- `python manage.py migrate` - Apply database migrations
- `python manage.py collectstatic` - Collect static files for production

## Security Considerations

- Never store plaintext passwords or API credentials
- Use Django encrypted fields for sensitive data storage
- Implement proper input validation and sanitization
- Follow Django security best practices (CSRF, XSS, SQLi protection)
- Rate limiting for API endpoints
- Regular dependency updates

## Performance Requirements

- <2 minute average sync time for typical users
- Proper database indexing for frequently queried fields
- Caching for frequently accessed data
- Pagination for large datasets
- Query optimization for reporting views