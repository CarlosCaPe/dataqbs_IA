#!/usr/bin/env bash
# Remote Desktop Navarro — Connect to 192.168.0.141 via RDP
# Usage: ./rdp-navarro.sh

RDP_HOST="192.168.0.141"
RDP_USER="ccpena"

# Check if VPN is connected
if ! nmcli connection show --active | grep -q "Work-VPN-PPTP"; then
  echo "⚠️  VPN no conectada. Conectando VPN Navarro primero..."
  nmcli connection up Work-VPN-PPTP
  sleep 2
fi

echo "🖥️  Conectando Remote Desktop a $RDP_HOST..."

# Check if remmina is installed
if ! command -v remmina &>/dev/null; then
  echo "📦 Instalando Remmina..."
  sudo apt install -y remmina remmina-plugin-rdp
fi

remmina -c rdp://"$RDP_USER"@"$RDP_HOST"
