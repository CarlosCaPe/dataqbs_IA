#!/bin/bash
# System health check script

echo "========================================="
echo "  System Health Check"
echo "========================================="
echo

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# CPU
echo "CPU:"
lscpu | grep -E "Model name|CPU\(s\):|Thread|Core|MHz" | sed 's/^/  /'
echo

# RAM
echo "RAM:"
free -h | grep -E "Mem|Swap" | sed 's/^/  /'
echo

# Disk
echo "Disk Usage:"
df -h / /home 2>/dev/null | grep -v tmpfs | sed 's/^/  /'
echo

# Uptime and Load
echo "Uptime and Load Average:"
uptime | sed 's/^/  /'
echo

# Virtualization
echo "Virtualization:"
if egrep -q '(vmx|svm)' /proc/cpuinfo; then
    echo -e "  ${GREEN}✓ Enabled (VT-x/AMD-V)${NC}"
else
    echo -e "  ${RED}✗ Not detected${NC}"
fi
echo

# Dev Tools
echo "Development Tools:"
for cmd in python3 poetry git ruff pytest black pre-commit; do
    if command -v $cmd &> /dev/null; then
        version=$($cmd --version 2>&1 | head -1)
        echo -e "  ${GREEN}✓${NC} $cmd: $version"
    else
        echo -e "  ${RED}✗${NC} $cmd: Not installed"
    fi
done
echo

# Poetry Environments
echo "Poetry Virtual Environments:"
cd /home/carloscarrillo/Documents/github/dataqbs_IA 2>/dev/null
if command -v poetry &> /dev/null; then
    for project in projects/*/pyproject.toml; do
        if [ -f "$project" ]; then
            proj_dir=$(dirname "$project")
            proj_name=$(basename "$proj_dir")
            cd "$proj_dir"
            if poetry env list &>/dev/null && [ -n "$(poetry env list)" ]; then
                echo -e "  ${GREEN}✓${NC} $proj_name"
            else
                echo -e "  ${YELLOW}○${NC} $proj_name (no venv)"
            fi
            cd - >/dev/null
        fi
    done
else
    echo "  Poetry not found"
fi
echo

# VM Tools
echo "Virtualization Tools:"
if command -v virsh &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} QEMU/KVM installed"
    echo "  VMs:"
    virsh list --all 2>/dev/null | tail -n +3 | sed 's/^/    /' || echo "    None"
else
    echo -e "  ${YELLOW}○${NC} QEMU/KVM not installed"
fi
echo

# Git SSL
echo "Git Configuration:"
ssl_ca=$(git config --global http.sslCAInfo 2>/dev/null)
if [ -n "$ssl_ca" ]; then
    echo -e "  ${GREEN}✓${NC} SSL CA: $ssl_ca"
else
    echo -e "  ${YELLOW}○${NC} SSL CA not configured"
fi
echo

# Processes
echo "Top 5 Processes (CPU):"
ps aux --sort=-%cpu | head -6 | tail -5 | awk '{printf "  %s: %.1f%% CPU, %.1f%% RAM\n", $11, $3, $4}'
echo

echo "========================================="
echo "  End of Health Check"
echo "========================================="
