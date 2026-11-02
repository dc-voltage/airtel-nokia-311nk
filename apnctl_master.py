#!/usr/bin/env python3
"""
Nokia FastMile 5G Outdoor CPE (AOD311NK) Master Toolkit
Developed by: DC-Voltage (https://github.com/dc-voltage)

Features:
  - APN Management (get, set)
  - 5G SA Band n78 / NSA / LTE Mode Switcher
  - Live RF & Cellular Telemetry (RSRP, SNR, Bandwidth, PCI)
  - Device Info, Full Config Backup, & Clean Remote Reboot
"""

import sys
import os
import argparse
import json
import base64
import hashlib
import webbrowser
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROUTER_IP = os.getenv("ROUTER_IP", "192.168.0.1")
DEFAULT_USER = "admin"
DEFAULT_PASS = "ANKODA1F00016691"
GITHUB_URL = "https://github.com/dc-voltage"

BANNER = f"""
\033[1;36m======================================================================
 ███╗   ██╗ ██████╗ ██╗  ██╗██╗ █████╗     ██████╗ ██████╗ ██╗   ██╗
 ████╗  ██║██╔═══██╗██║ ██╔╝██║██╔══██╗   ██╔═══██╗██╔══██╗██║   ██║
 ██╔██╗ ██║██║   ██║█████╔╝ ██║███████║   ██║   ██║██║  ██║██║   ██║
 ██║╚██╗██║██║   ██║██╔═██╗ ██║██╔══██║   ██║   ██║██║  ██║██║   ██║
 ██║ ╚████║╚██████╔╝██║  ██╗██║██║  ██║   ╚██████╔╝██████╔╝╚██████╔╝
 ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ 
      Nokia FastMile 5G Outdoor CPE (AOD311NK) Master Toolkit
      Created by: DC-Voltage  |  \033[4;33m{GITHUB_URL}\033[0m\033[1;36m
======================================================================\033[0m
"""

ACCESS_MODES = {
    1: "Both 5G SA and 5G NSA are allowed (Auto)",
    2: "Only 5G NSA is allowed",
    3: "Only 5G SA is allowed (Band n78)",
    4: "Only LTE is allowed (4G Only)"
}

MODE_ALIASES = {
    "n78": 3,
    "sa": 3,
    "5gsa": 3,
    "jio5g": 3,
    "nsa": 2,
    "5gnsa": 2,
    "auto": 1,
    "both": 1,
    "default": 1,
    "lte": 4,
    "4g": 4
}

def print_banner():
    print(BANNER)

def base64url_escape(s):
    res = []
    for c in s:
        if c == '+':
            res.append('-')
        elif c == '/':
            res.append('_')
        elif c == '=':
            res.append('.')
        else:
            res.append(c)
    return ''.join(res)

def sha256_b64(x, k):
    data = (f"{x}:{k}").encode('utf-8')
    digest = hashlib.sha256(data).digest()
    return base64.b64encode(digest).decode('ascii')

def sha256url(x, k):
    return base64url_escape(sha256_b64(x, k))

def auto_detect_serial(base_url):
    try:
        r = requests.get(f"{base_url}/prelogin_status_web_app.cgi", verify=False, timeout=4)
        dev = r.json().get("device_info", [{}])[0]
        return dev.get("SerialNumber")
    except:
        return None

