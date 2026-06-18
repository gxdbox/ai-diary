# Prometheus 告警规则说明

本文档描述 AI Diary 项目的 Prometheus 告警规则配置。

## 配置文件位置

- **告警规则**: `alert_rules.yml`
- **Prometheus 配置**: `prometheus.yml`
- **监控服务编排**: `docker-compose.monitoring.yml`

## 告警规则列表

### 1. InstanceDown (服务宕机)

**级别**: `critical`  
**持续时间**: 1分钟  
**表达式**: `up == 0`

当 AI Diary 后端服务无法被 Prometheus 抓取时触发此告警。

**处理建议**:
- 检查服务是否正在运行: `ps aux | grep uvicorn`
- 查看服务日志: `docker logs ai-diary-backend`
- 检查端口占用: `lsof -i :8000`

---

### 2. HighErrorRate (高错误率)

**级别**: `warning`  
**持续时间**: 5分钟  
**表达式**: HTTP 5xx 错误率 > 5%

当后端 API 的 HTTP 5xx 错误率超过 5% 时触发。

**处理建议**:
- 查看应用日志定位错误原因
- 检查数据库连接是否正常
- 验证外部依赖服务(如 DeepSeek API)是否可用

---

### 3. HighResponseTime (高响应时间)

**级别**: `warning`  
**持续时间**: 5分钟  
**表达式**: P95 响应时间 > 2秒

当 95% 的请求响应时间超过 2 秒时触发。

**处理建议**:
- 检查慢查询日志
- 分析性能瓶颈(CPU/内存/磁盘 I/O)
- 考虑优化数据库索引或缓存策略

---

### 4. DiskSpaceLow (磁盘空间不足)

**级别**: `critical`  
**持续时间**: 5分钟  
**表达式**: 可用磁盘空间 < 10%

当服务器磁盘使用率超过 90% 时触发。

**处理建议**:
- 清理旧日志文件: `/var/log/`
- 清理 Docker 无用镜像: `docker system prune -a`
- 清理临时文件: `/tmp/`
- 检查数据库文件大小

---

### 5. HighMemoryUsage (内存使用率过高)

**级别**: `warning`  
**持续时间**: 5分钟  
**表达式**: 内存使用率 > 85%

当服务器内存使用率超过 85% 时触发。

**处理建议**:
- 检查内存泄漏: `top` 或 `htop`
- 重启占用过多内存的服务
- 增加服务器内存或优化应用内存使用

---

### 6. HighCPUUsage (CPU 使用率过高)

**级别**: `warning`  
**持续时间**: 5分钟  
**表达式**: CPU 使用率 > 80%

当服务器 CPU 使用率持续超过 80% 时触发。

**处理建议**:
- 识别高 CPU 占用进程: `top -o cpu`
- 检查是否有死循环或计算密集型任务
- 考虑水平扩展或优化算法

---

## 部署和更新

### 首次部署

```bash
# 1. 启动监控栈（Prometheus + Grafana）
docker-compose -f docker-compose.monitoring.yml up -d prometheus grafana

# 2. （可选）部署 Node Exporter 用于系统指标采集
# 注意：由于网络限制，可能需要手动拉取镜像或配置代理
docker pull prom/node-exporter:v1.6.1
docker-compose -f docker-compose.monitoring.yml up -d node-exporter

# 3. 验证 Prometheus 运行状态
curl http://localhost:9090/-/ready

# 4. 访问 Prometheus UI
open http://localhost:9090
```

### 更新告警规则

```bash
# 1. 修改 alert_rules.yml

# 2. 上传到服务器
scp alert_rules.yml root@8.136.124.182:~/ai-diary/
scp prometheus.yml root@8.136.124.182:~/ai-diary/

# 3. 重载 Prometheus 配置(无需重启)
ssh root@8.136.124.182 "cd ~/ai-diary && docker-compose -f docker-compose.monitoring.yml exec prometheus kill -HUP 1"

# 4. 验证规则加载
curl http://localhost:9090/api/v1/rules
```

### 重启监控栈

```bash
# 完全重启(仅在必要时)
docker-compose -f docker-compose.monitoring.yml down
docker-compose -f docker-compose.monitoring.yml up -d
```

---

## 监控指标来源

| 指标类型 | 来源 | 端口 |
|---------|------|------|
| 应用指标 | AI Diary Backend (`/metrics`) | 8000 |
| 系统指标 | Node Exporter | 9100 |

---

## Grafana 可视化

Grafana 已配置在端口 `3002`:

- **URL**: `http://8.136.124.182:3002`
- **默认账号**: `admin`
- **默认密码**: `ai-diary-admin-2026`

建议在 Grafana 中导入以下 Dashboard:
- Node Exporter Full (ID: 1860)
- Prometheus Stats (ID: 3662)

---

## 故障排查

### Prometheus 无法抓取目标

```bash
# 检查目标状态
curl http://localhost:9090/api/v1/targets

# 查看 Prometheus 日志
docker logs ai-diary-prometheus
```

### 告警未触发

```bash
# 检查规则是否加载
curl http://localhost:9090/api/v1/rules

# 手动测试表达式
curl "http://localhost:9090/api/v1/query?query=up"
```

### Node Exporter 无数据

```bash
# 检查容器状态
docker ps | grep node-exporter

# 查看日志
docker logs ai-diary-node-exporter

# 验证指标端点
curl http://localhost:9100/metrics
```

---

## 参考资源

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [告警规则配置](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Node Exporter](https://github.com/prometheus/node_exporter)
- [PromQL 查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
