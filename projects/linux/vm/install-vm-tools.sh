#!/bin/bash
# Install QEMU/KVM for running Windows VMs on Linux

set -e

echo "========================================="
echo "  Installing VM Tools (QEMU/KVM)"
echo "========================================="
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Error: Do not run this script as root. It will prompt for sudo when needed.${NC}"
   exit 1
fi

# Check virtualization support
echo -e "${YELLOW}Checking virtualization support...${NC}"
virt_count=$(egrep -c '(vmx|svm)' /proc/cpuinfo)
if [ "$virt_count" -eq 0 ]; then
    echo -e "${RED}Error: CPU virtualization not detected!${NC}"
    echo "Enable Intel VT-x or AMD-V in your BIOS settings."
    exit 1
fi
echo -e "${GREEN}✓ Virtualization enabled ($virt_count cores support it)${NC}"
echo

# Install packages
echo -e "${YELLOW}Installing QEMU/KVM packages...${NC}"
sudo apt update
sudo apt install -y \
    qemu-kvm \
    libvirt-daemon-system \
    libvirt-clients \
    bridge-utils \
    virt-manager \
    cpu-checker \
    libguestfs-tools \
    libosinfo-bin

echo

# Add user to required groups
echo -e "${YELLOW}Adding user to libvirt and kvm groups...${NC}"
sudo usermod -aG libvirt,kvm $USER
echo -e "${GREEN}✓ User $USER added to libvirt and kvm groups${NC}"
echo

# Enable and start libvirtd service
echo -e "${YELLOW}Enabling libvirtd service...${NC}"
sudo systemctl enable --now libvirtd
sudo systemctl start libvirtd
echo -e "${GREEN}✓ libvirtd service running${NC}"
echo

# Verify installation
echo -e "${YELLOW}Verifying installation...${NC}"
if kvm-ok 2>/dev/null; then
    echo -e "${GREEN}✓ KVM acceleration available${NC}"
else
    echo -e "${YELLOW}Note: kvm-ok check failed. This may be normal on some systems.${NC}"
fi

sudo virsh list --all
echo

echo -e "${GREEN}========================================="
echo "  ✓ VM Tools Installed Successfully!"
echo "=========================================${NC}"
echo
echo "IMPORTANT: You must log out and log back in for group changes to take effect."
echo
echo "After re-logging in, you can:"
echo "  1. Launch virt-manager GUI: virt-manager"
echo "  2. Download Windows ISO: ./download-windows-iso.sh"
echo "  3. Create Windows VM: ./create-windows-vm.sh"
echo
echo "To verify groups after re-login: groups | grep libvirt"
