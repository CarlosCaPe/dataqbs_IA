#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# VPN Setup for Pop!_OS / Ubuntu — L2TP/IPSec & PPTP
# Server: 167.249.255.45
# ─────────────────────────────────────────────────────────
set -euo pipefail

echo "═══════════════════════════════════════════════════"
echo "  VPN Setup — L2TP/IPSec + PPTP for Pop!_OS"
echo "═══════════════════════════════════════════════════"

# ── 1. Install VPN packages ──────────────────────────────
echo ""
echo "[1/3] Installing VPN packages..."
sudo apt update -qq
sudo apt install -y \
    network-manager-l2tp \
    network-manager-l2tp-gnome \
    network-manager-pptp \
    network-manager-pptp-gnome \
    xl2tpd \
    strongswan \
    libreswan 2>/dev/null || true

echo ""
echo "[2/3] Restarting NetworkManager..."
sudo systemctl restart NetworkManager

# ── 2. Create VPN connection (L2TP first, most common) ───
echo ""
echo "[3/3] Creating VPN connections..."

VPN_SERVER="167.249.255.45"
VPN_USER="ccpena"
VPN_NAME="Work-VPN-L2TP"
VPN_NAME_PPTP="Work-VPN-PPTP"

# Remove existing connections with same name (if re-running)
nmcli connection delete "$VPN_NAME" 2>/dev/null || true
nmcli connection delete "$VPN_NAME_PPTP" 2>/dev/null || true

# ── L2TP/IPSec connection ────────────────────────────────
echo "  → Creating L2TP/IPSec connection..."
nmcli connection add \
    type vpn \
    vpn-type l2tp \
    con-name "$VPN_NAME" \
    vpn.data "gateway=$VPN_SERVER, user=$VPN_USER, refuse-eap=yes, refuse-pap=no, refuse-chap=no, refuse-mschap=no, refuse-mschapv2=no" \
    connection.autoconnect no

# ── PPTP connection (fallback) ───────────────────────────
echo "  → Creating PPTP connection (fallback)..."
nmcli connection add \
    type vpn \
    vpn-type pptp \
    con-name "$VPN_NAME_PPTP" \
    vpn.data "gateway=$VPN_SERVER, user=$VPN_USER, refuse-eap=yes, refuse-pap=no, refuse-chap=no, refuse-mschap=no, refuse-mschapv2=no" \
    connection.autoconnect no

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✅ VPN connections created!"
echo ""
echo "  To connect via GUI:"
echo "    Settings → Network → VPN → toggle ON"
echo "    Select '$VPN_NAME' or '$VPN_NAME_PPTP'"
echo "    Enter password when prompted: (see credentials)"
echo ""
echo "  To connect via terminal:"
echo "    nmcli connection up '$VPN_NAME' --ask"
echo "    # or"
echo "    nmcli connection up '$VPN_NAME_PPTP' --ask"
echo ""
echo "  To disconnect:"
echo "    nmcli connection down '$VPN_NAME'"
echo ""
echo "  If L2TP doesn't work, try PPTP."
echo "  If neither works, check with IT if a"
echo "  pre-shared key (PSK) is required for IPSec."
echo "═══════════════════════════════════════════════════"
