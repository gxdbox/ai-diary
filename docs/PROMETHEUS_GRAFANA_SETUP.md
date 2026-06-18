# Prometheus + Grafana 监控配置指南

## 访问地址

- **Prometheus**: http://8.136.124.182:9090
- **Grafana**: http://8.136.124.182:3002 (默认账号: admin, 密码: ai-diary-admin-2026)

> **注意**: Grafana 使用 3002 端口(而非默认的 3000),因为服务器上 3000 端口已被其他服务占用。如需从外部访问 Grafana,需要在阿里云安全组中开放 3002 端口。

## 部署架构

```
┌─────────────────┐
│  AI Diary API   │ :8000
│  (FastAPI)      │
└────────┬────────┘
         │ /metrics
         ▼
┌─────────────────┐
│   Prometheus    │ :9090
│  (每15秒抓取)    │
└────────┬────────┘
         │ 查询
         ▼
┌─────────────────┐
│    Grafana      │ :3002
│  (可视化面板)    │
└─────────────────┘
```

## 配置文件说明

### docker-compose.monitoring.yml
定义 Prometheus 和 Grafana 容器服务,包括:
- 镜像版本、端口映射
- 数据卷持久化
- 网络配置

### prometheus.yml
Prometheus 主配置文件,定义了:
- 全局抓取间隔: 15秒
- 告警规则文件路径
- 抓取目标: AI Diary 后端 (/metrics)

### alert_rules.yml
告警规则文件(当前为占位配置,P2-16 任务会完善):
- InstanceDown: 实例宕机告警

## 配置 Grafana Dashboard

### 方式1: 导入现成模板(推荐)

1. 登录 Grafana (http://8.136.124.182:3002)
2. 点击左侧菜单 → Dashboards → Import
3. 输入模板 ID: **13609** (FastAPI Dashboard)
4. 选择 Prometheus 数据源
5. 点击 Import

### 方式2: 手动创建 Dashboard

1. 点击 New Dashboard
2. 添加 Panel,使用以下 PromQL 查询:

**HTTP 请求总数**:
```promql
sum(rate(http_requests_total[5m])) by (handler, status)
```

**平均响应时间**:
```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

**错误率**:
```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```

## 常用 PromQL 查询

| 指标 | PromQL 查询 |
|------|------------|
| QPS | `sum(rate(http_requests_total[1m]))` |
| P95 响应时间 | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` |
| P99 响应时间 | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` |
| 活跃连接数 | `process_open_fds` |
| CPU 使用率 | `rate(process_cpu_seconds_total[1m]) * 100` |
| 内存使用(MB) | `process_resident_memory_bytes / 1024 / 1024` |
| 错误率(%) | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100` |

## 管理命令

### 启动监控栈
```bash
cd ~/ai-diary
docker compose -f docker-compose.monitoring.yml up -d
```

### 停止监控栈
```bash
cd ~/ai-diary
docker compose -f docker-compose.monitoring.yml down
```

### 查看日志
```bash
# Prometheus 日志
podman logs ai-diary-prometheus --tail 50

# Grafana 日志
podman logs ai-diary-grafana --tail 50
```

### 重启服务
```bash
# 重启 Prometheus
podman restart ai-diary-prometheus

# 重启 Grafana
podman restart ai-diary-grafana
```

### 重新加载 Prometheus 配置(无需重启)
```bash
curl -X POST http://localhost:9090/-/reload
```

## 故障排查

### Prometheus 无法抓取数据

1. 检查 target 状态:
   ```bash
   curl -s 'http://localhost:9090/api/v1/targets' | python3 -m json.tool
   ```

2. 确认 AI Diary 后端正在运行:
   ```bash
   curl http://localhost:8000/metrics
   ```

3. 检查 `prometheus.yml` 中的 targets 配置是否正确

### Grafana 无法连接 Prometheus

1. 检查 Prometheus 是否正常运行:
   ```bash
   podman ps | grep prometheus
   ```

2. 在 Grafana 中添加数据源:
   - Configuration → Data Sources → Add data source
   - 选择 Prometheus
   - URL: `http://ai-diary-prometheus:9090` (Docker 内部网络)
   - 点击 Save & Test

### Grafana 无法从外部访问

1. 检查阿里云安全组是否开放 3002 端口
2. 检查防火墙规则:
   ```bash
   iptables -L -n | grep 3002
   ```

### 磁盘空间不足

Prometheus 数据保留 30 天,如果磁盘空间紧张,可以:
1. 修改 `docker-compose.monitoring.yml` 中的 `--storage.tsdb.retention.time=15d`
2. 重启 Prometheus:
   ```bash
   podman restart ai-diary-prometheus
   ```

## 数据安全

- **Grafana 管理员密码**: `ai-diary-admin-2026` (生产环境建议修改)
- **Prometheus 数据**: 存储在 Docker volume `prometheus_data`,重启后不会丢失
- **Grafana 配置**: 存储在 Docker volume `grafana_data`,包括 Dashboard 和数据源配置

## 下一步

- [P2-16] 完善告警规则(alert_rules.yml)
- [P2-17] 配置钉钉/企业微信告警通知
- [P2-18] 创建自定义 Dashboard 监控业务指标
