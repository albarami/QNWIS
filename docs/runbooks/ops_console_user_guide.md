# Ops Console User Guide

## Overview

The QNWIS Ops Console is a web-based interface for monitoring and managing incidents and alerts. This guide covers common operator workflows for incident triage, acknowledgment, and resolution.

## Accessing the Console

### URL

```
https://<your-qnwis-domain>/ops
```

### Authentication

You must be authenticated with one of the following roles:
- **analyst**: Can view and manage incidents
- **admin**: Full access to all features
- **auditor**: Read-only access for auditing

### Navigation

The console navigation bar provides quick access to:
- **Dashboard**: Overview with incident statistics
- **Incidents**: List and manage incidents
- **Alerts**: View alert evaluation history

## Dashboard

The dashboard provides a high-level overview of your system health.

### Incident Statistics

**Total Incidents**: Current count of all incidents

**By State**:
- **OPEN**: Newly triggered, awaiting acknowledgment
- **ACK**: Acknowledged, being investigated
- **SILENCED**: Temporarily suppressed
- **RESOLVED**: Closed, no action needed

**By Severity**:
- **CRITICAL**: Immediate attention required
- **ERROR**: Significant issue, high priority
- **WARNING**: Potential problem, monitor closely
- **INFO**: Informational, no immediate action

### Quick Actions

- **View All Incidents**: Navigate to full incident list
- **Open Incidents**: Filter for unresolved incidents
- **Alert History**: View recent alert evaluations

### Live Updates

The dashboard includes a live feed showing real-time incident state changes. Updates appear automatically without page refresh.

## Incident List

### Viewing Incidents

Navigate to **Incidents** in the navigation bar to see all incidents.

**Table Columns**:
- **ID**: Unique incident identifier (first 8 characters)
- **Rule**: Alert rule that triggered the incident
- **Severity**: Critical, Error, Warning, or Info
- **State**: Current incident state
- **Message**: Description of the issue
- **Window**: Time range of the alert
- **Actions**: Quick links to detail page

### Filtering Incidents

Use the filter form at the top of the page:

**By State**:
```
State: [Open ▼]  → Show only open incidents
```

**By Severity**:
```
Severity: [Critical ▼]  → Show only critical incidents
```

**By Rule**:
```
Rule ID: [high_turnover]  → Filter by specific rule
```

Click **Apply Filters** to update the list.

### Sorting

Incidents are sorted by creation time (most recent first) by default.

## Incident Detail

Click on any incident ID or the **Details** button to view full information.

### Overview Section

**Incident Information**:
- Incident ID (full)
- Rule ID
- Severity badge
- Current state
- Alert message
- Time window
- Creation and update timestamps

**Audit Pack Link** (if available):
- Link to associated audit evidence and analysis

### Timeline Section

Visual timeline showing incident lifecycle events:

**Events**:
- **CREATED**: When incident was first triggered
- **ACK**: When operator acknowledged
- **SILENCED**: When incident was silenced (if applicable)
- **RESOLVED**: When incident was closed

Each event includes:
- Timestamp
- Actor (user who performed the action)

### Actions Section

Available actions depend on the current incident state:

#### Acknowledge Incident

**When**: Incident is in OPEN state  
**Effect**: Changes state to ACK, indicating investigation has started

```
[Acknowledge Incident] button
```

**Use Case**: You've reviewed the incident and are investigating the root cause.

#### Resolve Incident

**When**: Any non-RESOLVED state  
**Effect**: Closes the incident

```
Resolution Note: [Optional description of fix]
[Resolve Incident] button
```

**Use Case**: 
- Issue has been fixed
- False positive confirmed
- Alert conditions have returned to normal

**Best Practice**: Always add a resolution note explaining:
- What was found
- What action was taken
- Any follow-up needed

Example: "Fixed by restarting worker-03. Root cause was memory leak in v2.3.1. Upgrading to v2.3.2 in next deployment."

#### Silence Incident

**When**: Any non-RESOLVED state  
**Effect**: Suppresses notifications until specified time

```
Silence Until: [2024-01-15 23:59]  (date/time picker)
Reason: [Planned maintenance window]
[Silence Incident] button
```

**Use Case**:
- Planned maintenance
- Known issue with delayed fix
- Alert during expected system changes