def do_login(username, password, base_url, verbose=False):
    s = requests.Session()
    s.verify = False

    # Auto-detect Serial Number if password is not provided or using default
    if not password or password == DEFAULT_PASS:
        detected_sn = auto_detect_serial(base_url)
        if detected_sn:
            if verbose:
                print(f"[*] Auto-detected ODU Serial Number: {detected_sn}")
            password = detected_sn
        else:
            password = DEFAULT_PASS

    if verbose:
        print("[*] Contacting gateway at:", base_url)
    try:
        r = s.post(f"{base_url}/login_web_app.cgi?nonce", data={"userName": username}, timeout=8)
        nonce_info = r.json()
    except Exception as e:
        print(f"\033[1;31m[-] Error connecting to {base_url}: {e}\033[0m")
        sys.exit(1)

    nonce = nonce_info.get("nonce")
    random_key = str(nonce_info.get("randomKey", ""))
    iterations = int(nonce_info.get("iterations", 1))

    c = sha256url(username, nonce)
    escaped_nonce = base64url_escape(nonce)
    r_salt = s.post(f"{base_url}/login_web_app.cgi?salt",
                    data=f"userhash={c}&nonce={escaped_nonce}",
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=6)
    alati = r_salt.json().get("alati", "")

    if iterations >= 1:
        r_hash = hashlib.sha256((alati + password).encode('utf-8')).hexdigest()
    else:
        r_hash = alati + password

    for _ in range(1, iterations):
        r_hash = hashlib.sha256(bytes.fromhex(r_hash)).hexdigest()

    _u = sha256_b64(username, r_hash.lower())
    m = sha256url(_u, nonce)
    C = sha256url(random_key, nonce)

    raw_key = os.urandom(16)
    raw_iv = os.urandom(16)
    T = base64.b64encode(raw_key).decode('ascii')
    P = base64.b64encode(raw_iv).decode('ascii')
    enckey = base64url_escape(T)
    enciv = base64url_escape(P)

    post_data = f"userhash={c}&RandomKeyhash={C}&response={m}&nonce={escaped_nonce}&enckey={enckey}&enciv={enciv}"
    r_login = s.post(f"{base_url}/login_web_app.cgi",
                     data=post_data,
                     headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=6)
    
    login_resp = r_login.json()
    if login_resp.get("result") != 0:
        print(f"\033[1;31m[-] Authentication failed: {login_resp}\033[0m")
        sys.exit(1)

    token = login_resp.get("token")
    return s, token

def call_ubus(s, base_url, token, function_name, paralist=None):
    if paralist is None:
        paralist = []
    payload = {
        "version": 1,
        "csrf_token": token,
        "id": 1,
        "interface": "Nokia.GenericService",
        "service": "OAM",
        "function": function_name,
        "paralist": paralist
    }
    r = s.post(f"{base_url}/service_function_web_app.cgi", json=payload, verify=False, timeout=8)
    return r.json()

def get_session_and_token(args):
    base_url = f"https://{args.host}"
    return do_login(args.user, args.password, base_url, args.verbose)

# Command: APN Get
def cmd_get(args):
    base_url = f"https://{args.host}"
    s, token = get_session_and_token(args)
    data = call_ubus(s, base_url, token, "GetAPN")
    apn_list = data.get("FunctionResult", {}).get("APNList", [])
    print(f"\033[1;32m[+] Configured APNs ({len(apn_list)} instance(s)):\033[0m")
    for item in apn_list:
        inst_id = item.get("APNInstanceID")
        apn = item.get("AccessPointName")
        connected = item.get("ConnectionState")
        v4 = item.get("IPv4Address")
        v6 = item.get("IPv6Address")
        status = "\033[1;32mCONNECTED\033[0m" if connected else "\033[1;31mDISCONNECTED\033[0m"
        print(f"  Instance {inst_id}: APN = '\033[1;33m{apn}\033[0m' | Status = {status} | IPv4 = {v4} | IPv6 = {v6}")

# Command: APN Set
def cmd_set(args):
    new_apn = args.apn_name.strip()
    target_instance = args.instance
    base_url = f"https://{args.host}"
    print(f"[*] Setting APN instance {target_instance} to: '\033[1;33m{new_apn}\033[0m'...")

    s, token = get_session_and_token(args)
    data = call_ubus(s, base_url, token, "GetAPN")
    apn_list = data.get("FunctionResult", {}).get("APNList", [])
    
    target_obj = None
    for item in apn_list:
        if item.get("APNInstanceID") == target_instance:
            target_obj = item
            break
            
    if not target_obj:
        print(f"\033[1;31m[-] APN instance {target_instance} not found!\033[0m")
        sys.exit(1)

    old_apn = target_obj.get("AccessPointName")
    print(f"[*] Current APN: '{old_apn}' -> New APN: '{new_apn}'")
    target_obj["AccessPointName"] = new_apn

    res = call_ubus(s, base_url, token, "ModifyAPN", [target_obj])
    if res.get("result") == 0:
        print(f"\033[1;32m[+] SUCCESS! APN updated to '{new_apn}'.\033[0m")
    else:
        print(f"\033[1;31m[-] Error updating APN: {res}\033[0m")

