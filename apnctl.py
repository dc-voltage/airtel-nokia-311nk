#!/usr/bin/env python3
"""
Native Linux Python implementation of apnctl for Nokia AOD311NK (Airtel 5G Outdoor Unit)
Supports:
  - APN management (get, set)
  - 5G SA / n78 band lock (mode n78, mode auto, mode lte, mode nsa)
  - Detailed live telemetry (status)
"""

import sys
import argparse
import json
import urllib3
import requests
from router_login import do_login

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROUTER_IP = "192.168.0.1"
DEFAULT_USER = "admin"
DEFAULT_PASS = "ANKODA1F00016691"
SERVICE_URL = f"https://{ROUTER_IP}/service_function_web_app.cgi"

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

def get_session_and_token(user, password, base_url=f"https://{ROUTER_IP}"):
    s, res, _, _ = do_login(user, password, base_url)
    if res.get("result") != 0:
        print(f"[-] Login failed: {res}")
        sys.exit(1)
    return s, res.get("token")

def call_ubus(s, token, function_name, paralist=None):
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
    r = s.post(SERVICE_URL, json=payload, verify=False)
    return r.json()

def cmd_get(args):
    s, token = get_session_and_token(args.user, args.password)
    data = call_ubus(s, token, "GetAPN")
    apn_list = data.get("FunctionResult", {}).get("APNList", [])
    print(f"[+] Total APN entries found: {len(apn_list)}")
    for item in apn_list:
        inst_id = item.get("APNInstanceID")
        apn = item.get("AccessPointName")
        connected = item.get("ConnectionState")
        v4 = item.get("IPv4Address")
        v6 = item.get("IPv6Address")
        status = "CONNECTED" if connected else "DISCONNECTED"
        print(f"  Instance {inst_id}: APN='{apn}' | Status={status} | IPv4={v4} | IPv6={v6}")

def cmd_set(args):
    new_apn = args.apn_name.strip()
    target_instance = args.instance
    print(f"[*] Setting APN instance {target_instance} to: '{new_apn}'...")

    s, token = get_session_and_token(args.user, args.password)
    # 1. Fetch current APN List
    data = call_ubus(s, token, "GetAPN")
    apn_list = data.get("FunctionResult", {}).get("APNList", [])
    
    target_obj = None
    for item in apn_list:
        if item.get("APNInstanceID") == target_instance:
            target_obj = item
            break
            
    if not target_obj:
        print(f"[-] APN instance {target_instance} not found!")
        sys.exit(1)

    old_apn = target_obj.get("AccessPointName")
    print(f"[*] Current APN: '{old_apn}' -> New APN: '{new_apn}'")
    target_obj["AccessPointName"] = new_apn

    # 2. Modify APN
    res = call_ubus(s, token, "ModifyAPN", [target_obj])
    if res.get("result") == 0:
        print(f"[+] SUCCESS! APN updated to '{new_apn}'.")
    else:
        print(f"[-] Error updating APN: {res}")

def set_mode_internal(s, token, mode_num):
    mode_desc = ACCESS_MODES.get(mode_num, f"Mode {mode_num}")
    print(f"[*] Switching Cellular Access Mode to: {mode_desc}...")
    paralist = [{"AccessModeNo": mode_num, "NetworkSlicingEnable": False}]
    res = call_ubus(s, token, "SetCellularAccessConfig", paralist)
    if res.get("result") == 0:
        print(f"[+] SUCCESS! Mode applied: {mode_desc}")
    else:
        print(f"[-] Error setting mode: {res}")

def cmd_mode(args):
    s, token = get_session_and_token(args.user, args.password)
    
    if not args.mode_target:
        # Just show current mode
        res = call_ubus(s, token, "GetCellularAccessConfig")
        func_res = res.get("FunctionResult", {})
        curr_mode = func_res.get("AccessModeNo")
        curr_brief = func_res.get("AccessModeBrief")
        print(f"[+] Current Cellular Mode: {curr_brief} (AccessModeNo={curr_mode})")
        print("\nAvailable options to switch:")
        print("  python3 apnctl.py mode n78   -> Lock to 5G SA (Band n78 / Jio 5G)")
        print("  python3 apnctl.py mode auto  -> Both 5G SA & NSA (Default Airtel/Jio)")
        print("  python3 apnctl.py mode lte   -> 4G LTE Only")
        print("  python3 apnctl.py mode nsa   -> 5G NSA Only")
        return

    target = args.mode_target.lower().strip()
    if target not in MODE_ALIASES:
        print(f"[-] Unknown mode '{target}'! Choose from: n78, auto, lte, nsa")
        sys.exit(1)
        
    mode_num = MODE_ALIASES[target]
    set_mode_internal(s, token, mode_num)

def cmd_n78(args):
    s, token = get_session_and_token(args.user, args.password)
    set_mode_internal(s, token, 3)

def cmd_auto(args):
    s, token = get_session_and_token(args.user, args.password)
    set_mode_internal(s, token, 1)

