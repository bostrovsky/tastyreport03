# Taskmaster MCP Prompt for TastyTrade Tracker PRD Creation

## Context

I need you to transform the Django Architecture Plan and Detailed Implementation Plan for the TastyTrade Tracker application into a comprehensive Product Requirements Document (PRD) with risk-assessed steps and sub-steps. This PRD will serve as the definitive guide for development, with a strong emphasis on test-driven development at each implementation step.

## Input Documents

1. Django Monolith Architecture document
2. Django Implementation Plan document
3. TastyTrade SDK Implementation Guide

## Output Requirements

Create a detailed PRD with the following structure:

1. **Executive Summary**
   - Brief overview of the TastyTrade Tracker application
   - Key objectives and success metrics
   - Target timeline
   - Testing philosophy and approach

2. **Product Overview**
   - Purpose and scope
   - User personas
   - Core functionality
   - Technical architecture summary
   - Testing strategy overview

3. **Detailed Requirements**
   - For each feature (User Authentication, TastyTrade API Integration, etc.):
     - Feature description
     - User stories
     - Acceptance criteria
     - Technical requirements
     - Dependencies
     - **Testing requirements (unit, integration, end-to-end)**

4. **Implementation Plan**
   - Convert the implementation steps into a structured plan with:
     - Main steps
     - Sub-steps
     - **Risk assessment (1-10 scale) for each step**
     - **Break down any step with risk > 5 into smaller sub-steps with risk < 5**
     - Dependencies between steps
     - Estimated effort (story points or hours)
     - **Testing strategy for each step**
     - **Definition of Done including test passing criteria**

5. **Technical Specifications**
   - Database schema
   - API endpoints
   - Authentication flow
   - TastyTrade sync mechanism (based on the SDK Implementation Guide)
   - Security considerations
   - **Testability considerations for each component**

6. **UI/UX Requirements**
   - Dashboard layout
   - Key screens
   - User flows
   - Bootstrap implementation guidelines
   - **UI component testing approach**

7. **Testing Requirements**
   - **Unit testing strategy and requirements**
     - Component-level test plans
     - Normal input test cases
     - Irregular/edge case test cases
     - Mocking strategies for external dependencies
   - **Integration testing approach**
     - Interface testing between components
     - Data flow validation
   - **End-to-end testing criteria**
     - User journey validation
     - System-wide workflows
   - **Automated testing framework**
     - Test automation tools and setup
     - CI/CD integration
   - **Manual testing requirements** (only where automation is impractical)
   - **Test reporting and documentation**

8. **Deployment Plan**
   - Heroku deployment steps
   - Database setup
   - Environment configuration
   - Monitoring setup
   - **Deployment validation tests**

## Risk Assessment Guidelines

For the risk assessment:
- **Risk Level 1-3**: Low complexity, well-understood tasks with minimal dependencies
- **Risk Level 4-5**: Moderate complexity or dependencies, but still manageable
- **Risk Level 6-8**: High complexity, external dependencies, or technical challenges
- **Risk Level 9-10**: Critical path items, unknown technologies, or potential blockers

For any task with risk > 5:
1. Identify the specific risk factors
2. Break down the task into smaller sub-tasks
3. Ensure each sub-task has a risk level < 5
4. Add specific mitigation strategies for each high-risk component
5. **Include detailed testing strategies to validate each sub-task**

## Testing Strategy Requirements

For each implementation step, include:

1. **Unit Testing Requirements**
   - Test cases for normal inputs/conditions
   - Test cases for irregular inputs/edge cases
   - Expected outcomes and assertions
   - Mocking requirements for dependencies
   - Minimum test coverage requirements

2. **Integration Testing** (for major steps or component combinations)
   - Interface testing between components
   - Data flow validation
   - Error handling across boundaries
   - Performance considerations

3. **End-to-End Testing** (for complete features)
   - User workflow validation
   - System behavior under various conditions
   - Cross-feature interactions

4. **Testing Tools and Automation**
   - Specify automated testing tools and frameworks
   - Define what (if anything) requires manual testing
   - Include test automation in the implementation steps

5. **Definition of Done**
   - All unit tests must pass
   - Integration tests must pass where applicable
   - End-to-end tests must pass for completed features
   - Test coverage meets minimum requirements
   - No critical bugs or issues remain