**Best Practice**: Always provide a clear reason for silencing.

### Metadata Section

Shows additional incident metadata:
- Custom fields
- Alert scope
- Evidence data

## Common Workflows

### Workflow 1: Triage New Incident

**Goal**: Assess and acknowledge a new critical incident

1. **Notification Received**: Check email/Teams for alert notification
2. **Navigate to Console**: Go to Dashboard or Incidents list
3. **Locate Incident**: Find incident by ID or filter by rule/severity
4. **Open Detail**: Click incident ID to view full details
5. **Review Information**:
   - Read alert message
   - Check time window
   - Review scope (sector, occupation, etc.)
6. **Acknowledge**: Click "Acknowledge Incident" button
7. **Begin Investigation**: Use detail page as reference

### Workflow 2: Resolve False Positive

**Goal**: Close an incident that was incorrectly triggered

1. **Open Incident**: Navigate to incident detail page
2. **Verify False Positive**: Check alert conditions and data
3. **Resolve with Note**:
   ```
   Resolution Note: False positive. Turnover spike due to scheduled contractor end dates. No actual retention issue.
   ```
4. **Click Resolve**: Incident closes and is logged
5. **Follow Up**: If pattern persists, consider tuning alert rule

### Workflow 3: Silence During Maintenance

**Goal**: Suppress alerts during planned system maintenance

1. **Before Maintenance**: Navigate to related incidents
2. **For Each Incident**:
   - Open detail page
   - Click "Silence Incident"
   - Set "Silence Until" to maintenance end time + buffer (e.g., +30 minutes)
   - Provide reason: "Planned maintenance: Q1 data pipeline upgrade"
   - Submit
3. **After Maintenance**: Check that incidents auto-unsilence or manually resolve if issue is fixed

### Workflow 4: Escalate to Team

**Goal**: Document incident and share with team for investigation

1. **Open Incident**: View incident detail page
2. **Copy Information**:
   - Incident ID
   - Alert message
   - Audit pack link (if available)
3. **Acknowledge Incident**: Mark as being investigated
4. **Share in Teams/Slack**:
   ```
   🚨 Critical Incident: inc_abc123
   
   High turnover detected in Construction sector (010)
   
   Details: https://qnwis.example.com/ops/incidents/inc_abc123
   Audit Pack: https://qnwis.example.com/audit_packs/abc-def-123
   
   Investigating...
   ```
5. **Update as Investigation Progresses**: Add notes in chat
6. **Resolve When Fixed**: Return to console and resolve with summary note

### Workflow 5: Monitor Incident Trends

**Goal**: Identify patterns in recurring incidents

1. **Navigate to Incidents List**: Click "Incidents" in nav bar
2. **Filter by Rule**:
   ```
   Rule ID: high_turnover
   ```
3. **Review List**: Check frequency and distribution
4. **Analyze Patterns**:
   - Which sectors trigger most often?
   - What times of day?
   - Resolution patterns?
5. **Take Action**:
   - Adjust alert thresholds if too sensitive
   - Investigate systemic issues if pattern is real
   - Document findings for team review

## Live Updates

### Server-Sent Events (SSE)

The console uses SSE to push real-time updates to your browser. No page refresh needed.

**Connection Indicator**: Look for "Connected. Waiting for updates..." in the live feed area.

**What Gets Updated**:
- Incident state changes (ACK, RESOLVED, etc.)
- New incidents (if triggered while viewing)

**Reconnection**: If connection drops (network issue, server restart), the browser automatically reconnects.

**Browser Compatibility**: SSE works in all modern browsers (Chrome, Firefox, Safari, Edge).

## Keyboard Shortcuts

While no custom shortcuts are defined, standard browser shortcuts work:

- **Ctrl+F / Cmd+F**: Find on page
- **Ctrl+R / Cmd+R**: Refresh page
- **Tab**: Navigate between form fields
- **Enter**: Submit focused button

## Accessibility Features

The ops console is designed for accessibility:

### Screen Readers

All elements are properly labeled:
- Form inputs have associated `<label>` elements
- Images have alternative text
- Page regions use ARIA landmarks

### Keyboard Navigation

- All interactive elements are keyboard accessible
- Focus indicators are clearly visible (3px blue outline)
- Logical tab order

### High Contrast