def cmd_status(args):
    s, token = get_session_and_token(args.user, args.password)
    
    # 1. Network identification
    net_id = call_ubus(s, token, "GetCellularNetworkIdentification").get("FunctionResult", {})
    operator_name = net_id.get("Name", "Unknown")
    
    # 2. SIM Info
    sim_info = call_ubus(s, token, "GetSIMInfo").get("FunctionResult", {})
    sim_type = sim_info.get("SIMType", "Unknown")
    sim_status = sim_info.get("SIMStatus", "Unknown")
    
    # 3. Cellular Access Mode
    mode_info = call_ubus(s, token, "GetCellularAccessConfig").get("FunctionResult", {})
    access_brief = mode_info.get("AccessModeBrief", "Unknown")
    
    # 4. RF Statistics
    r = s.get(f"https://{ROUTER_IP}/status_get_web_app.cgi", verify=False)
    rf_data = r.json()
    
    acc_tech = ""
    for item in rf_data.get("AccessTechnology", []):
        acc_tech = item.get("CurrentAccessTechnology", "")
        
    c5g = rf_data.get("cell_5G_stats_cfg", [{}])[0].get("stat", {})
    c4g = rf_data.get("cell_LTE_stats_cfg", [{}])[0].get("stat", {})
    
    # 5. APN & IP
    apn_data = call_ubus(s, token, "GetAPN").get("FunctionResult", {}).get("APNList", [])
    active_apn = apn_data[0].get("AccessPointName", "") if apn_data else ""
    ipv4 = apn_data[0].get("IPv4Address", "") if apn_data else ""
    ipv6 = apn_data[0].get("IPv6Address", "") if apn_data else ""
    
    print("=" * 55)
    print("        NOKIA AOD311NK 5G ODU CELLULAR STATUS        ")
    print("=" * 55)
    print(f"  Operator       : {operator_name}")
    print(f"  SIM Slot       : {sim_type} (Status: {sim_status})")
    print(f"  Configured Mode: {access_brief}")
    print(f"  Active Tech    : {acc_tech or 'Scanning / None'}")
    print(f"  APN            : {active_apn}")
    print(f"  IPv4 Address   : {ipv4 or 'None'}")
    print(f"  IPv6 Address   : {ipv6 or 'None'}")
    print("-" * 55)
    
    if acc_tech == "NR5GSA" or c5g.get("Band"):
        print("  [5G Standalone Details]")
        print(f"    Band         : {c5g.get('Band')} (ARFCN: {c5g.get('Downlink_NR_ARFCN')})")
        print(f"    Bandwidth    : {c5g.get('Bandwidth')}")
        print(f"    PCI / NCI    : {c5g.get('PhysicalCellID')} / {c5g.get('NCI')}")
        print(f"    RSRP / RSRQ  : {c5g.get('RSRPCurrent')} dBm / {c5g.get('RSRQCurrent')} dB")
        print(f"    SNR / RSSI   : {c5g.get('SNRCurrent')} dB / {c5g.get('RSSICurrent')} dBm")
    elif acc_tech == "LTE" or c4g.get("Band"):
        print("  [4G LTE Details]")
        print(f"    Band         : {c4g.get('Band')} (EARFCN: {c4g.get('DownlinkEarfcn')})")
        print(f"    Bandwidth    : {c4g.get('Bandwidth')}")
        print(f"    PCI / eNBID  : {c4g.get('PhysicalCellID')} / {c4g.get('eNBID')}")
        print(f"    RSRP / RSRQ  : {c4g.get('RSRPCurrent')} dBm / {c4g.get('RSRQCurrent')} dB")
        print(f"    SNR / RSSI   : {c4g.get('SNRCurrent')} dB / {c4g.get('RSSICurrent')} dBm")
    else:
        print("  No active RF connection.")
    print("=" * 55)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="apnctl - Nokia AOD311NK 5G APN & Band Manager")
    parser.add_argument("-u", "--user", default=DEFAULT_USER, help="Web username")
    parser.add_argument("-p", "--password", default=DEFAULT_PASS, help="Web password")
    
    sub = parser.add_subparsers(dest="subcommand", required=True)
    
    # get
    sub.add_parser("get", help="Get current APN configuration")
    
    # set
    set_p = sub.add_parser("set", help="Set APN name (e.g. jionet, airtelfwamdu.com, bsnlnet)")
    set_p.add_argument("apn_name", help="New APN name")
    set_p.add_argument("-i", "--instance", type=int, default=1, help="APN Instance ID (default 1)")
    
    # mode
    mode_p = sub.add_parser("mode", help="Get or set Cellular Access Mode (n78, auto, lte, nsa)")
    mode_p.add_argument("mode_target", nargs="?", help="Target mode: n78 (5G SA), auto, lte (4G), nsa")
    
    # direct shortcuts
    sub.add_parser("n78", help="Quick shortcut to lock to Band n78 (5G SA only)")
    sub.add_parser("auto", help="Quick shortcut to reset to Auto (5G SA + NSA)")
    
    # status
    sub.add_parser("status", help="Get comprehensive cellular RF & network telemetry")
    
    args = parser.parse_args()
    
    if args.subcommand == "get":
        cmd_get(args)
    elif args.subcommand == "set":
        cmd_set(args)
    elif args.subcommand == "mode":
        cmd_mode(args)
    elif args.subcommand == "n78":
        cmd_n78(args)
    elif args.subcommand == "auto":
        cmd_auto(args)
    elif args.subcommand == "status":
        cmd_status(args)
