# Hardware Upgrade Analysis Scripts

This repository contains Python scripts to analyze MAAS machines and determine hardware upgrade requirements for disk storage and network interfaces.

## Scripts

### 1. generate_disk_replacement_summary.py

Analyzes machine disk configurations to determine what storage upgrades are needed to meet requirements.

**Requirements checked:**

- Boot disk must be a 1TB+ SSD
- Machine must have at least one additional 1TB+ SSD

**Usage:**

```bash
./generate_disk_replacement_summary.py <profile> [--tag TAG] [--hostname HOSTNAME]
```

**Arguments:**

- `profile`: MAAS profile name (required)
- `--tag`: Filter by tag (optional)
- `--hostname`: Filter by specific hostname (optional)

**Output categories:**

- **No changes needed**: Machines already meeting requirements
- **Replace boot disk**: Need to upgrade boot disk to 1TB+ SSD
- **Replace second disk**: Need to upgrade existing second disk to 1TB+ SSD
- **Add second disk**: Need to add a second 1TB+ SSD
- **Replace boot + add/replace second**: Need both boot disk upgrade and second disk

### 2. generate_nic_summary.py

Analyzes network interface configurations to determine if machines have sufficient connected NICs.

**Requirements checked:**

- Machine must have at least three connected network interfaces (excludes VLAN interfaces)

**Usage:**

```bash
./generate_nic_summary.py <profile> [--tag TAG] [--hostname HOSTNAME]
```

**Arguments:**

- `profile`: MAAS profile name (required)
- `--tag`: Filter by tag (optional)
- `--hostname`: Filter by specific hostname (optional)

**Output categories:**

- **Machines meeting requirements**: ≥3 connected NICs
- **Machines not meeting requirements**: <3 connected NICs

## Prerequisites

- Python 3.6+
- MAAS CLI configured with appropriate profile
- Access to MAAS via CLI

## Examples

```bash
# Analyze all machines for disk requirements
./generate_disk_replacement_summary.py my-maas-profile

# Check specific tagged machines for NIC requirements
./generate_nic_summary.py my-maas-profile --tag rack_xyz

# Analyze a specific machine
./generate_disk_replacement_summary.py my-maas-profile --hostname server-01
```