# Command: Set Mode Internal
def set_mode_internal(s, base_url, token, mode_num):
    mode_desc = ACCESS_MODES.get(mode_num, f"Mode {mode_num}")
    print(f"[*] Switching Cellular Access Mode to: \033[1;33m{mode_desc}\033[0m...")
    paralist = [{"AccessModeNo": mode_num, "NetworkSlicingEnable": False}]
    res = call_ubus(s, base_url, token, "SetCellularAccessConfig", paralist)
    if res.get("result") == 0:
        print(f"\033[1;32m[+] SUCCESS! Mode applied: {mode_desc}\033[0m")
    else:
        print(f"\033[1;31m[-] Error setting mode: {res}\033[0m")

# Command: Mode
def cmd_mode(args):
    base_url = f"https://{args.host}"
    s, token = get_session_and_token(args)
    
    if not args.mode_target:
        res = call_ubus(s, base_url, token, "GetCellularAccessConfig")
        func_res = res.get("FunctionResult", {})
        curr_mode = func_res.get("AccessModeNo")
        curr_brief = func_res.get("AccessModeBrief")
        print(f"\033[1;32m[+] Current Mode: {curr_brief} (AccessModeNo={curr_mode})\033[0m")
        print("\nAvailable options:")
        print("  apnctl n78        -> Lock to 5G SA (Band n78 / Jio 5G)")
        print("  apnctl auto       -> Both 5G SA & NSA (Default Airtel/Jio)")
        print("  apnctl lte        -> 4G LTE Only")
        print("  apnctl mode nsa   -> 5G NSA Only")
        return

    target = args.mode_target.lower().strip()
    if target not in MODE_ALIASES:
        print(f"\033[1;31m[-] Unknown mode '{target}'! Choose from: n78, auto, lte, nsa\033[0m")
        sys.exit(1)
        
    set_mode_internal(s, base_url, token, MODE_ALIASES[target])

def cmd_n78(args):
    base_url = f"https://{args.host}"
    s, token = get_session_and_token(args)
    set_mode_internal(s, base_url, token, 3)

def cmd_auto(args):
    base_url = f"https://{args.host}"
    s, token = get_session_and_token(args)
    set_mode_internal(s, base_url, token, 1)

def cmd_lte(args):
    base_url = f"https://{args.host}"
    s, token = get_session_and_token(args)
    set_mode_internal(s, base_url, token, 4)

