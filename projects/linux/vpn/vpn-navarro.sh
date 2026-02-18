#!/usr/bin/env bash
# VPN Navarro — Quick connect/disconnect
# Usage: ./vpn-navarro.sh [up|down|status]

ACTION="${1:-up}"
VPN_NAME="Work-VPN-PPTP"

case "$ACTION" in
  up)
    echo "🔌 Conectando VPN Navarro..."
    nmcli connection up "$VPN_NAME"
    if [ $? -eq 0 ]; then
      echo "✅ VPN Navarro conectada"
      echo "   IP local: $(nmcli -t -f IP4.ADDRESS dev show ppp0 2>/dev/null | cut -d: -f2)"
    else
      echo "❌ Error al conectar"
    fi
    ;;
  down)
    echo "🔌 Desconectando VPN Navarro..."
    nmcli connection down "$VPN_NAME"
    echo "✅ VPN Navarro desconectada"
    ;;
  status)
    if nmcli connection show --active | grep -q "$VPN_NAME"; then
      echo "✅ VPN Navarro: CONECTADA"
    else
      echo "❌ VPN Navarro: DESCONECTADA"
    fi
    ;;
  *)
    echo "Uso: $0 [up|down|status]"
    ;;
esac
