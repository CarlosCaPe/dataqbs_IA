#!/bin/bash
# Quick launch script for Windows VM

VM_NAME="windows10-vpn"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if VM exists
if ! virsh list --all | grep -q "$VM_NAME"; then
    echo -e "${RED}Error: VM '$VM_NAME' not found${NC}"
    echo "Create it first with: ./create-windows-vm.sh"
    exit 1
fi

# Check if already running
if virsh list --state-running | grep -q "$VM_NAME"; then
    echo -e "${YELLOW}VM '$VM_NAME' is already running${NC}"
    echo "Opening virt-manager to connect..."
    virt-manager --connect qemu:///system --show-domain-console "$VM_NAME" &
    exit 0
fi

echo -e "${GREEN}Starting VM '$VM_NAME'...${NC}"
virsh start "$VM_NAME"

echo "Waiting for VM to boot..."
sleep 3

echo -e "${GREEN}✓ VM started${NC}"
echo "Opening virt-manager console..."
virt-manager --connect qemu:///system --show-domain-console "$VM_NAME" &

echo
echo "VM Commands:"
echo "  Stop VM: virsh shutdown $VM_NAME"
echo "  Force stop: virsh destroy $VM_NAME"
echo "  VM status: virsh list --all"
echo "  Connect: virt-manager"
