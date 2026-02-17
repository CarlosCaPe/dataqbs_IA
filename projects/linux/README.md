# Linux Migration & Setup Project

This project contains all tools, scripts, and documentation for setting up and maintaining the Linux development environment after migrating from Windows.

## Project Structure

```
linux/
├── README.md                    # This file
├── setup/                       # Installation and setup scripts
│   ├── install-dev-tools.sh     # Install Python, Poetry, ruff, pytest, etc.
│   ├── configure-vscode.sh      # Apply VS Code Linux configurations
│   ├── fix-ssl-certs.sh         # Configure SSL certificates for Git/pip
│   └── bootstrap-workspace.sh   # Complete workspace bootstrap
├── vm/                          # Virtual machine setup
│   ├── install-vm-tools.sh      # Install QEMU/KVM for Windows VMs
│   ├── download-windows-iso.sh  # Download Windows 10 LTSC ISO
│   ├── create-windows-vm.sh     # Create and configure Windows VM
│   └── launch-vm.sh             # Quick launch script
├── vpn/                         # VPN configurations
│   ├── README.md                # VPN setup guide
│   └── vpn-clients.md           # Native Linux VPN client alternatives
├── configs/                     # Configuration files
│   ├── vscode/                  # VS Code settings backup
│   │   ├── settings.json        # Linux-compatible settings
│   │   └── tasks.json           # Fixed tasks (no PowerShell)
│   └── bash/                    # Bash configurations
│       └── .bashrc_additions    # PATH and environment setup
├── docs/                        # Documentation
│   ├── migration-log.md         # Complete migration log
│   ├── performance.md           # System performance analysis
│   ├── troubleshooting.md       # Common issues and solutions
│   └── differences-vs-windows.md # Key differences from Windows
└── scripts/                     # Utility scripts
    ├── check-system.sh          # System health check
    ├── monitor-performance.sh   # Performance monitoring
    └── update-all.sh            # Update all projects and tools
```

## Quick Start

### Initial Setup (Fresh Linux Install)

```bash
cd projects/linux/setup
./bootstrap-workspace.sh
```

This will:
- Install Python 3.13, Poetry, Git
- Install dev tools (ruff, pytest, pre-commit, black)
- Fix SSL certificates
- Configure VS Code for Linux
- Set up Poetry virtualenvs for all projects

### Windows VM for VPN (Optional)

If you need Windows for VPN or specific tools:

```bash
cd projects/linux/vm
./install-vm-tools.sh      # Install QEMU/KVM
./download-windows-iso.sh  # Download Windows 10 LTSC (4.5 GB)
./create-windows-vm.sh     # Create VM (allocate 2 cores, 4GB RAM, 40GB disk)
./launch-vm.sh             # Launch the VM
```

## What Was Done (Migration Log)

### 1. Repository Cloned
- Used shallow clone (`--depth 1`) due to large history
- Configured Git with `http.sslCAInfo` to fix SSL certificate issues

### 2. VS Code Configured for Linux
- Fixed `tasks.json`: Replaced PowerShell commands with bash equivalents
- Fixed paths: Changed Windows backslashes `.\` to Unix forward slashes `./`
- Updated `settings.json`:
  - Changed `python.defaultInterpreterPath` to `python3`
  - Added `terminal.integrated.defaultProfile.linux`: `"bash"`
  - Added Poetry to PATH via `terminal.integrated.env.linux`
  - Enabled `task.allowAutomaticTasks`: `"on"` for auto-execution

### 3. Dev Tools Installed
| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.13.11 | Runtime |
| Poetry | 2.3.2 | Dependency management |
| ruff | 0.15.1 | Linter/formatter |
| pytest | 9.0.2 | Testing |
| black | 26.1.0 | Code formatter |
| pre-commit | 4.5.1 | Git hooks |

### 4. Poetry Virtualenvs Created
All 7 subprojects now have their virtualenvs:
- `email_collector`
- `oai_code_evaluator`
- `real_estate`
- `arbitraje`
- `tls_compara_audios`
- `tls_compara_imagenes`
- `supplier_verifier`

### 5. SSL Certificates Fixed
- Git configured to use `/etc/pki/tls/certs/ca-bundle.crt`
- Environment variables set: `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`

### 6. System Validated
- CPU: Intel i7-7600U with VT-x virtualization enabled ✅
- RAM: 15 GB (10 GB available) ✅
- Disk: 225 GB (194 GB free) ✅
- All tools working ✅

## Pending Tasks

### High Priority
1. **Create `.env` file** with API keys for:
   - Email credentials (Gmail, Hotmail)
   - Exchange API keys (Binance, OKX, etc.)
   - Other service credentials

2. **Configure VPN** for corporate/provider access

### Medium Priority
3. **Install Playwright browsers** for TLS automation projects:
   ```bash
   cd projects/tls_compara_audios
   poetry run playwright install
   ```

4. **Set up pre-commit hooks**:
   ```bash
   poetry run pre-commit install
   ```

## Performance Monitoring

Check system performance:
```bash
./scripts/check-system.sh
```

Monitor in real-time:
```bash
./scripts/monitor-performance.sh
```

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues and solutions.

## Useful Commands

```bash
# Update all Poetry dependencies
./scripts/update-all.sh

# Check if virtualization is enabled
egrep -c '(vmx|svm)' /proc/cpuinfo  # Should return 4 (number of cores)

# Verify KVM modules
lsmod | grep kvm

# Check Poetry environments
poetry env list

# Run a specific task from VS Code tasks.json
# Terminal > Run Task > [select task]
```

## Resources

- [VS Code on Linux](https://code.visualstudio.com/docs/setup/linux)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [QEMU/KVM Setup](https://ubuntu.com/server/docs/virtualization-qemu)
- [Pop!_OS Documentation](https://support.system76.com/articles/pop-basics/)
