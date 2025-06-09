#!/usr/bin/env python3

import argparse
import subprocess
import json
import sys
from typing import Dict, Any, List, Optional


def format_size(size_bytes: int) -> str:
    """Convert bytes to TiB and TB format"""
    tib = size_bytes / (1024**4)
    tb = size_bytes / (1000**4)
    return f"{tib:.2f} TiB ({tb:.2f} TB)"


def analyze_boot_disk(machine: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze boot disk and return disk info and status"""
    boot_disk = machine.get("boot_disk")
    if boot_disk is None:
        return {
            "id": None,
            "size": 0,
            "is_ssd": False,
            "is_1tb_ssd": False,
            "info": "No boot disk information available",
        }

    boot_disk_id = boot_disk.get("id")
    boot_disk_size = boot_disk.get("size", 0)
    boot_disk_is_ssd = "ssd" in boot_disk.get("tags", [])
    boot_disk_1tb_ssd = boot_disk_is_ssd and boot_disk_size >= 1_000_000_000_000

    disk_type = "ssd" if boot_disk_is_ssd else "not ssd"
    size_info = format_size(boot_disk_size)
    info = f"{boot_disk.get('name', 'unknown')} - {size_info} ({disk_type})"

    return {
        "id": boot_disk_id,
        "size": boot_disk_size,
        "is_ssd": boot_disk_is_ssd,
        "is_1tb_ssd": boot_disk_1tb_ssd,
        "info": info,
    }


def analyze_block_devices(
    machine: Dict[str, Any], boot_disk_id: Optional[int]
) -> Dict[str, Any]:
    """Analyze block devices and return counts and device info"""
    if "blockdevice_set" not in machine:
        return {
            "additional_1tb_ssds": 0,
            "has_non_boot_ssd_under_1tb": False,
            "device_info": [],
        }

    additional_1tb_ssds = 0
    has_non_boot_ssd_under_1tb = False
    device_info = []

    for device in machine["blockdevice_set"]:
        device_id = device.get("id")
        device_size = device.get("size", 0)
        device_is_ssd = "ssd" in device.get("tags", [])
        device_type = (
            "ssd"
            if device_is_ssd
            else "rotary" if "rotary" in device.get("tags", []) else "unknown"
        )

        size_info = format_size(device_size)
        info = f"{device.get('name', 'unnamed')}: {size_info} ({device_type})"
        device_info.append(info)

        # Count additional 1TB+ SSDs (not the boot disk)
        if device_id != boot_disk_id:
            if device_is_ssd and device_size >= 1_000_000_000_000:
                additional_1tb_ssds += 1
            elif device_is_ssd and device_size < 1_000_000_000_000:
                has_non_boot_ssd_under_1tb = True

    return {
        "additional_1tb_ssds": additional_1tb_ssds,
        "has_non_boot_ssd_under_1tb": has_non_boot_ssd_under_1tb,
        "device_info": device_info,
    }


def categorize_machine(
    boot_disk_info: Dict[str, Any], block_device_info: Dict[str, Any]
) -> str:
    """Categorize what changes are needed for a machine"""
    boot_disk_1tb_ssd = boot_disk_info["is_1tb_ssd"]
    additional_1tb_ssds = block_device_info["additional_1tb_ssds"]
    has_non_boot_ssd_under_1tb = block_device_info["has_non_boot_ssd_under_1tb"]

    has_required_config = boot_disk_1tb_ssd and additional_1tb_ssds >= 1

    if has_required_config:
        return "no_change_needed"
    elif not boot_disk_1tb_ssd and additional_1tb_ssds >= 1:
        return "need_boot_disk_replacement"
    elif boot_disk_1tb_ssd and additional_1tb_ssds == 0:
        if has_non_boot_ssd_under_1tb:
            return "need_second_disk_replacement"
        else:
            return "need_second_disk_addition"
    elif not boot_disk_1tb_ssd and additional_1tb_ssds == 0:
        return "need_both_boot_and_second_disk"


def print_machine_details(
    machine_name: str, boot_disk_info: Dict[str, Any], block_device_info: Dict[str, Any]
) -> None:
    """Print detailed information for a single machine"""
    print(f"\nMachine: {machine_name}")
    print(f"Boot disk: {boot_disk_info['info']}")

    device_info = block_device_info["device_info"]
    print(f"Block devices ({len(device_info)}):")
    for info in device_info:
        print(f"  - {info}")

    additional_1tb_ssds = block_device_info["additional_1tb_ssds"]
    has_required_config = boot_disk_info["is_1tb_ssd"] and additional_1tb_ssds >= 1

    print("\nRequirements check:")
    print(f"  Boot disk is 1TB+ SSD: {'✅' if boot_disk_info['is_1tb_ssd'] else '❌'}")
    print(f"  Additional 1TB+ SSDs: {additional_1tb_ssds} (need ≥1)")
    print(
        f"  Machine meets requirements: {'✅ YES' if has_required_config else '❌ NO'}"
    )
    print("-" * 60)


def print_summary(categories: Dict[str, List[str]]) -> None:
    """Print the summary of changes needed"""
    print("\n" + "=" * 60)
    print("SUMMARY - Changes needed to meet requirements:")
    print("=" * 60)

    if categories["no_change_needed"]:
        print(f"\nNO CHANGES NEEDED ({len(categories['no_change_needed'])} machines):")
        for machine in categories["no_change_needed"]:
            print(f"  - {machine}")

    if categories["need_boot_disk_replacement"]:
        print(
            f"\nREPLACE BOOT DISK with 1TB+ SSD ({len(categories['need_boot_disk_replacement'])} machines):"
        )
        for machine in categories["need_boot_disk_replacement"]:
            print(f"  - {machine}")

    if categories["need_second_disk_replacement"]:
        print(
            f"\nREPLACE SECOND DISK with 1TB+ SSD ({len(categories['need_second_disk_replacement'])} machines):"
        )
        for machine in categories["need_second_disk_replacement"]:
            print(f"  - {machine}")

    if categories["need_second_disk_addition"]:
        print(
            f"\nADD SECOND 1TB+ SSD ({len(categories['need_second_disk_addition'])} machines):"
        )
        for machine in categories["need_second_disk_addition"]:
            print(f"  - {machine}")

    if categories["need_both_boot_and_second_disk"]:
        print(
            f"\nREPLACE BOOT DISK + ADD/REPLACE SECOND DISK ({len(categories['need_both_boot_and_second_disk'])} machines):"
        )
        for machine in categories["need_both_boot_and_second_disk"]:
            print(f"  - {machine}")

    total_machines = sum(len(machines) for machines in categories.values())
    print(f"\nTotal machines: {total_machines}")
    print(f"Machines meeting requirements: {len(categories['no_change_needed'])}")


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query MAAS machines and count results"
    )
    parser.add_argument("profile", help="MAAS profile name (required)")
    parser.add_argument("--tag", help="Filter by tag (optional)")
    parser.add_argument("--hostname", help="Filter by hostname (optional)")

    args = parser.parse_args()

    machines = get_maas_machines(args.profile, args.tag, args.hostname)
    print(f"Number of machines returned: {len(machines)}")

    # Initialize categories
    categories = {
        "no_change_needed": [],
        "need_boot_disk_replacement": [],
        "need_second_disk_replacement": [],
        "need_second_disk_addition": [],
        "need_both_boot_and_second_disk": [],
    }

    # Process each machine
    for machine in machines:
        machine_name = machine.get(
            "hostname", machine.get("fqdn", machine.get("system_id", "unknown"))
        )

        # Analyze machine components
        boot_disk_info = analyze_boot_disk(machine)
        block_device_info = analyze_block_devices(machine, boot_disk_info["id"])

        # Print machine details
        print_machine_details(machine_name, boot_disk_info, block_device_info)

        # Categorize machine
        category = categorize_machine(boot_disk_info, block_device_info)
        categories[category].append(machine_name)

    # Print summary
    print_summary(categories)


if __name__ == "__main__":
    main()
