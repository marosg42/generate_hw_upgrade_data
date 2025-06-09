#!/usr/bin/env python3

import argparse
import subprocess
import json
import sys
from typing import Dict, Any, List, Optional


def format_speed(speed: Optional[int]) -> str:
    """Convert speed from Mbps to human readable format"""
    if speed is None:
        return "unknown"
    if speed >= 1000:
        return f"{speed // 1000} Gbps"
    return f"{speed} Mbps"


def analyze_interfaces(machine: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze network interfaces and return interface info and connection status"""
    if "interface_set" not in machine:
        return {"interfaces": [], "connected_count": 0, "meets_requirement": False}

    interfaces = []
    connected_count = 0

    for interface in machine["interface_set"]:
        interface_name = interface.get("name", "unknown")

        # Skip VLAN interfaces (contain dots in the name)
        if "." in interface_name:
            continue

        link_speed = interface.get("link_speed")
        is_connected = link_speed is not None and link_speed > 0

        if is_connected:
            connected_count += 1

        interface_info = {
            "name": interface_name,
            "enabled": interface.get("enabled", False),
            "interface_speed": interface.get("interface_speed"),
            "link_speed": link_speed,
            "interface_speed_formatted": format_speed(interface.get("interface_speed")),
            "link_speed_formatted": format_speed(link_speed),
            "is_connected": is_connected,
        }
        interfaces.append(interface_info)

    meets_requirement = connected_count >= 3

    return {
        "interfaces": interfaces,
        "connected_count": connected_count,
        "meets_requirement": meets_requirement,
    }


def print_machine_details(machine_name: str, interface_data: Dict[str, Any]) -> None:
    """Print detailed information for a single machine"""
    interfaces = interface_data["interfaces"]
    connected_count = interface_data["connected_count"]
    meets_requirement = interface_data["meets_requirement"]

    status_icon = "✅" if meets_requirement else "❌"
    print(f"\nMachine: {machine_name} {status_icon}")
    print(f"Network interfaces ({len(interfaces)}):")

    if not interfaces:
        print("  No interface information available")
    else:
        for interface in interfaces:
            status = "enabled" if interface["enabled"] else "disabled"
            connection_status = (
                "connected" if interface["is_connected"] else "disconnected"
            )
            print(f"  - {interface['name']}: {status}, {connection_status}")
            print(f"    Interface speed: {interface['interface_speed_formatted']}")
            print(f"    Link speed: {interface['link_speed_formatted']}")

    print(f"\nConnected NICs: {connected_count} (need ≥3)")
    print(f"Meets requirement: {'✅ YES' if meets_requirement else '❌ NO'}")
    print("-" * 60)


def get_maas_machines(
    profile: str, tag: Optional[str] = None, hostname: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Query MAAS for machines and return parsed JSON"""
    cmd = ["maas", profile, "machines", "read"]

    if tag:
        cmd.append(f"tags={tag}")

    if hostname:
        cmd.append(f"hostname={hostname}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running maas command: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}", file=sys.stderr)
        sys.exit(1)


def print_summary(
    machines_meeting: List[str], machines_not_meeting: List[str], total_machines: int
) -> None:
    """Print the summary of machines meeting and not meeting requirements"""
    print("\n" + "=" * 60)
    print("SUMMARY - Network Interface Requirements:")
    print("=" * 60)

    print(f"\nTotal machines processed: {total_machines}")
    print(f"Machines meeting requirements (≥3 connected NICs): {len(machines_meeting)}")
    print(f"Machines not meeting requirements: {len(machines_not_meeting)}")

    if machines_meeting:
        print(f"\n✅ MACHINES MEETING REQUIREMENTS ({len(machines_meeting)}):")
        for machine in machines_meeting:
            print(f"  - {machine}")

    if machines_not_meeting:
        print(f"\n❌ MACHINES NOT MEETING REQUIREMENTS ({len(machines_not_meeting)}):")
        for machine in machines_not_meeting:
            print(f"  - {machine}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query MAAS machines and show network interface information"
    )
    parser.add_argument("profile", help="MAAS profile name (required)")
    parser.add_argument("--tag", help="Filter by tag (optional)")
    parser.add_argument("--hostname", help="Filter by hostname (optional)")

    args = parser.parse_args()

    machines = get_maas_machines(args.profile, args.tag, args.hostname)
    print(f"Number of machines returned: {len(machines)}")

    machines_meeting = []
    machines_not_meeting = []

    # Process each machine
    for machine in machines:
        machine_name = machine.get(
            "hostname", machine.get("fqdn", machine.get("system_id", "unknown"))
        )

        # Analyze machine interfaces
        interface_data = analyze_interfaces(machine)

        # Print machine details
        print_machine_details(machine_name, interface_data)

        # Categorize machine
        if interface_data["meets_requirement"]:
            machines_meeting.append(machine_name)
        else:
            machines_not_meeting.append(machine_name)

    # Print summary
    print_summary(machines_meeting, machines_not_meeting, len(machines))


if __name__ == "__main__":
    main()