# Command: Status
def cmd_status(args):
    base_url = f"https://{args.host}"
    s, token = get_session_and_token(args)
    
    net_id = call_ubus(s, base_url, token, "GetCellularNetworkIdentification").get("FunctionResult", {})
    operator_name = net_id.get("Name", "Unknown")
    
    sim_info = call_ubus(s, base_url, token, "GetSIMInfo").get("FunctionResult", {})
    sim_type = sim_info.get("SIMType", "Unknown")
    sim_status = sim_info.get("SIMStatus", "Unknown")
    
    mode_info = call_ubus(s, base_url, token, "GetCellularAccessConfig").get("FunctionResult", {})
    access_brief = mode_info.get("AccessModeBrief", "Unknown")
    
    r = s.get(f"{base_url}/status_get_web_app.cgi", verify=False)
    rf_data = r.json()
    
    acc_tech = ""
    for item in rf_data.get("AccessTechnology", []):
        acc_tech = item.get("CurrentAccessTechnology", "")
        
    c5g = rf_data.get("cell_5G_stats_cfg", [{}])[0].get("stat", {})
    c4g = rf_data.get("cell_LTE_stats_cfg", [{}])[0].get("stat", {})
    
    apn_data = call_ubus(s, base_url, token, "GetAPN").get("FunctionResult", {}).get("APNList", [])
    active_apn = apn_data[0].get("AccessPointName", "") if apn_data else ""
    ipv4 = apn_data[0].get("IPv4Address", "") if apn_data else ""
    ipv6 = apn_data[0].get("IPv6Address", "") if apn_data else ""
    
    print("\033[1;34m" + "=" * 60 + "\033[0m")
    print("\033[1;37m        NOKIA AOD311NK 5G ODU CELLULAR STATUS        \033[0m")
    print("\033[1;34m" + "=" * 60 + "\033[0m")
    print(f"  Operator       : \033[1;32m{operator_name}\033[0m")
    print(f"  SIM Slot       : \033[1;33m{sim_type}\033[0m (Status: {sim_status})")
    print(f"  Configured Mode: {access_brief}")
    print(f"  Active Tech    : \033[1;35m{acc_tech or 'Scanning / None'}\033[0m")
    print(f"  APN            : \033[1;33m{active_apn}\033[0m")
    print(f"  IPv4 Address   : {ipv4 or 'None'}")
    print(f"  IPv6 Address   : {ipv6 or 'None'}")
    print("\033[1;34m" + "-" * 60 + "\033[0m")
    
    if acc_tech == "NR5GSA" or c5g.get("Band"):
        print("\033[1;36m  [5G Standalone Details]\033[0m")
        print(f"    Band         : \033[1;32m{c5g.get('Band')}\033[0m (ARFCN: {c5g.get('Downlink_NR_ARFCN')})")
        print(f"    Bandwidth    : {c5g.get('Bandwidth')}")
        print(f"    PCI / NCI    : {c5g.get('PhysicalCellID')} / {c5g.get('NCI')}")
        print(f"    RSRP / RSRQ  : \033[1;33m{c5g.get('RSRPCurrent')} dBm\033[0m / {c5g.get('RSRQCurrent')} dB")
        print(f"    SNR / RSSI   : \033[1;33m{c5g.get('SNRCurrent')} dB\033[0m / {c5g.get('RSSICurrent')} dBm")
    elif acc_tech == "LTE" or c4g.get("Band"):
        print("\033[1;36m  [4G LTE Details]\033[0m")
        print(f"    Band         : \033[1;32m{c4g.get('Band')}\033[0m (EARFCN: {c4g.get('DownlinkEarfcn')})")
        print(f"    Bandwidth    : {c4g.get('Bandwidth')}")
        print(f"    PCI / eNBID  : {c4g.get('PhysicalCellID')} / {c4g.get('eNBID')}")
        print(f"    RSRP / RSRQ  : \033[1;33m{c4g.get('RSRPCurrent')} dBm\033[0m / {c4g.get('RSRQCurrent')} dB")
        print(f"    SNR / RSSI   : \033[1;33m{c4g.get('SNRCurrent')} dB\033[0m / {c4g.get('RSSICurrent')} dBm")
    else:
        print("  \033[1;33mNo active RF connection.\033[0m")
    print("\033[1;34m" + "=" * 60 + "\033[0m")

# Command: Info
def cmd_info(args):
    base_url = f"https://{args.host}"
    s, token = get_session_and_token(args)
    r_dev = s.get(f"{base_url}/device_status_web_app.cgi?getroot", verify=False).json()
    r_fm = s.get(f"{base_url}/fastmile_statistics_status_web_app.cgi", verify=False).json()
    
    dev = r_dev.get("device_info", {})
    imei = r_fm.get("network_cfg", [{}])[0].get("IMEI", "")
    sim = r_fm.get("sim_cfg", [{}])[0]
    
    print("\033[1;34m" + "=" * 60 + "\033[0m")
    print("\033[1;37m             NOKIA AOD311NK DEVICE DETAILS           \033[0m")
    print("\033[1;34m" + "=" * 60 + "\033[0m")
    print(f"  Manufacturer   : {dev.get('Manufacturer', 'Nokia')}")
    print(f"  Model / Class  : {dev.get('ProductClass', 'FWA')} ({dev.get('ModelName', '')})")
    print(f"  Serial Number  : \033[1;33m{dev.get('SerialNumber', '')}\033[0m")
    print(f"  Hardware Ver   : {dev.get('HardwareVersion', '')}")
    print(f"  Software Ver   : \033[1;32m{dev.get('SoftwareVersion', '')}\033[0m")
    print(f"  IMEI           : {imei}")
    print(f"  eSIM EID       : {sim.get('Eid', '')}")
    print(f"  eSIM ICCID     : {sim.get('ICCID', '')}")
    print(f"  System Uptime  : {dev.get('UpTime', 0)} seconds")
    print("\033[1;34m" + "=" * 60 + "\033[0m")

