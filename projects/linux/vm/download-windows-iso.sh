#!/bin/bash
# Download Windows 10 LTSC ISO for VM installation

set -e

echo "========================================="
echo "  Windows 10 LTSC ISO Downloader"
echo "========================================="
echo

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ISO details
ISO_NAME="Windows10_LTSC_2021.iso"
ISO_DIR="$HOME/VMs/ISOs"
ISO_PATH="$ISO_DIR/$ISO_NAME"

# Create ISOs directory
mkdir -p "$ISO_DIR"

echo "Windows 10 LTSC 2021 Enterprise Edition"
echo "  - Lightweight, no bloatware"
echo "  - 10 years support"
echo "  - Size: ~4.5 GB"
echo "  - Download location: $ISO_PATH"
echo

if [ -f "$ISO_PATH" ]; then
    echo -e "${GREEN}ISO already exists at: $ISO_PATH${NC}"
    echo "Size: $(du -h "$ISO_PATH" | cut -f1)"
    echo
    read -p "Do you want to re-download? (y/N): " choice
    if [[ ! "$choice" =~ ^[Yy]$ ]]; then
        echo "Using existing ISO."
        exit 0
    fi
    rm -f "$ISO_PATH"
fi

echo -e "${YELLOW}Starting download (this will take several minutes)...${NC}"
echo

# Option 1: Direct download from archive.org (recommended)
echo "Downloading from archive.org..."
wget -O "$ISO_PATH" \
    --progress=bar:force:noscroll \
    "https://archive.org/download/windows-10-ltsc-2021/Windows%2010%20LTSC%202021.iso" \
    || {
        echo "Download failed from archive.org"
        echo
        echo "Alternative: Download manually from:"
        echo "  https://massgrave.dev/windows_ltsc_links.html"
        echo "  https://tb.rg-adguard.net/public.php"
        echo
        echo "Then save it to: $ISO_PATH"
        exit 1
    }

echo
echo -e "${GREEN}✓ Download complete!${NC}"
echo "ISO saved to: $ISO_PATH"
echo "Size: $(du -h "$ISO_PATH" | cut -f1)"
echo
echo "Next steps:"
echo "  1. Create VM: ./create-windows-vm.sh"
echo "  2. Or use virt-manager GUI to create it manually"
