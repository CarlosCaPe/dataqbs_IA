#!/bin/bash
# Create a Windows 10 VM for VPN and Windows-specific tools

set -e

echo "========================================="
echo "  Create Windows 10 VM"
echo "========================================="
echo

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
VM_NAME="windows10-vpn"
ISO_PATH="$HOME/VMs/ISOs/Windows10_LTSC_2021.iso"
DISK_SIZE=40  # GB
RAM=4096      # MB (4 GB)
CPUS=2
DISK_PATH="$HOME/VMs/disks/${VM_NAME}.qcow2"

# Check if ISO exists
if [ ! -f "$ISO_PATH" ]; then
    echo -e "${RED}Error: Windows ISO not found at: $ISO_PATH${NC}"
    echo "Run ./download-windows-iso.sh first"
    exit 1
fi

# Create directories
mkdir -p "$HOME/VMs/disks"

# Check if VM already exists
if virsh list --all | grep -q "$VM_NAME"; then
    echo -e "${YELLOW}VM '$VM_NAME' already exists.${NC}"
    echo
    read -p "Do you want to delete it and recreate? (y/N): " choice
    if [[ "$choice" =~ ^[Yy]$ ]]; then
        echo "Destroying existing VM..."
        virsh destroy "$VM_NAME" 2>/dev/null || true
        virsh undefine "$VM_NAME" --remove-all-storage 2>/dev/null || true
    else
        echo "Keeping existing VM. Use ./launch-vm.sh to start it."
        exit 0
    fi
fi

echo "VM Configuration:"
echo "  Name: $VM_NAME"
echo "  RAM: ${RAM}MB"
echo "  CPUs: $CPUS"
echo "  Disk: ${DISK_SIZE}GB"
echo "  ISO: $ISO_PATH"
echo

read -p "Continue with VM creation? (Y/n): " confirm
if [[ "$confirm" =~ ^[Nn]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo
echo -e "${YELLOW}Creating VM (this will open virt-manager for installation)...${NC}"
echo

# Create VM with virt-install
sudo virt-install \
    --name="$VM_NAME" \
    --ram=$RAM \
    --vcpus=$CPUS \
    --disk path="$DISK_PATH",size=$DISK_SIZE,format=qcow2 \
    --cdrom="$ISO_PATH" \
    --os-variant=win10 \
    --network network=default,model=virtio \
    --graphics spice \
    --video qxl \
    --channel spicevmc \
    --boot uefi \
    --features kvm_hidden=on \
    --noautoconsole

echo
echo -e "${GREEN}✓ VM created successfully!${NC}"
echo
echo "The VM is now installing. To access it:"
echo "  1. Open virt-manager: virt-manager"
echo "  2. Double-click on '$VM_NAME'"
echo "  3. Follow Windows installation wizard"
echo
echo "Recommended Windows setup:"
echo "  - Choose 'Custom: Install Windows only (advanced)'"
echo "  - Create a single partition using all space"
echo "  - Skip product key (works without activation for evaluation)"
echo "  - Create a local account (no Microsoft account needed)"
echo
echo "After Windows is installed:"
echo "  - Install your VPN client"
echo "  - Network should work automatically (NAT bridge)"
echo "  - To improve performance, install virtio drivers:"
echo "    https://github.com/virtio-win/virtio-win-pkg-scripts/blob/master/README.md"
echo
echo "To start the VM later: ./launch-vm.sh"
echo "To stop the VM: virsh shutdown $VM_NAME"
