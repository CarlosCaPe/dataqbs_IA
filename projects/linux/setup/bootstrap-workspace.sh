#!/bin/bash
# Complete workspace bootstrap for Linux environment
# Run this on a fresh Pop!_OS/Ubuntu/Debian system

set -e  # Exit on error

echo "========================================="
echo "  dataqbs_IA Workspace Bootstrap"
echo "========================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Error: Do not run this script as root${NC}"
   exit 1
fi

echo -e "${YELLOW}[1/6] Checking system requirements...${NC}"
if ! egrep -q '(vmx|svm)' /proc/cpuinfo; then
    echo -e "${RED}Warning: Virtualization not detected. Enable VT-x/AMD-V in BIOS if you need VMs.${NC}"
fi

echo -e "${GREEN}✓ CPU: $(grep "model name" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)${NC}"
echo -e "${GREEN}✓ RAM: $(free -h | awk '/^Mem:/{print $2}') total${NC}"
echo

echo -e "${YELLOW}[2/6] Installing system packages...${NC}"
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-venv \
    git curl wget \
    build-essential \
    ca-certificates \
    gnupg \
    lsb-release

echo

echo -e "${YELLOW}[3/6] Installing Python dev tools...${NC}"
pip3 install --user poetry ruff pytest pre-commit black

# Add to PATH if not already there
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    export PATH="$HOME/.local/bin:$PATH"
fi

echo

echo -e "${YELLOW}[4/6] Configuring SSL certificates...${NC}"
if [ -f /etc/pki/tls/certs/ca-bundle.crt ]; then
    git config --global http.sslCAInfo /etc/pki/tls/certs/ca-bundle.crt
    echo 'export SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt' >> ~/.bashrc
    echo 'export REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt' >> ~/.bashrc
    export SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt
    export REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt
    echo -e "${GREEN}✓ SSL certificates configured${NC}"
else
    echo -e "${YELLOW}Note: CA bundle not found at expected location. Git SSL may need manual configuration.${NC}"
fi

echo

echo -e "${YELLOW}[5/6] Installing Poetry dependencies (this may take a while)...${NC}"
cd /home/carloscarrillo/Documents/github/dataqbs_IA

# Root project
echo "  → Installing root project dependencies..."
poetry lock --no-update 2>/dev/null || true
poetry install

# Subprojects
for project in email_collector oai_code_evaluator real_estate arbitraje tls_compara_audios tls_compara_imagenes supplier_verifier; do
    if [ -d "projects/$project" ]; then
        echo "  → Installing $project dependencies..."
        cd "projects/$project"
        poetry lock --no-update 2>/dev/null || true
        poetry install 2>&1 | grep -E "(Installing|✓|✗)" || true
        cd ../..
    fi
done

echo

echo -e "${YELLOW}[6/6] Configuring VS Code...${NC}"
VSCODE_SETTINGS_DIR="$HOME/.config/Code/User"
if [ -d "$VSCODE_SETTINGS_DIR" ]; then
    echo "  → VS Code settings will be applied from projects/linux/configs/vscode/"
    echo "  → Manual step: Copy settings if needed"
else
    echo -e "${YELLOW}  Note: VS Code settings directory not found. Install VS Code first.${NC}"
fi

echo
echo -e "${GREEN}========================================="
echo "  ✓ Bootstrap Complete!"
echo "=========================================${NC}"
echo
echo "Next steps:"
echo "  1. Create .env file with your API keys and credentials"
echo "  2. Run pre-commit install in the root: poetry run pre-commit install"
echo "  3. If you need Windows VM for VPN: cd projects/linux/vm && ./install-vm-tools.sh"
echo
echo "Tool versions installed:"
poetry --version
python3 --version
git --version
ruff --version 2>/dev/null || echo "ruff: check PATH"
pytest --version 2>/dev/null || echo "pytest: check PATH"
echo
echo "Reload shell to apply PATH changes: source ~/.bashrc"
