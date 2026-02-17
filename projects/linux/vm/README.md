# Windows VM Setup for VPN & Windows-Only Tools

This directory contains scripts to set up a lightweight Windows 10 virtual machine on Linux using QEMU/KVM.

## Why You Might Need This

- **VPN with no Linux client**: Some corporate/provider VPNs only have Windows clients
- **Windows-specific tools**: Software that doesn't work with Wine
- **Testing**: Test Windows-specific features or configurations
- **Legacy software**: Run older Windows applications

## Quick Start

### 1. Install VM Tools (One-time setup)

```bash
./install-vm-tools.sh
```

This installs QEMU/KVM and adds your user to the required groups.

**Important**: After this script finishes, **log out and log back in** for group changes to take effect.

### 2. Download Windows ISO

```bash
./download-windows-iso.sh
```

Downloads Windows 10 LTSC 2021 (~4.5 GB):
- Lightweight (no bloatware)
- Long-term support (10 years)
- Works without activation for evaluation
- Saved to: `~/VMs/ISOs/Windows10_LTSC_2021.iso`

### 3. Create the VM

```bash
./create-windows-vm.sh
```

Creates a VM with:
- **Name**: windows10-vpn
- **RAM**: 4 GB
- **CPU**: 2 cores
- **Disk**: 40 GB (dynamically allocated)
- **Network**: NAT (shares host internet)

The script will launch virt-manager where you can follow the Windows installation wizard.

### 4. Launch the VM

```bash
./launch-vm.sh
```

Starts the VM and opens the console window.

## Windows Installation Tips

1. **During Installation**:
   - Choose "Custom: Install Windows only (advanced)"
   - Create a single partition using all available space
   - Skip product key (it will work without activation)
   - Create a local account (no Microsoft account needed)

2. **After Installation**:
   - Install your VPN client
   - Install any Windows tools you need
   - Network should work automatically via NAT

3. **Optional Performance Boost**:
   - Install virtio drivers for better disk/network performance
   - Download from: https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/

## VM Management Commands

```bash
# Start VM
virsh start windows10-vpn

# Stop VM gracefully
virsh shutdown windows10-vpn

# Force stop VM
virsh destroy windows10-vpn

# Check VM status
virsh list --all

# Delete VM completely
virsh undefine windows10-vpn --remove-all-storage

# Open virt-manager GUI
virt-manager
```

## Using VPN from the VM

### Method 1: Direct use in VM
1. Install VPN client inside Windows
2. Connect to VPN in Windows
3. Use Windows applications that need VPN
4. Access VPN-protected resources from Windows browser

### Method 2: Share VPN with host Linux
If you need the VPN connection on your Linux host:

**Option A: SSH Tunnel** (если у вас есть SSH в VM)
```bash
# Inside VM: Install OpenSSH Server
# Then from Linux:
ssh -D 1080 username@windows-vm-ip

# Configure Firefox/Chrome to use SOCKS proxy:
# Settings → Network → Manual proxy
# SOCKS Host: 127.0.0.1, Port: 1080
```

**Option B: Bridge Network**
Change VM network from NAT to Bridge mode in virt-manager:
1. Open VM settings → Network
2. Change "NAT" to "Bridge" 
3. Select your network interface
4. VM will get its own IP on your network
5. VPN connection in VM may route all traffic through VPN

## Troubleshooting

### "Permission denied" when running scripts
```bash
chmod +x *.sh
```

### "Not a member of libvirt group"
```bash
sudo usermod -aG libvirt,kvm $USER
# Then log out and log back in
```

### VM won't start: "No KVM support"
1. Check if virtualization is enabled:
   ```bash
   egrep -c '(vmx|svm)' /proc/cpuinfo
   ```
   Should return > 0
2. If 0, enable VT-x/AMD-V in BIOS/UEFI settings

### VM is slow
1. Increase RAM: Edit VM in virt-manager → RAM → Increase to 8GB
2. Add more CPU cores: Edit VM → vCPUs → Increase to 4
3. Install virtio drivers in Windows

### Can't download ISO
If archive.org is down, download manually from:
- https://massgrave.dev/windows_ltsc_links.html
- https://tb.rg-adguard.net/public.php

Then save as: `~/VMs/ISOs/Windows10_LTSC_2021.iso`

### Network not working in VM
- VM uses NAT by default (shares host internet)
- Check firewall settings on host
- In VM: Run Windows Network Troubleshooter

## Performance Considerations

**RAM**: Host needs enough RAM
- Your system: 15 GB total
- Recommended VM RAM: 4 GB
- Leaves ~9 GB for Linux (comfortable)

**CPU**: VM uses 2/4 cores
- Won't slow down Linux significantly
- Can adjust in virt-manager if needed

**Disk**: Uses only actual data size
- 40 GB allocated, but starts at ~10-15 GB
- Grows as you install software
- Your disk has 194 GB free (plenty of space)

## Alternatives to VM

Before setting up a VM, check if your VPN has a Linux client:
- See [../vpn/README.md](../vpn/README.md) for native Linux VPN options
- Many Windows VPNs have Linux equivalents (OpenConnect, WireGuard, etc.)

VMs are great but have overhead. Native Linux clients are always faster.

## Resources

- [QEMU Documentation](https://www.qemu.org/documentation/)
- [KVM Virtualization](https://www.linux-kvm.org/)
- [virt-manager User Guide](https://virt-manager.org/)
- [Windows LTSC Info](https://docs.microsoft.com/en-us/windows/whats-new/ltsc/)
