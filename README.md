# Nokia FastMile 5G Outdoor CPE (AOD311NK) Toolkit — `apnctl`

<p align="center">
  <a href="https://github.com/dc-voltage"><img src="https://img.shields.io/badge/Author-DC--Voltage-blue.svg?style=for-the-badge&logo=github" alt="Author"></a>
  <a href="#supported-hardware"><img src="https://img.shields.io/badge/Device-Nokia%20AOD311NK-orange.svg?style=for-the-badge&logo=nokia" alt="Device"></a>
  <a href="#1-lock-to-5g-sa-band-n78-jio-true-5g"><img src="https://img.shields.io/badge/5G%20SA-Band%20n78%20(3.5GHz)-success.svg?style=for-the-badge&logo=5g" alt="5G SA n78"></a>
  <a href="#4-modify-apn-jio-bsnl-vi-airtel"><img src="https://img.shields.io/badge/Carrier-Jio%20%7C%20Airtel%20%7C%20BSNL%20%7C%20Vi-blueviolet.svg?style=for-the-badge" alt="Carriers"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="License"></a>
</p>

<p align="center">
  <a href="https://github.com/dc-voltage/airtel-nokia-311nk/stargazers"><img src="https://img.shields.io/github/stars/dc-voltage/airtel-nokia-311nk?style=social" alt="Stars"></a>
  <a href="https://github.com/dc-voltage/airtel-nokia-311nk/network/members"><img src="https://img.shields.io/github/forks/dc-voltage/airtel-nokia-311nk?style=social" alt="Forks"></a>
</p>

<p align="center">
  <img src="assets/terminal_status_crop.png" alt="apnctl live status running on Nokia AOD311NK" width="850">
</p>

A standalone, all-in-one management, APN unlock, and 5G band-locking toolkit for the **Nokia FastMile 5G Outdoor Unit (AOD311NK)** used by Airtel AirFiber in India.

> [!TIP]
> **Quick Start:** Download the pre-compiled binary [`dist/apnctl`](dist/apnctl) and run:
> ```bash
> chmod +x dist/apnctl
> sudo cp dist/apnctl /usr/local/bin/
> apnctl status
> apnctl n78
> ```


---

