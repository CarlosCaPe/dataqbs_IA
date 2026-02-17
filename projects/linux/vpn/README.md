# VPN Setup on Linux

## Native VPN Clients (Recommended)

Instead of running Windows in a VM just for VPN, most VPN providers have native Linux clients or can use standard protocols.

### Common VPN Types and Linux Equivalents

| Windows VPN | Linux Native Client | Installation |
|-------------|---------------------|--------------|
| **Cisco AnyConnect** | `openconnect` | `sudo apt install openconnect network-manager-openconnect-gnome` |
| **FortiClient** | `openfortivpn` | `sudo apt install openfortivpn` |
| **GlobalProtect** (Palo Alto) | `openconnect` with GP protocol | `sudo apt install openconnect` |
| **WireGuard** | Native support | `sudo apt install wireguard` |
| **OpenVPN** | Native support | `sudo apt install openvpn network-manager-openvpn-gnome` |
| **L2TP/IPSec** | `xl2tpd` + `strongswan` | `sudo apt install xl2tpd strongswan network-manager-l2tp-gnome` |
| **SSTP** (Microsoft) | `sstp-client` | `sudo apt install sstp-client` |
| **IKEv2** | `strongswan` | `sudo apt install strongswan network-manager-strongswan` |

## GUI Method (Easiest)

### Install VPN plugins for NetworkManager:

```bash
sudo apt install \
    network-manager-openvpn-gnome \
    network-manager-l2tp-gnome \
    network-manager-vpnc-gnome \
    network-manager-strongswan
```

After installation:
1. Click network icon in system tray
2. Settings → Network → VPN → Add (+)
3. Import from file or configure manually

## Command Line Methods

### OpenConnect (Cisco AnyConnect / GlobalProtect)

```bash
# Install
sudo apt install openconnect

# Connect to Cisco AnyConnect
sudo openconnect vpn.example.com

# Connect to GlobalProtect
sudo openconnect --protocol=gp vpn.example.com
```

### OpenVPN

```bash
# Install
sudo apt install openvpn

# Connect with config file
sudo openvpn --config your-vpn-config.ovpn

# Or import to NetworkManager and use GUI
```

### FortiClient VPN

```bash
# Install
sudo apt install openfortivpn

# Connect
sudo openfortivpn vpn.example.com:443 -u username

# Or create config file at /etc/openfortivpn/config:
# host = vpn.example.com
# port = 443
# username = your_username
# password = your_password

# Then connect:
sudo openfortivpn
```

### WireGuard

```bash
# Install
sudo apt install wireguard

# Import config
sudo cp your-vpn.conf /etc/wireguard/wg0.conf

# Start
sudo wg-quick up wg0

# Stop
sudo wg-quick down wg0
```

## Using Windows VM for VPN (Last Resort)

If your VPN provider has no Linux support and you must use their Windows client:

1. **Install VM tools**: `cd ~/projects/linux/vm && ./install-vm-tools.sh`
2. **Download Windows ISO**: `./download-windows-iso.sh`
3. **Create VM**: `./create-windows-vm.sh`
4. **Launch VM**: `./launch-vm.sh`
5. Inside Windows VM:
   - Install your VPN client
   - Connect to VPN
   - Use Windows as a proxy/gateway

### Bridge VM Network to Host

To use the VPN connection from the VM on your host Linux:

```bash
# Option 1: SSH tunnel through VM
ssh -D 1080 user@windows-vm-ip

# Option 2: Set up SOCKS proxy in Firefox/Chrome
# Settings → Network → Manual proxy → SOCKS Host: 127.0.0.1:1080
```

## Troubleshooting

### DNS not working after VPN connects

```bash
# Check DNS
cat /etc/resolv.conf

# Manually set DNS
sudo systemctl restart systemd-resolved
```

### VPN connects but no internet

```bash
# Check routing table
ip route

# Add default route via VPN (replace tun0 with your VPN interface)
sudo ip route add default dev tun0
```

### Permission denied errors

Most VPN clients require root/sudo to modify network settings.

## Security Note

Store VPN credentials securely:
- Use GNOME Keyring / KWallet for GUI
- Use `pass` or `keepassxc` for command-line
- Never store plaintext passwords in scripts
