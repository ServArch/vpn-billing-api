# VPN Client & Router Setup Guide

## VLESS Reality Protocol
VLESS with Reality TLS camouflage provides high-performance traffic obfuscation against active probing. It replaces traditional TLS certificates with real destination SNI certificates (e.g. microsoft.com, yahoo.com).

### Client Configuration (iOS & Android)
For mobile devices, recommended clients are:
- iOS: Streisand, Shadowrocket, FoXray
- Android: v2rayNG, NekoBox for Android

To connect:
1. Copy the VLESS connection URI from your personal dashboard or Telegram bot.
2. Open your client application and select "Add configuration from Clipboard".
3. Verify that Flow is set to `xtls-rprx-vision` and Security is set to `reality`.
4. Test latency with ping before initiating connection.

### Desktop Configuration (Windows & macOS)
Recommended desktop clients:
- Windows: v2rayN, Hiddify Next, Nekoray
- macOS: FoXray, V2Box, Hiddify

Common desktop connection issues:
- Error `handshake failed: certificate unknown`: Ensure your system clock is synchronized via NTP (max drift allowed is 90 seconds).
- Error `tun interface allocation failed`: On macOS, enable system extension permissions in System Settings -> Privacy & Security.

## Router Configuration (Keenetic & OpenWrt)
Routing traffic directly at gateway level protects all household IoT devices and TVs.

### Keenetic Routers (Entware + Xray)
KeeneticOS 3.x and 4.x support running Xray core via Entware on USB flash drive:
1. Install Entware repository via Keenetic web interface.
2. SSH into router and install core packages: `opkg update && opkg install xray-core`.
3. Place `config.json` containing your VLESS outbound into `/opt/etc/xray/`.
4. Configure iptables redirect rules for DNS ports 53 and outbound TCP/UDP traffic.

### OpenWrt Routers (Passwall & OpenClash)
1. Install LuCI interface plugin: `luci-app-passwall` or `luci-app-openclash`.
2. Import server node configuration using subscription link or JSON config.
3. Set TCP proxy mode to `Redirect` and UDP proxy mode to `TProxy`.
4. Enable ChinaDNS / fake-ip mode to prevent DNS pollution and ISP leakage.

## Troubleshooting & FAQ
### What to do if connection connects but no web pages open?
Check your DNS settings inside client:
1. Set remote DNS to `1.1.1.1` or `8.8.8.8` over TLS/HTTPS (DoH/DoT).
2. Disable IPv6 in adapter properties if your ISP does not route native IPv6.
3. Verify that subscription expiry has not elapsed in `/billing/status`.

### Connection drops every few minutes
- On mobile: Disable battery optimization / background app sleep for the VPN client app.
- Check MTU settings: Set MTU to 1420 or 1280 if operating on mobile LTE/5G networks with encapsulation overhead.
