# Prometheus & Grafana Monitoring Guide

Complete guide for monitoring your load-tester application and Kubernetes cluster.

---

## Quick Access

```bash
# From infra directory
make port-forward-prometheus     # http://localhost:9090
make port-forward-grafana        # http://localhost:3000 (admin/admin)
make port-forward-load-tester-frontend  # http://localhost:3001
```

---

## Prometheus Queries

### 1. Container CPU Usage

**Current CPU usage per container:**
```promql
rate(container_cpu_usage_seconds_total{namespace="load-tester"}[5m])
```

**CPU usage by pod:**
```promql
sum(rate(container_cpu_usage_seconds_total{namespace="load-tester"}[5m])) by (pod)
```

**CPU usage percentage (vs limits):**
```promql
100 * sum(rate(container_cpu_usage_seconds_total{namespace="load-tester"}[5m])) by (pod) 
/ 
sum(container_spec_cpu_quota{namespace="load-tester"}/container_spec_cpu_period{namespace="load-tester"}) by (pod)
```

### 2. Memory Usage

**Current memory usage:**
```promql
container_memory_usage_bytes{namespace="load-tester"}
```

**Memory usage by pod (MB):**
```promql
sum(container_memory_usage_bytes{namespace="load-tester"}) by (pod) / 1024 / 1024
```

**Memory usage percentage (vs limits):**
```promql
100 * sum(container_memory_usage_bytes{namespace="load-tester"}) by (pod)
/
sum(container_spec_memory_limit_bytes{namespace="load-tester"}) by (pod)
```

### 3. Pod Status & Restarts

**Pod restart count:**
```promql
kube_pod_container_status_restarts_total{namespace="load-tester"}
```

**Pods not running:**
```promql
kube_pod_status_phase{namespace="load-tester", phase!="Running"}
```

**Container restart rate (last 5m):**
```promql
rate(kube_pod_container_status_restarts_total{namespace="load-tester"}[5m])
```

### 4. Network Traffic

**Network receive rate (bytes/sec):**
```promql
rate(container_network_receive_bytes_total{namespace="load-tester"}[5m])
```

**Network transmit rate (bytes/sec):**
```promql
rate(container_network_transmit_bytes_total{namespace="load-tester"}[5m])
```

### 5. HTTP Metrics (if using ServiceMonitor)

**Request rate:**
```promql
rate(http_requests_total{namespace="load-tester"}[5m])
```

**Request duration (p95):**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{namespace="load-tester"}[5m]))
```

### 6. Cluster-Wide Metrics

**Total cluster CPU usage:**
```promql
sum(rate(container_cpu_usage_seconds_total[5m]))
```

**Total cluster memory usage (GB):**
```promql
sum(container_memory_usage_bytes) / 1024 / 1024 / 1024
```

**Node CPU usage:**
```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

**Node memory usage:**
```promql
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
```

### 7. Load Tester Specific

**Backend pod count:**
```promql
count(kube_pod_info{namespace="load-tester", pod=~"local-backend.*"})
```

**Frontend pod count:**
```promql
count(kube_pod_info{namespace="load-tester", pod=~"local-frontend.*"})
```

---

## Grafana Dashboards

### Import Pre-built Dashboards

1. **Open Grafana**: http://localhost:3000 (admin/admin)
2. **Navigate**: Dashboards → Import
3. **Import by ID**:

| Dashboard | ID | Description |
|-----------|-----|-------------|
| **Kubernetes Cluster Monitoring** | 7249 | Overall cluster health |
| **Kubernetes Pod Monitoring** | 6417 | Pod-level metrics |
| **Node Exporter Full** | 1860 | Node-level metrics |
| **Kubernetes Deployment** | 8588 | Deployment metrics |

### Create Custom Dashboard for Load Tester

1. **Create New Dashboard** → Add Visualization
2. **Add Panels** with these queries:

#### Panel 1: CPU Usage
- **Query**: `sum(rate(container_cpu_usage_seconds_total{namespace="load-tester"}[5m])) by (pod)`
- **Visualization**: Time series
- **Legend**: `{{pod}}`