# Command: Backup
def cmd_backup(args):
    base_url = f"https://{args.host}"
    s, token = get_session_and_token(args)
    print("[*] Fetching complete router configuration snapshot...")
    backup = {}
    endpoints = [
        ("device_info", "device_status_web_app.cgi?getroot"),
        ("wan_config", "wan_config_glb_status_web_app.cgi"),
        ("cellular_status", "status_get_web_app.cgi"),
        ("fastmile_stats", "fastmile_statistics_status_web_app.cgi"),
        ("lan_ipv4", "lan_ipv4_status_web_app.cgi"),
        ("lan_status", "lan_status_web_app.cgi?lan"),
        ("firewall_status", "firewall_status_web_app.cgi?fire"),
    ]
    for key, path in endpoints:
        try:
            r = s.get(f"{base_url}/{path}", verify=False, timeout=5)
            backup[key] = r.json()
        except:
            pass

    out_file = args.output or f"nokia_backup_{args.host}.json"
    with open(out_file, "w") as f:
        json.dump(backup, f, indent=2)
    print(f"\033[1;32m[+] Configuration backup saved to: {out_file}\033[0m")

# Command: Reboot
def cmd_reboot(args):
    base_url = f"https://{args.host}"
    s, token = get_session_and_token(args)
    confirm = input("\033[1;31m[!] Are you sure you want to reboot the ODU? (y/N): \033[0m")
    if confirm.lower() != 'y':
        print("[*] Cancelled.")
        return
    print("[*] Sending reboot command to Nokia ODU...")
    r = s.post(f"{base_url}/reboot_web_app.cgi", headers={"csrf_token": token}, verify=False)
    print(f"\033[1;32m[+] Reboot command sent! Device is restarting now.\033[0m")

# Command: GitHub
def cmd_github(args):
    print(f"[*] Opening GitHub page: {GITHUB_URL}...")
    try:
        webbrowser.open(GITHUB_URL)
    except:
        pass
    print(f"\033[1;32m[+] Follow & Star on GitHub: {GITHUB_URL}\033[0m")

def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="apnctl - Nokia FastMile 5G Outdoor CPE (AOD311NK) Master Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--host", default=ROUTER_IP, help=f"Gateway IP (default: {ROUTER_IP})")
    parser.add_argument("-u", "--user", default=DEFAULT_USER, help=f"Web username (default: {DEFAULT_USER})")
    parser.add_argument("-p", "--password", default=None, help="Device password (default: auto-detect serial number)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose debug output")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # get
    sub.add_parser("get", help="Get active APN configuration")

    # set
    set_p = sub.add_parser("set", help="Set APN name (e.g. jionet, airtelfwamdu.com, bsnlnet)")
    set_p.add_argument("apn_name", help="New APN name")
    set_p.add_argument("-i", "--instance", type=int, default=1, help="APN Instance ID (default: 1)")

    # band & mode shortcuts
    sub.add_parser("n78", help="Lock strictly to 5G SA (Band n78 / Jio 5G)")
    sub.add_parser("auto", help="Reset to Auto (Both 5G SA & NSA)")
    sub.add_parser("lte", help="Lock to 4G LTE Only")

    # mode command
    mode_p = sub.add_parser("mode", help="Get or set mode (n78, auto, lte, nsa)")
    mode_p.add_argument("mode_target", nargs="?", help="Target mode: n78, auto, lte, nsa")

    # status
    sub.add_parser("status", help="Get live RF telemetry (Operator, SIM, Band n78, RSRP, SNR, IP)")

    # info
    sub.add_parser("info", help="Get device serial, IMEI, eSIM EID, software version")

    # backup
    b_p = sub.add_parser("backup", help="Export full configuration snapshot to JSON")
    b_p.add_argument("-o", "--output", help="Output JSON file path")

    # reboot
    sub.add_parser("reboot", help="Remotely reboot the ODU")

    # github
    sub.add_parser("github", help="Visit project GitHub page")

    args = parser.parse_args()

    dispatch = {
        "get": cmd_get,
        "set": cmd_set,
        "n78": cmd_n78,
        "auto": cmd_auto,
        "lte": cmd_lte,
        "mode": cmd_mode,
        "status": cmd_status,
        "info": cmd_info,
        "backup": cmd_backup,
        "reboot": cmd_reboot,
        "github": cmd_github,
    }

    if args.subcommand in dispatch:
        dispatch[args.subcommand](args)

if __name__ == "__main__":
    main()
