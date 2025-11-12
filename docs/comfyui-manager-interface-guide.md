# ComfyUI-Manager Interface System Guide

## Overview

This guide documents the comprehensive interface system for monitoring and managing ComfyUI-Manager and custom nodes. The system provides both directory-based monitoring and API-level integration with ComfyUI-Manager.

## System Architecture

### Components

1. **Directory Scanner** (`comfyui_nodes_scanner.py`)
   - Monitors `custom_nodes` directory for changes
   - Scans node metadata (git info, requirements, file counts)
   - Exports inventory data

2. **API Client** (`comfyui_manager_api_client.py`)
   - Connects to ComfyUI-Manager REST API
   - Retrieves installed nodes and registry information
   - Supports monitoring and automation

3. **Advanced Interface** (`comfyui_manager_interface.py`)
   - Comprehensive monitoring with file system events
   - Real-time change detection
   - Health checks and validation

## Installation & Setup

### Prerequisites

```bash
# Basic requirements (Ubuntu/Debian)
sudo apt update
sudo apt install python3 python3-pip git

# Python packages (optional - for advanced features)
pip3 install --user pyyaml watchdog requests gitpython
```

### Quick Start

1. **Basic Directory Scanning**:
```bash
cd /home/ned/ComfyUI-Install
python3 scripts/comfyui_nodes_scanner.py
```

2. **API Client Demo**:
```bash
python3 src/comfyui_manager_api_client.py
```

3. **Real-time Monitoring** (requires additional packages):
```bash
python3 scripts/comfyui_manager_monitor.py monitor
```

## Usage Examples

### 1. Scan and Export Custom Nodes

```bash
# Basic scan
python3 scripts/comfyui_nodes_scanner.py scan

# Detailed scan with full information
python3 scripts/comfyui_nodes_scanner.py scan --detailed
```

**Output:**
```
🔍 Scanning custom nodes in: /home/ned/ComfyUI-Install/ComfyUI/custom_nodes
📊 **Custom Nodes Summary**
   Total nodes: 21
   Total size: 228.7 MB
   Git repositories: 6
   With requirements: 12
   Python files: 445

📦 **Individual Nodes**
   🔧 ComfyUI-Civitai-Toolkit
      Size: 7.8 MB
      Git: https://github.com/BAIKEMARK/ComfyUI-Civitai-Toolkit
      Features: ⚙️requirements install script
```

### 2. Test API Connectivity

```bash
python3 scripts/comfyui_nodes_scanner.py  # Includes API test
```

**Output:**
```
🔌 Testing ComfyUI Manager API...
✅ API connected successfully: 19 items returned
📋 API responded with data
```

### 3. Export Node Inventory

```python
from src.comfyui_manager_interface import ComfyUIManagerInterface

# Initialize interface
manager = ComfyUIManagerInterface()

# Scan and export
nodes = manager.scan_all_nodes()
manager.export_node_inventory("/path/to/export/dir")
```

**Generated Files:**
- `custom_nodes_inventory.json` - Machine-readable format
- `custom_nodes_inventory.yaml` - Human-readable format

### 4. Monitor for Changes

```python
from src.comfyui_manager_interface import ComfyUIManagerInterface

# Start monitoring (requires watchdog package)
config = ComfyUIManagerConfig(enable_file_watcher=True)

with ComfyUIManagerInterface(config) as manager:
    manager.start_monitoring()
    # Monitoring continues until interrupted
```

## API Endpoints

The interface can access the following ComfyUI-Manager API endpoints:

| Endpoint | Description | Status |
|----------|-------------|--------|
| `/customnode/installed` | Get installed nodes | ✅ Working |
| `/customnode/getlist` | Get available nodes | ⚠️ Sometimes 500 error |
| `/customnode/getmappings` | Get node mappings | ⚠️ Sometimes 500 error |
| `/customnode/fetch_updates` | Check for updates | ⚠️ Requires parameters |
| `/customnode/alternatives` | Get alternative nodes | Untested |
| `/snapshot/getlist` | Get saved snapshots | ✅ Working |
| `/externalmodel/getlist` | Get external models | Untested |
| `/manager/queue/update_all` | Update all nodes | Untested |

## Configuration

### Scanner Configuration

Create `/home/ned/ComfyUI-Install/config/custom_nodes/custom_nodes_tracker.yaml`:

```yaml
monitoring:
  enabled: true
  check_interval: 60
  enable_file_watcher: true
  log_changes: true

api:
  base_url: "http://localhost:8188"
  timeout: 30
  retry_attempts: 3

paths:
  comfyui_install: "/home/ned/ComfyUI-Install/ComfyUI"
  custom_nodes: "/home/ned/ComfyUI-Install/ComfyUI/custom_nodes"
  export_dir: "/home/ned/ComfyUI-Install/config/custom_nodes"
```

### Advanced Interface Configuration

```python
from src.comfyui_manager_interface import ComfyUIManagerConfig

config = ComfyUIManagerConfig(
    server_host="localhost",
    server_port=8188,
    monitoring_interval=60,
    enable_file_watcher=True,
    log_level="INFO"
)
```

## Data Export Formats

### JSON Export