#### Panel 2: Memory Usage
- **Query**: `sum(container_memory_usage_bytes{namespace="load-tester"}) by (pod) / 1024 / 1024`
- **Visualization**: Time series
- **Unit**: MB

#### Panel 3: Pod Status
- **Query**: `kube_pod_status_phase{namespace="load-tester"}`
- **Visualization**: Stat
- **Thresholds**: Green (Running), Red (Failed)

#### Panel 4: Restart Count
- **Query**: `sum(kube_pod_container_status_restarts_total{namespace="load-tester"}) by (pod)`
- **Visualization**: Stat

#### Panel 5: Network I/O
- **Query A**: `rate(container_network_receive_bytes_total{namespace="load-tester"}[5m])`
- **Query B**: `rate(container_network_transmit_bytes_total{namespace="load-tester"}[5m])`
- **Visualization**: Time series

---

## Alert Rules (PromQL)

### High CPU Usage
```promql
sum(rate(container_cpu_usage_seconds_total{namespace="load-tester"}[5m])) by (pod) > 0.8
```
**Trigger**: When CPU usage > 80%

### High Memory Usage
```promql
100 * sum(container_memory_usage_bytes{namespace="load-tester"}) by (pod)
/
sum(container_spec_memory_limit_bytes{namespace="load-tester"}) by (pod) > 90
```
**Trigger**: When memory usage > 90% of limit

### Pod Restarts
```promql
rate(kube_pod_container_status_restarts_total{namespace="load-tester"}[15m]) > 0
```
**Trigger**: Any restarts in last 15 minutes

### Pod Not Running
```promql
kube_pod_status_phase{namespace="load-tester", phase!="Running"} == 1
```
**Trigger**: Pod not in Running state

---

## Testing Your Monitoring

### Generate Load Spikes

1. **Open Load Tester**: http://localhost:3001
2. **Configure Interval**: 3 seconds, 1 minute duration
3. **Start CPU Interval**: Click "🔄 CPU Interval"
4. **Watch Metrics**:
   - Prometheus: CPU query should spike
   - Grafana: CPU panel should show increase

### Simulate Crashes

1. **Click "💀 Crash"** in Load Tester
2. **Watch**:
   - Pod restart count increases
   - Brief downtime in availability
   - New pod spins up

### Memory Stress

1. **Click "Memory (100MB)"** or use interval
2. **Watch**:
   - Memory usage increases
   - Should stay within limits

---

## Common Monitoring Patterns

### 1. Golden Signals (SRE)

**Latency**: Request duration
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Traffic**: Requests per second
```promql
rate(http_requests_total[5m])
```

**Errors**: Error rate
```promql
rate(http_requests_total{status=~"5.."}[5m])
```

**Saturation**: Resource usage
```promql
container_memory_usage_bytes / container_spec_memory_limit_bytes
```

### 2. RED Method (Requests, Errors, Duration)

**Rate**: Requests/sec
**Errors**: Error percentage
**Duration**: Latency percentiles

### 3. USE Method (Utilization, Saturation, Errors)

**Utilization**: % time resource busy
**Saturation**: Queue depth
**Errors**: Error count

---

## Grafana Tips

### Variables
Create dashboard variables for dynamic filtering:
- `namespace`: `label_values(kube_pod_info, namespace)`
- `pod`: `label_values(kube_pod_info{namespace="$namespace"}, pod)`

### Annotations
Mark events on graphs:
- Deployments
- Scaling events
- Incidents

### Alerts
Configure in Grafana:
1. Alert Rules → New Alert Rule
2. Set query and threshold
3. Configure notification channels (email, Slack, etc.)

---

## Next Steps

1. **Import Kubernetes dashboards** (IDs above)
2. **Create custom load-tester dashboard**
3. **Set up alerts** for critical metrics
4. **Test with load generation** from frontend
5. **Observe patterns** during stress tests