## 📋 Table of Contents
1. [Overview & Motivation](#-overview--motivation)
2. [Supported Hardware & Firmware](#-supported-hardware--firmware)
   - [Community test results](#community-test-results)
3. [Key Features](#-key-features)
4. [Hardware & Network Setup](#-hardware--network-setup)
   - [Connecting via Laptop (Linux / Windows)](#connecting-via-laptop)
   - [Connecting via 3rd-Party Router (OpenWrt / ASUS / TP-Link)](#connecting-via-3rd-party-router)
5. [Installation](#-installation)
6. [Command Reference & Usage](#-command-reference--usage)
   - [1. Lock to 5G SA Band n78 (Jio True 5G)](#1-lock-to-5g-sa-band-n78-jio-true-5g)
   - [2. Reset to Auto Mode (5G SA + NSA)](#2-reset-to-auto-mode-5g-sa--nsa)
   - [3. Lock to 4G LTE Only](#3-lock-to-4g-lte-only)
   - [4. Modify APN (Jio, BSNL, Vi, Airtel)](#4-modify-apn-jio-bsnl-vi-airtel)
   - [5. Live Cellular RF Telemetry](#5-live-cellular-rf-telemetry)
   - [6. Device Information](#6-device-information)
   - [7. Full Configuration Backup Export](#7-full-configuration-backup-export)
   - [8. Remote Clean Reboot](#8-remote-clean-reboot)
7. [The Physical SIM (Jio) Reboot Issue Explained](#-the-physical-sim-jio-reboot-issue-explained)
8. [ODU Architecture & TR-181 Workflow Deep-Dive](#-odu-architecture--tr-181-workflow-deep-dive)
9. [Security & Privacy](#-security--privacy)
10. [Author & Credits](#-author--credits)

---

## 🔍 Overview & Motivation

The **Nokia AOD311NK** is a high-performance Qualcomm-based 5G Outdoor CPE deployed by Bharti Airtel for AirFiber fixed-wireless broadband. By default, the ISP firmware enforces several restrictions:

1. **APN Locked:** Hardcoded to `airtelfwamdu.com`. If you insert an external SIM (such as Jio or BSNL), data sessions fail to establish because the network rejects the Airtel APN.
2. **eSIM Boot Priority:** The ODU contains an embedded onboard eSIM profile. On cold boot or power cycle, the firmware queries the eSIM first (`esimStatus is Valid`), while bypassing the external physical SIM tray (`usimStatus is None`).
3. **Band Locking Restrictions:** 4G LTE is restricted to `B1, B3, B40`, locking out Jio's primary low-band coverage (**Band 5 / 850 MHz**) and 5G low-band (**n28 / 700 MHz**).
4. **Trunk Port Enforcement:** The Ethernet PoE interface communicates via tagged **VLAN 1999**, making it invisible to standard untagged network devices.

**`apnctl`** solves all these challenges directly from the terminal with a single, standalone, compiled binary without needing to open the device or solder UART wires.

---

## 🏷️ Supported Hardware & Firmware

| Parameter | Value |
| :--- | :--- |
| **Manufacturer** | Nokia Corporation |
| **Product Class** | Fixed Wireless Access (FWA) |
| **Model Name** | **AOD311NK** (FastMile 5G Receiver) |
| **Hardware Version** | `3TG03366AAAA` |
| **Software Version** | `AOD311NK_R4.0`. Also tested: R1.0 (works), R3.0 (clients get no internet, see [Community test results](#community-test-results)) |
| **Default Gateway IP** | `192.168.0.1` |
| **Management VLAN** | **VLAN 1999** |

---

## Community test results

Measured on real units. "Clients" means a PC behind the ODU on VLAN 1999 that got its address from the
ODU's DHCP. Each result is one short run, at a weak-signal spot (mostly 4G only, RSRP about -111 to -122 dBm),
so treat it as "works / does not work", not as speed.

| Firmware | SIM / APN | Mode | Clients behind the ODU |
|---|---|---|---|
| R1.0 | Jio / `jionet` | LTE only | **Works**: 25 of 25 pings, avg 125 ms, 3 of 3 pages |
| R1.0 | Jio / `jionet` | 5G NSA only | Worked (10 of 10, avg 95 ms); right after a mode change 2 of 8, then 18 of 20 at about 1.6 s |
| R1.0 | Jio / `jionet` | Auto | **No internet** (0 of 10); the ODU's IPv4 field was empty at the last reading |
| R1.0 | Airtel mobile SIM / `airtelgprs.com` | Auto | **Works**: 12 of 12, avg 65 ms; 5-minute run 295 of 296, avg 63 ms |
| R3.0 | Jio / `jionet` | Auto | **No internet** (0 of 10, twice), although the ODU's own ping from its web page worked (4 of 4) |
| R3.0 | Jio / `jionet` | LTE only | **No internet** (0 of 10), with `IPv4 192.0.0.2` shown on the ODU |
| R3.0 | Airtel mobile SIM / `airtelgprs.com` | Auto | **No internet** in three runs, including after a power cycle |

The R3.0 unit gave clients an address, gateway and DNS, and answered DNS, but forwarded nothing. I have only
one R3.0 unit, so I cannot tell whether that is the firmware or that unit.

Also tested: a TP-Link ER605 router with a WAN port set to Dynamic IP and **VLAN 1999**. On R1.0 the WAN came up
with a `192.168.0.x` address and devices behind the router reached the internet through the ODU
(traceroute: router, then `192.168.0.1`, then the internet).

How it was tested: Windows 11 with a Hyper-V external switch tagged VLAN 1999, an Ubuntu 22.04 PC using an
802.1Q VLAN 1999 interface (same results), and the router above. Ping and HTTPS to a public address, run
through a temporary host route so the path is known.

### Notes from testing

- **IPv4 can be empty right after an APN or mode change.** If `IPv4 Address` shows `None`, clients have no
  internet. On Jio it normally reads `192.0.0.2`; wait a couple of minutes, and re-apply the APN if it stays empty.
- **Login:** on both R1.0 and R3.0, `/prelogin_status_web_app.cgi` returns 404, so the serial cannot be
  auto-detected and the tool falls back to the serial hard-coded in the source. That attempt counts as a
  failed login on the unit (the reply shows `failurecount`). Use the S/N printed on the unit's label as the
  password with `-p`.
- **`apnctl n78` selects "5G SA only" (`AccessModeNo` 3).** It does not choose a band, and `status` prints the
  "5G Standalone" block whenever any 5G band is reported, so it cannot tell SA from NSA.

---

## ⚡ Key Features

* **Zero-Config Auto Serial Detection:** Automatically queries the gateway's pre-login API to retrieve the hardware Serial Number and authenticates with zero manual password entry.
* **One-Click 5G SA (Band n78) Lock:** Instantly switches the modem into pure **NR5GSA** mode, attaching to Jio's **100 MHz Band n78** high-speed channel.
* **Dynamic APN Switcher:** Modify active PDN contexts in real-time to `jionet`, `bsnlnet`, `airtelfwamdu.com`, or custom enterprise APNs.
* **Live RF & Telemetry Engine:** View live RSRP, RSRQ, SNR, RSSI, Cell ID, PCI, NCI, ARFCN, and assigned dual-stack IPv4/IPv6 addresses.
* **Remote Power Cycle:** Cleanly reboots the ODU over software without physically disconnecting the PoE injector on the roof.
* **Configuration Snapshot Exporter:** Back up all active WAN, LAN, firewall, cellular, and TR-069 configurations into structured JSON.
* **Tamper-Proof Standalone Binary:** Built as an optimized ELF 64-bit binary. Runs without Python dependencies and cannot be altered in plaintext.

---

## 🔌 Hardware & Network Setup

Because the Nokia 311NK ODU uses **VLAN 1999** on its PoE Ethernet port, clients must tag their traffic accordingly.

### Connecting via Laptop

#### Linux (Ubuntu / Kali / Debian):
```bash
# 1. Bring up physical Ethernet
sudo ip link set dev eth0 up

# 2. Create VLAN 1999 sub-interface
sudo ip link add link eth0 name eth0.1999 type vlan id 1999
sudo ip link set dev eth0.1999 up

# 3. Request IP via DHCP from ODU (assigns 192.168.0.x)
sudo dhclient -v eth0.1999
```

#### Windows:
1. Open **Device Manager** → Expand **Network Adapters** → Right-click your Intel/Realtek NIC → **Properties**.
2. Go to **Advanced** tab → Set **VLAN ID** to `1999` (or use Realtek/Intel PROSet Diagnostic Utility to create a tagged VLAN 1999 virtual adapter).
3. Set IPv4 to Obtain Automatically (DHCP) or Static `192.168.0.100` / Subnet `255.255.255.0` / Gateway `192.168.0.1`.

---

### Connecting via 3rd-Party Router

To distribute 5G internet across your home using a regular Wi-Fi router (OpenWrt, AsusWRT, TP-Link):

1. **OpenWrt:**
   - Go to **Network** → **Interfaces** → **Devices** → Add VLAN device `wan.1999`.
   - Assign `wan.1999` to the **WAN** interface (DHCP client).
2. **TP-Link / Asus (IPTV/VLAN Mode):**
   - Enable **IPTV / VLAN** in WAN settings.
   - Set **Internet VLAN ID** = `1999` (Priority `0`).

---

## 🚀 Installation

### Option 1: Using Precompiled Binary (Recommended)
```bash
# Clone the repository
git clone https://github.com/dc-voltage/airtel-nokia-311nk.git
cd airtel-nokia-311nk

# Install binary to system PATH
sudo cp apnctl /usr/local/bin/apnctl
sudo chmod +x /usr/local/bin/apnctl

# Verify installation
apnctl --help
```

### Option 2: Running via Python
```bash
pip install requests urllib3
python3 apnctl_master.py --help
```

---

## 🛠️ Command Reference & Usage

```text
======================================================================
 ███╗   ██╗ ██████╗ ██╗  ██╗██╗ █████╗     ██████╗ ██████╗ ██╗   ██╗
 ████╗  ██║██╔═══██╗██║ ██╔╝██║██╔══██╗   ██╔═══██╗██╔══██╗██║   ██║
 ██╔██╗ ██║██║   ██║█████╔╝ ██║███████║   ██║   ██║██║  ██║██║   ██║
 ██║╚██╗██║██║   ██║██╔═██╗ ██║██╔══██║   ██║   ██║██║  ██║██║   ██║
 ██║ ╚████║╚██████╔╝██║  ██╗██║██║  ██║   ╚██████╔╝██████╔╝╚██████╔╝
 ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ 
      Nokia FastMile 5G Outdoor CPE (AOD311NK) Master Toolkit
      Created by: DC-Voltage  |  https://github.com/dc-voltage
======================================================================
```

### 1. Lock to 5G SA Band n78 (Jio True 5G)
Locks the cellular radio into Standalone (SA) mode, forcing it to drop 4G LTE anchors and latch directly onto Jio's **Band n78 (3500 MHz, 100 MHz Bandwidth)**:
```bash
apnctl n78
```
*Output:*
```text
[*] Switching Cellular Access Mode to: Only 5G SA is allowed (Band n78)...
[+] SUCCESS! Mode applied: Only 5G SA is allowed (Band n78)
```

---

### 2. Reset to Auto Mode (5G SA + NSA)
Restores default dual-connectivity mode (Both 5G Standalone and Non-Standalone allowed):
```bash
apnctl auto
```

---

### 3. Lock to 4G LTE Only
Restricts the modem to 4G LTE bands only:
```bash
apnctl lte
```

---

### 4. Modify APN (Jio, BSNL, Vi, Airtel)
Set the primary PDP context APN instance:
```bash
# Set APN for Reliance Jio
apnctl set jionet

# Set APN for BSNL 4G/5G
apnctl set bsnlnet

# Set APN for Vodafone Idea (Vi)
apnctl set portalnmms

# Reset to Airtel Default
apnctl set airtelfwamdu.com
```

To view current APN instances and assigned IP addresses:
```bash
apnctl get
```

---

### 5. Live Cellular RF Telemetry
Inspect live radio signal conditions, band allocation, and network parameters:
```bash
apnctl status
```
*Output Example:*
```text
============================================================
        NOKIA AOD311NK 5G ODU CELLULAR STATUS        
============================================================
  Operator       : Jio
  SIM Slot       : USIM (Status: Valid)
  Configured Mode: Only 5G SA is allowed
  Active Tech    : NR5GSA
  APN            : jionet
  IPv4 Address   : 192.0.0.2
  IPv6 Address   : 2409:40f3:xxxx:xxxx:xxxx:xxxx:xxxx:xxxx
------------------------------------------------------------
  [5G Standalone Details]
    Band         : n78 (ARFCN: 634080)
    Bandwidth    : 100M
    PCI / NCI    : 408 / 4355227650
    RSRP / RSRQ  : -109 dBm / -11 dB
    SNR / RSSI   : 10 dB / -104 dBm
============================================================
```

---

### 6. Device Information
Display hardware model, firmware build, and masked modem identifiers:
```bash
apnctl info
```
*Output Example:*
```text
============================================================
             NOKIA AOD311NK DEVICE DETAILS           
============================================================
  Manufacturer   : Nokia
  Model / Class  : FWA (AOD311NK)
  Serial Number  : ANKODA1F000*****
  Hardware Ver   : 3TG03366AAAA
  Software Ver   : AOD311NK_R4.0
  IMEI           : 351830656333***
  eSIM ICCID     : 89918620400355*****
  System Uptime  : 3482 seconds
============================================================
```

---

### 7. Full Configuration Backup Export
Export all router parameters (WAN, LAN, Cellular, TR-069, Firewall) into a timestamped JSON file:
```bash
apnctl backup
```

---

### 8. Remote Clean Reboot
Reboot the ODU safely from your workstation:
```bash
apnctl reboot
```

---

## 💡 The Physical SIM (Jio) Reboot Issue & Permanent AT Command Fix

### Root Cause: Qualcomm SDX65 Dual-SIM Slot Selection (`AT+QUIMSLOT`)

In the Airtel firmware logs (`LOG.CellularMgr`):
```text
GetCellularNetworkIdentification: usimStatus is None, esimStatus is Valid
GetCellularNetworkIdentification: getESIMProfilesObject find esim profile, iccid is 899110...
```

1. **Dual SIM Architecture:**
   - **Slot 1 (`+QUIMSLOT: 1`)**: External physical USIM card tray (`IMSI: 405862082013816`, Reliance Jio True 5G).
   - **Slot 2 (`+QUIMSLOT: 2`)**: Internal soldered eSIM profile (`IMSI: 404100803787172`, Bharti Airtel).
2. **Boot Default:** During power-on or cold reboot, the Qualcomm SDX65 baseband driver defaults to **Slot 2** (the internal eSIM). As a result, the physical SIM tray (`Slot 1`) is left completely unpowered (`usimStatus is None`).
3. **The AT Command Solution (No Hot-Plug Needed!):**
   Instead of physically pulling out and re-inserting the SIM tray, sending `AT+QUIMSLOT=1` directly to `/dev/smd11` switches the baseband multiplexer to the physical SIM tray in software:
   ```bash
   exec 3<>/dev/smd11 && {
     echo -e "AT+QUIMSLOT=1\r" >&3
     sleep 1
     echo -e "AT+CFUN=1\r" >&3
     sleep 0.5
     exec 3>&-
   }
   ```
4. **Permanent Autonomous Daemon (`/configs/r7p.sh`)**:
   This AT switch is incorporated into [`/configs/r7p.sh`](r7p_device.sh) and executed automatically on every boot via [`/configs/aic_conf.json`](NOKIA_ODU_FULL_DUMP_20261124_LIVE/system_diagnostics/aic_conf.json), ensuring that the physical Jio SIM is powered on, registered (`+COPS: "JIO 4G"`, `rmnet_data0`/`rmnet_data1`), and routed through NAT masquerade immediately upon startup.

---

## 🔬 ODU Architecture & TR-181 Workflow Deep-Dive

For a complete architectural breakdown, partition structure, reverse-engineered TR-181 data models, and VLAN flow analysis, see the dedicated reference:
👉 **[Nokia FastMile 5G ODU Architecture & TR-181 Workflow Deep-Dive (docs/NOKIA_5G_ODU_ARCHITECTURE_AND_TR181_WORKFLOW.md)](docs/NOKIA_5G_ODU_ARCHITECTURE_AND_TR181_WORKFLOW.md)**

### Key Technical Findings:
* **Hardware & Kernel:** Qualcomm Snapdragon X65 (`sdxlemur`, ARM Cortex-A7 @ 1.0 GHz), Linux Kernel `5.4.289` PREEMPT, Realtek RTL8168 PCIe 2.5G/1G NIC (`r8168_ioss`) with Qualcomm IP Accelerator (`IPA`).
* **Storage & Partitions:** SquashFS dm-verity read-only rootfs (`/dev/ubiblock0_0`, 75MB), DSP modem firmware (`/dev/ubiblock1_0`, 81MB), persistent UBIFS `/configs` (8MB) & `/systemrw` (30MB).
* **Nokia PCD Supervisor:** Managed by `/bin/pcd` through `/etc/hb/*.pcd` dependency chains (`prepare` ➔ `SysEvent` ➔ `MQTT` ➔ `CfgMgr` ➔ `CellularMgr` ➔ `TR069Agent` / `obuspa`).
* **Dual-Plane Ethernet Architecture:**
  - **VLAN 1999 (OAM Management):** Static `192.168.0.1/24` on `bridge0` exposing local Web UI (80/443), SSH (22), and Telnet (23).
  - **VLAN 1081 (Airtel User Traffic):** Enforces Layer-2 Ethernet-over-GRE (`L2 EoGRE`) encapsulation directly to the Airtel IDU/Core.
* **Dual Cellular APNs:** Dedicated **APN 1** (`rmnet_data0`) for OAM/TR-069 ACS management vs **APN 2** (`rmnet_data1`) for high-speed subscriber 5G data.
* **Live System Backup & Dumps:** Component archives (25MB `.tar.gz`) and decrypted 1MB TR-181 tree dumps available in [`NOKIA_ODU_FULL_DUMP_20261124_LIVE/`](NOKIA_ODU_FULL_DUMP_20261124_LIVE/).

---

## 🔒 Security & Privacy

* This tool interacts strictly through legitimate local CGI / OAM endpoints over HTTPS.
* **Privacy Assurance:** No hardware serial numbers, IMEIs, IMSIs, or private location identifiers are transmitted externally. All telemetry stays strictly between your host and the CPE.

---

## 👤 Author & Credits

* **Developer:** **[DC-Voltage](https://github.com/dc-voltage)**
* **Project Repository:** [https://github.com/dc-voltage/airtel-nokia-311nk](https://github.com/dc-voltage)
* **Contributions & Bug Reports:** Open an Issue or Pull Request on GitHub.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