Color palette meets WCAG 2.1 AA standards:
- Text contrast ratio ≥ 4.5:1
- Interactive element contrast ≥ 3:1

### Zoom

Interface remains usable up to 200% browser zoom.

## Troubleshooting

### "CSRF token invalid or expired"

**Cause**: Security token expired (15-minute TTL)

**Solution**: Refresh the page to get a new token, then retry action.

### Live updates not working

**Cause**: SSE connection issue

**Solutions**:
1. Check browser console for errors
2. Verify network connectivity
3. Try refreshing the page
4. Check with admin if issue persists

### Cannot perform action (403 Forbidden)

**Cause**: Insufficient permissions

**Solution**: 
- Check your assigned role (shown in nav bar)
- Contact admin to request appropriate role
- Auditors have read-only access

### Incident not found (404)

**Cause**: Incident ID doesn't exist or was deleted

**Solution**:
- Verify incident ID is correct
- Check if incident was archived
- Contact admin if you believe this is an error

## Best Practices

### Acknowledgment

✅ **Do**:
- Acknowledge incidents promptly after reviewing
- Use acknowledgment to claim ownership of investigation

❌ **Don't**:
- Acknowledge without reviewing details
- Leave critical incidents unacknowledged for extended periods

### Resolution Notes

✅ **Do**:
- Write clear, actionable resolution notes
- Include what was found, what was done, and any follow-up
- Reference related tickets or documentation

❌ **Don't**:
- Leave resolution note blank for non-trivial incidents
- Use vague notes like "Fixed" or "Done"

### Silencing

✅ **Do**:
- Use silencing for known, temporary situations
- Always provide a reason
- Set realistic silence duration
- Document in team chat if silencing major incident

❌ **Don't**:
- Silence indefinitely
- Silence without explaining why
- Use silencing as a substitute for fixing the issue

## Security

### CSRF Protection

All actions (Acknowledge, Resolve, Silence) require a CSRF token. This prevents malicious sites from performing actions on your behalf.

**User Impact**: None. Tokens are automatically included in forms.

### Session Management

**Idle Timeout**: Sessions expire after inactivity (configured by admin)

**Multiple Tabs**: You can have multiple tabs open. Actions in one tab may update data in others via live updates.

**Logout**: Click your user name (if logout link is present) or close browser.

### Audit Trail

All actions are logged with:
- Your user ID
- Request ID (shown in footer)
- Timestamp
- Action details

This ensures accountability and enables security audits.

## Support

### Getting Help

**Technical Issues**:
- Contact your IT support team
- Reference error messages and request IDs from page footer

**Process Questions**:
- Consult team lead or incident response coordinator
- Review team incident response playbook

**Feature Requests**:
- Submit via your team's feedback channel
- Include specific use case and expected behavior

### Reporting Bugs

When reporting issues:
1. **Describe what happened**: Expected vs. actual behavior
2. **Include details**:
   - URL of page
   - Request ID from footer
   - Browser and version
   - Steps to reproduce
3. **Attach screenshot** if visual issue
4. **Check browser console** for error messages (F12 → Console tab)

## Appendix

### Incident State Definitions

| State | Description | Typical Duration |
|-------|-------------|------------------|
| OPEN | Newly triggered, needs acknowledgment | Minutes |
| ACK | Investigation in progress | Hours |
| SILENCED | Temporarily suppressed | Hours to Days |
| RESOLVED | Closed, no further action | Permanent |

### Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| CRITICAL | System-wide impact, immediate action required | < 15 minutes |
| ERROR | Significant issue, high priority | < 1 hour |
| WARNING | Potential problem, investigate soon | < 4 hours |
| INFO | Informational, no immediate action | < 24 hours |

### Common Alert Rules

| Rule ID | Description | Typical Cause |
|---------|-------------|---------------|
| high_turnover | Turnover rate exceeds threshold | Layoffs, mass resignations |
| yoy_decline | Year-over-year employment decline | Economic downturn, sector contraction |
| foreclosure_spike | Rapid increase in business closures | Regulatory changes, market shifts |
| wage_pressure | Significant wage growth | Talent shortage, inflation |

---

**Document Version**: 1.0  
**Last Updated**: Step 30 Implementation  
**Maintained By**: QNWIS Ops Team