```json
{
  "export_timestamp": "2025-10-07T23:59:46.870592",
  "custom_nodes_path": "/home/ned/ComfyUI-Install/ComfyUI/custom_nodes",
  "nodes": {
    "ComfyUI-Manager": {
      "name": "ComfyUI-Manager",
      "path": "/home/ned/ComfyUI-Install/ComfyUI/custom_nodes/ComfyUI-Manager",
      "git_url": "https://github.com/ltdrdata/ComfyUI-Manager.git",
      "size_mb": 87.12,
      "node_count": 17,
      "has_requirements": true
    }
  },
  "summary": {
    "total_nodes": 21,
    "total_size_mb": 228.7,
    "git_managed_nodes": 6
  }
}
```

### Node Information Structure

Each node includes:
- **Basic Info**: name, path, version, status
- **Git Info**: repository URL, commit hash, last update
- **Content**: file count, Python files, size
- **Dependencies**: requirements.txt, install.py presence
- **Metrics**: node count, directory size

## Monitoring Features

### 1. File System Monitoring
- Detects new node installations
- Tracks directory removals
- Monitors configuration file changes
- Automatic cache updates

### 2. API Integration
- Real-time node status from ComfyUI-Manager
- Registry information for available nodes
- Update checking and snapshot management
- Queue management for operations

### 3. Health Checks
- Directory existence and permissions
- Git repository integrity
- API connectivity validation
- Dependency verification

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'yaml'"**
   - Solution: Use the basic scanner that doesn't require external dependencies
   - Or install: `pip3 install --user pyyaml watchdog`

2. **"HTTP Error 500: Internal Server Error"**
   - ComfyUI may not be running
   - Some endpoints require specific parameters
   - Check ComfyUI logs for errors

3. **"Cannot connect to API"**
   - Verify ComfyUI is running on the specified port
   - Check firewall settings
   - Ensure ComfyUI-Manager is installed and loaded

### Debug Mode

```bash
# Enable verbose logging
python3 scripts/comfyui_nodes_scanner.py scan 2>&1 | tee debug.log

# Test specific API endpoint
curl -v http://localhost:8188/customnode/installed
```

## Integration Examples

### 1. Automated Backup Script

```bash
#!/bin/bash
# backup_nodes.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ned/ComfyUI-Install/backups/nodes_$DATE"

mkdir -p "$BACKUP_DIR"

# Scan and export
cd /home/ned/ComfyUI-Install
python3 scripts/comfyui_nodes_scanner.py

# Copy important files
cp -r ComfyUI/custom_nodes "$BACKUP_DIR/"
cp config/custom_nodes/custom_nodes_scan.json "$BACKUP_DIR/"

echo "Backup completed: $BACKUP_DIR"
```

### 2. Change Detection

```python
import json
from pathlib import Path

def detect_changes(previous_file, current_file):
    """Detect changes between two node inventories"""
    with open(previous_file) as f:
        previous = json.load(f)

    with open(current_file) as f:
        current = json.load(f)

    # Compare nodes
    prev_nodes = set(previous['nodes'].keys())
    curr_nodes = set(current['nodes'].keys())

    new_nodes = curr_nodes - prev_nodes
    removed_nodes = prev_nodes - curr_nodes

    return {
        'new_nodes': list(new_nodes),
        'removed_nodes': list(removed_nodes),
        'scan_time': current['export_timestamp']
    }
```

### 3. Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "🏥 ComfyUI Custom Nodes Health Check"

# Check directory
if [ -d "/home/ned/ComfyUI-Install/ComfyUI/custom_nodes" ]; then
    echo "✅ Custom nodes directory exists"
else
    echo "❌ Custom nodes directory missing"
fi

# Check API
if curl -s http://localhost:8188/customnode/installed > /dev/null; then
    echo "✅ API responding"
else
    echo "❌ API not responding"
fi

# Run scanner
cd /home/ned/ComfyUI-Install
python3 scripts/comfyui_nodes_scanner.py scan
```

## Performance Considerations

### Optimization Tips

1. **Cache Management**: The system caches node information to avoid repeated scans
2. **Selective Monitoring**: Monitor only critical directories to reduce overhead
3. **API Rate Limiting**: Built-in retry logic prevents overwhelming the API
4. **File System Events**: Uses efficient OS-level file monitoring when available

### Resource Usage

- **Memory**: ~50MB for basic scanning
- **CPU**: Minimal during idle, spikes during scans
- **Disk**: Exports typically < 1MB
- **Network**: Light API calls, no heavy transfers

## Future Enhancements

### Planned Features

1. **Web Dashboard**: Web interface for monitoring and management
2. **Notification System**: Email/webhook alerts for changes
3. **Integration with ComfyUI Workflows**: Direct workflow integration
4. **Automated Testing**: Node validation and compatibility testing
5. **Backup Automation**: Scheduled backups with versioning

### Extension Points

- **Custom Validators**: Add custom node validation logic
- **External APIs**: Integration with GitHub, HuggingFace, etc.
- **Plugin System**: Support for custom monitoring plugins
- **Metrics Export**: Integration with monitoring systems

## Support

### Getting Help

1. **Logs**: Check scanner output and ComfyUI logs
2. **Configuration**: Verify paths and API settings
3. **Dependencies**: Ensure required packages are installed
4. **Network**: Check ComfyUI accessibility and firewall settings

### Contributing

The interface system is designed to be extensible:
- Add new API endpoints in the client
- Extend node information collection
- Add custom monitoring rules
- Improve health check logic

---

**Last Updated**: October 7, 2025
**Version**: 1.0
**Compatibility**: ComfyUI-Manager v3.x, Python 3.8+