## Example Format

```
## Implementation Step: TastyTrade API Integration

### Description
Implement the core API integration with TastyTrade for data synchronization

### Risk Assessment: 8 (High)
- External API dependency
- Authentication complexity
- Data consistency challenges
- Error handling requirements

### Testing Strategy
- Unit tests for each API client method
- Integration tests for authentication flow
- End-to-end tests for complete sync process
- Automated testing using pytest
- Mock TastyTrade API responses for testing

### Broken Down Sub-steps:

1. **Setup API Authentication Framework** (Risk: 4)
   - Implement OAuth integration
   - Create secure credential storage
   - Implement session token management
   - Add retry logic for authentication failures
   
   **Testing Requirements:**
   - Unit tests for each authentication component
     - Test successful authentication flow
     - Test authentication with invalid credentials
     - Test token refresh mechanism
     - Test retry logic with simulated failures
   - Test coverage: minimum 90%
   - Automated tests using pytest
   - Definition of Done: All tests pass, authentication works with both valid and invalid credentials

2. **Implement Basic Account Data Retrieval** (Risk: 3)
   - Create account models
   - Implement basic GET requests
   - Add response parsing
   - Implement basic error handling
   
   **Testing Requirements:**
   - Unit tests for account models
     - Test model validation
     - Test serialization/deserialization
   - Unit tests for API client methods
     - Test with normal API responses
     - Test with malformed responses
     - Test error handling with various HTTP errors
   - Mock API responses for testing
   - Test coverage: minimum 85%
   - Definition of Done: All tests pass, retrieval works with both valid and error responses

3. **Develop Transaction Synchronization** (Risk: 4)
   - Create transaction models
   - Implement deduplication logic
   - Add transaction history retrieval
   - Implement data validation
   
   **Testing Requirements:**
   - Unit tests for transaction models
   - Unit tests for deduplication logic
     - Test with duplicate transactions
     - Test with unique transactions
     - Test edge cases (nearly identical transactions)
   - Integration tests for the complete sync process
   - Test coverage: minimum 90%
   - Definition of Done: All tests pass, deduplication correctly identifies and handles duplicates

4. **Build Position and Balance Sync** (Risk: 4)
   - Create position models
   - Implement current position retrieval
   - Add balance calculation logic
   - Implement data consistency checks
   
   **Testing Requirements:**
   - Unit tests for position models
   - Unit tests for balance calculations
     - Test with various account scenarios
     - Test with edge cases (zero balances, negative values)
   - Integration tests with transaction data
   - Test coverage: minimum 85%
   - Definition of Done: All tests pass, positions and balances are correctly calculated

5. **Implement Comprehensive Error Handling** (Risk: 4)
   - Add detailed logging
   - Implement exponential backoff
   - Create user-friendly error messages
   - Add monitoring alerts
   
   **Testing Requirements:**
   - Unit tests for each error handling component
   - Tests for various error scenarios
     - Network failures
     - API errors
     - Timeout conditions
   - Integration tests for error recovery
   - Test coverage: minimum 90%
   - Definition of Done: All tests pass, system handles and recovers from all error conditions

### Integration Testing for Complete API Integration
- Test end-to-end sync process with mock API
- Validate data consistency across all models
- Test performance with large data sets
- Verify error recovery across the entire process

### Definition of Done for TastyTrade API Integration
- All unit tests pass for each sub-component
- Integration tests pass for the complete sync process
- End-to-end tests validate the entire workflow
- Test coverage meets or exceeds requirements
- Code review completed
- Documentation updated
```

## Additional Instructions

- Maintain consistency with the Django monolith architecture
- Ensure all features from the original plans are included
- Add concrete acceptance criteria for each feature
- Include specific technical implementation details from the SDK guide
- Focus on making the sync functionality bulletproof as specified
- Ensure the PRD is actionable for developers with varying experience levels
- **Emphasize test-driven development throughout the implementation process**
- **Ensure each component has comprehensive unit tests with both normal and irregular inputs**
- **Include integration and end-to-end testing at major milestones**
- **Prioritize automated testing, with manual testing only where necessary**
- **Ensure testing is documented in the PRD with clear pass/fail criteria**
