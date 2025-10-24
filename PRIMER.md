# Operations & Maintenance Worktree Primer

## 🎯 Mission Objective

**Goal**: Create systemd services for ComfyUI instances, implement log routing and rotation, and build health checks and repair automation with dry-run capabilities. Focus on operational stability, monitoring, and automated maintenance procedures.

## 🚀 Immediate Action Items

### Phase 1: Service Management Infrastructure
1. **Systemd Service Creation**:
   - Create `comfyui@.service` template for multi-instance support
   - Develop `comfyui-monitor.service` for health monitoring
   - Implement `comfyui-logrotate.service` for log management
   - Design service dependency hierarchy and startup ordering

2. **Service Configuration**:
   - Environment-based service configuration (`/etc/default/comfyui`)
   - User permission setup and security hardening
   - Resource limits and cgroup integration
   - Restart policies and failure handling

### Phase 2: Log Management System
1. **Log Routing Architecture**:
   - Centralized logging with journald integration
   - Structured logging with JSON format for parsing
   - Log level filtering and routing rules
   - Remote logging capability for external monitoring

2. **Log Rotation & Retention**:
   - Implement logrotate configuration for ComfyUI logs
   - Set up compression and archival policies
   - Configure log retention periods and cleanup
   - Create log analysis and reporting tools

### Phase 3: Health Monitoring & Automation
1. **Health Check System**:
   - HTTP endpoint monitoring for API responsiveness
   - GPU/CPU/memory usage monitoring
   - Model loading validation and integrity checks
   - Network connectivity and port availability checks

2. **Repair Automation**:
   - Automatic service restart on failure
   - Resource cleanup and memory management
   - Model path validation and repair
   - Configuration consistency checking

## 📊 Success Criteria

### Must-Have Outcomes
- ✅ Working systemd services for all ComfyUI instances
- ✅ Centralized log management with rotation
- ✅ Automated health monitoring with alerts
- ✅ Self-healing capabilities with dry-run mode
- ✅ Resource monitoring and reporting

### Operations Deliverables
- `ops/services/comfyui@.service` - Multi-instance service template
- `ops/services/comfyui-monitor.service` - Health monitoring service
- `ops/logrotate/comfyui` - Log rotation configuration
- `ops/health/health-check.py` - Health validation script
- `ops/repair/auto-repair.py` - Automated repair system

## 🛠️ Available Commands in This Worktree

- `/ops:service-create` - Create systemd services
- `/ops:health-check` - Run health validation
- `/ops:logs-rotate` - Configure log rotation
- `/ops:monitor-start` - Start monitoring services
- `/ops:dry-run` - Test operations in dry-run mode

## 🤝 Agent Coordination

**Primary Agents**:
- **DevOps Engineer** (`cicd-engineer`): Systemd service creation, deployment automation
- **Monitoring Specialist** (`perf-analyzer`): Health checks, metrics collection, alerting
- **System Administrator** (`backend-dev`): Log management, user permissions, security

**Memory Storage**: `swarm/ops-maint/`
**Hook Integration**: All service changes and health events logged

## 📁 Service Architecture to Support

```
/etc/systemd/system/
├── comfyui@.service              # Multi-instance template
├── comfyui-monitor.service        # Health monitoring
├── comfyui-logrotate.service      # Log management
└── comfyui-repair.service         # Auto-repair system

/etc/default/
└── comfyui                       # Environment configuration

/var/log/comfyui/
├── env-setup.log                  # Environment setup logs
├── models-integ.log               # Model integration logs
└── ops-maint.log                  # Operations logs

/home/ned/ComfyUI-Install/trees/ops-maint/ops/
├── services/                      # Service definitions
├── health/                        # Health check scripts
├── repair/                        # Repair automation
├── monitoring/                    # Monitoring tools
└── logrotate/                     # Log rotation configs
```

## ⚠️ Constraints & Guidelines

- **NEVER** deploy services without testing in dry-run mode first
- **ALWAYS** provide rollback procedures for operational changes
- **DOCUMENT** all service dependencies and startup sequences
- **MONITOR** resource usage and set appropriate limits
- **SECURE** service configurations with proper user permissions

## 🔧 Service Template Structure

```ini
# ops/services/comfyui@.service example
[Unit]
Description=ComfyUI Instance (%i)
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=comfyui
Group=comfyui
Environment=COMFY_PORT=%i
Environment=COMFY_LOG=/var/log/comfyui/%i.log
Environment=WORKTREE_NAME=%i
WorkingDirectory=/home/ned/ComfyUI-Install/trees/%i
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 🔍 Health Check Matrix

| Check Type | Command | Frequency | Action on Failure |
|------------|---------|-----------|-------------------|
| HTTP Health | `curl -f http://localhost:%port/health` | 30s | Restart service |
| GPU Memory | `nvidia-smi --query-gpu=memory.used --format=csv` | 60s | Alert admin |
| Disk Space | `df -h /home/ned/Models` | 300s | Cleanup old logs |
| Model Paths | `ls /home/ned/Models/checkpoints` | 600s | Repair paths |

## 🔄 Dry-Run Capabilities

All repair operations MUST support dry-run mode:
```bash
# Test service configuration without applying changes
python ops/health/health-check.py --dry-run --service env-setup

# Validate log rotation without rotating
python ops/logrotate/validate.py --dry-run --config ops/logrotate/comfyui

# Simulate repair procedures
python ops/repair/auto-repair.py --dry-run --mode health-check
```

## 📈 Monitoring Metrics

**Essential Metrics to Collect**:
- Service uptime and restart counts
- Response times for API endpoints
- GPU utilization and memory usage
- Disk I/O and network throughput
- Model loading success/failure rates
- Log volume and error rates

## 🛡️ Security Considerations

**Service Security**:
- Run services as unprivileged user (`comfyui`)
- Use specific user groups for resource access
- Implement resource limits with cgroups
- Restrict network access with firewalld
- Secure log files with appropriate permissions

**Operational Security**:
- Never log sensitive information or model paths
- Implement log rotation to prevent disk exhaustion
- Use secure communication for remote monitoring
- Regular security updates and vulnerability scanning

## 🚨 Alert Thresholds

**Critical Alerts**:
- Service down for > 5 minutes
- GPU memory usage > 90% for > 10 minutes
- Disk space < 10% on model storage
- Model loading failures > 5 in 1 hour

**Warning Alerts**:
- High memory usage (> 80%) for > 30 minutes
- Slow response times (> 5s) for API calls
- Frequent service restarts (> 3/hour)
- Log volume exceeding expected rates

## 🔄 Next Steps After Completion

1. Deploy services to staging environment for testing
2. Validate health checks and repair automation
3. Set up monitoring dashboard and alerting
4. Document operational procedures and runbooks
5. Test failover and recovery scenarios

---

**Remember: This worktree handles operational stability. Focus on monitoring, automation, and maintaining service availability with minimal human intervention.**