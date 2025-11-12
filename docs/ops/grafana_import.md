# Grafana Dashboard Import Guide

## Overview

The `qnwis_ops.json` dashboard provides comprehensive monitoring for the QNWIS ops console,
including notifications, incidents, performance metrics, and cache statistics.

## Prerequisites

- Grafana 9.0+ installed and accessible
- Prometheus data source configured in Grafana
- QNWIS metrics endpoint exposed to Prometheus scraper

## Import Steps

### 1. Access Grafana UI

Navigate to your Grafana instance (typically `http://localhost:3000`).

### 2. Import Dashboard

1. Click the **+** icon in the left sidebar
2. Select **Import**
3. Choose **Upload JSON file**
4. Select `grafana/dashboards/qnwis_ops.json`
5. Click **Load**

### 3. Configure Data Source

On the import screen:

1. Select your Prometheus data source from the dropdown
2. Update the **datasource** variable if needed
3. Click **Import**

### 4. Verify Metrics

After import, verify that panels are populated:

- Check that notification metrics show data
- Verify incident counts are visible
- Confirm latency panels display percentiles

## Dashboard Variables

The dashboard includes two template variables:

### datasource

- **Type**: Data source
- **Default**: Prometheus
- **Usage**: Select the Prometheus instance to query

### interval

- **Type**: Interval
- **Default**: 5m
- **Options**: 30s, 1m, 5m, 15m, 30m, 1h
- **Usage**: Aggregation window for rate calculations

To change variables:

1. Click the variable dropdown at the top of the dashboard
2. Select desired value
3. Dashboard will refresh automatically

## Panel Descriptions

### Notifications Sent (Rate)

- **Metric**: `qnwis_notifications_sent_total`
- **Visualization**: Time series graph
- **Labels**: `channel`, `severity`
- **Description**: Rate of notifications dispatched per channel and severity

### Notification Failures

- **Metric**: `qnwis_notifications_failed_total`
- **Visualization**: Time series graph with alert
- **Labels**: `channel`, `reason`
- **Alert**: Triggers if failures exceed 5/sec over 5 minutes
- **Description**: Rate of failed notification deliveries

### Notification Retries

- **Metric**: `qnwis_notifications_retried_total`
- **Visualization**: Time series graph
- **Labels**: `channel`
- **Description**: Retry attempts per channel

### Incident Lifecycle Counts

- **Metric**: `qnwis_incidents_total`
- **Visualization**: Stat panel with background colors
- **Labels**: `state` (OPEN, ACK, SILENCED, RESOLVED)
- **Description**: Current incident counts by state

### Notification Dispatch Latency

- **Metric**: `qnwis_notification_dispatch_duration_seconds`
- **Visualization**: Time series graph with threshold line
- **Quantiles**: p50, p95, p99
- **Threshold**: 50ms (red line)
- **Description**: End-to-end dispatch latency distribution

### Notification Routing Latency

- **Metric**: `qnwis_notification_route_duration_seconds`
- **Visualization**: Time series graph with threshold line
- **Quantiles**: p50, p95, p99
- **Threshold**: 60ms (red line)
- **Description**: Channel routing decision latency

### Ops Console Page Render Latency

- **Metric**: `qnwis_ops_console_render_duration_ms`
- **Visualization**: Time series graph with threshold line
- **Quantiles**: p50, p95, p99
- **Threshold**: 150ms (red line)
- **Description**: Server-side page rendering duration

### Cache Hit Rate

- **Metric**: `qnwis_cache_hits_total / (qnwis_cache_hits_total + qnwis_cache_misses_total)`
- **Visualization**: Gauge
- **Thresholds**:
  - Red: < 70%
  - Yellow: 70-90%
  - Green: > 90%
- **Description**: Cache effectiveness percentage

### SSE Connections Active

- **Metric**: `qnwis_sse_connections_active`
- **Visualization**: Stat panel
- **Description**: Number of active server-sent event streams

### CSRF Token Validation Failures

- **Metric**: `qnwis_csrf_validation_failures_total`
- **Visualization**: Stat panel with thresholds
- **Thresholds**:
  - Green: 0
  - Yellow: 1-5
  - Red: > 5
- **Description**: Rate of CSRF validation failures (potential security issues)

### Ops Console Requests by Endpoint

- **Metric**: `qnwis_ops_console_requests_total`
- **Visualization**: Table
- **Labels**: `endpoint`
- **Description**: Request rate per ops console endpoint

### Alert Evaluations by Rule

- **Metric**: `qnwis_alert_evaluations_total`
- **Visualization**: Table
- **Labels**: `rule_id`, `triggered`
- **Description**: Alert rule evaluation frequency and trigger status

## Annotations

The dashboard includes deployment annotations:

- **Source**: `changes(qnwis_build_info[5m])`
- **Display**: Vertical line at deployment time
- **Label**: Version number from build info

## Customization

### Adding Panels

1. Click **Add panel** in dashboard edit mode
2. Select **Add a new panel**
3. Configure metric query using Prometheus syntax
4. Save dashboard

### Modifying Thresholds

1. Edit panel in question
2. Navigate to **Thresholds** section in panel settings
3. Adjust threshold values and colors
4. Apply changes

### Exporting Modified Dashboard

1. Click dashboard settings (gear icon)
2. Select **JSON Model**
3. Copy JSON content
4. Save to `grafana/dashboards/qnwis_ops.json`
5. Commit to version control

## Troubleshooting

### No Data in Panels

**Issue**: Panels show "No data"

**Solutions**:
1. Verify Prometheus data source is correctly configured
2. Check that QNWIS metrics endpoint is being scraped
3. Confirm metric names match (run query in Prometheus UI)
4. Verify time range includes data (check "Last 1 hour" dropdown)

### High Cardinality Warning

**Issue**: Grafana warns about high cardinality queries

**Solutions**:
1. Add label filters to reduce cardinality
2. Increase aggregation interval (use `$interval` variable)
3. Use recording rules in Prometheus for expensive queries

### Incorrect Percentiles

**Issue**: p95/p99 latency values seem wrong

**Solutions**:
1. Verify histogram buckets are appropriate for your latency range
2. Check that `rate()` function uses correct interval (>= 2x scrape interval)
3. Ensure sufficient data points (at least 10 samples)

### Dashboard Refresh Issues

**Issue**: Dashboard doesn't auto-refresh

**Solutions**:
1. Check refresh interval setting (top-right dropdown)
2. Verify browser isn't blocking background requests
3. Ensure Prometheus connection is stable

## Alerting

To create alerts from dashboard panels:

1. Edit panel with alert
2. Click **Alert** tab
3. Configure alert conditions
4. Set up notification channels (email, Slack, etc.)
5. Save alert rule

Recommended alerts:

- **High Notification Failure Rate**: > 5 failures/sec for 5 minutes
- **Slow Ops Console**: p95 render latency > 150ms for 10 minutes
- **High CSRF Failures**: > 10 failures/sec for 2 minutes (security)
- **Cache Hit Rate Low**: < 70% for 15 minutes

## Best Practices

1. **Use Variables**: Leverage datasource and interval variables for flexibility
2. **Document Changes**: Update this guide when modifying dashboard
3. **Version Control**: Keep `qnwis_ops.json` in Git for change tracking
4. **Test Queries**: Validate Prometheus queries before adding to dashboard
5. **Set Alerts**: Configure alerts for critical metrics
6. **Regular Review**: Check dashboard monthly for relevance and accuracy

## References

- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Performance Metrics Reference](../PERFORMANCE.md)
