# Quick Answer: Migrating Multiple HA Pairs to Single Firewall with Multiple VRs

## TL;DR - YES, Absolutely Possible!

You can migrate multiple HA pairs to a single PA-5000 series with separate virtual routers. This is actually a **best practice** for this type of migration.

## ⭐ NEW: Automatic Device Group Splitting!

**Q: Does it automatically split the Panorama config by HA pair?**

**A: YES! Use the included `split_device_groups.py` utility!**

### Super Simple Process

```bash
# 1. Split Panorama export by device group (one per HA pair)
python3 split_device_groups.py panorama_export.xml

# Output:
#   split_configs/DG-Internet.xml  (HA Pair 1)
#   split_configs/DG-DMZ.xml       (HA Pair 2)
#   split_configs/DG-Guest.xml     (HA Pair 3)

# 2. Convert each device group
python3 panorama_to_terraform.py split_configs/DG-Internet.xml --output-dir internet-vr-tf
python3 panorama_to_terraform.py split_configs/DG-DMZ.xml --output-dir dmz-vr-tf
python3 panorama_to_terraform.py split_configs/DG-Guest.xml --output-dir guest-vr-tf

# 3. Customize VR names and deploy
# Done!
```

## How It Works

### Your Scenario
```
Source: 3 HA Pairs in Panorama → Target: Single PA-5450 with 3 Virtual Routers
```

### Automated Process

**Step 1: Export from Panorama (one file)**
```bash
ssh admin@panorama
> set cli config-output-format xml  
> show
# This exports ALL HA pairs in one file
```

**Step 2: Automatic splitting (one file per HA pair)**
```bash
python3 split_device_groups.py panorama_export.xml
```

The splitter automatically:
- Detects all device groups (typically one per HA pair)
- Extracts configuration for each device group
- Includes associated templates (network config)
- Preserves shared objects
- Creates separate XML files

**Step 3: Convert each separately**
```bash
# Now you have individual configs - convert each
python3 panorama_to_terraform.py split_configs/DG-Internet.xml --output-dir internet-vr-tf
# Repeat for each device group
```

## Example Mapping

| Source | Device Group | Target VR | Interfaces |
|--------|-------------|-----------|------------|
| HA Pair 1 | DG-Internet | Internet-VR | ethernet1/1-8 |
| HA Pair 2 | DG-DMZ | DMZ-VR | ethernet1/9-16 |
| HA Pair 3 | DG-Guest | Guest-VR | ethernet1/17-24 |

## What The Converter Does

The converter provides **two tools**:

### Tool 1: Device Group Splitter (`split_device_groups.py`)
✅ Automatically detects all device groups in Panorama export
✅ Splits into separate XML files (one per HA pair/device group)
✅ Includes associated network templates
✅ Preserves shared objects

### Tool 2: Main Converter (`panorama_to_terraform.py`)
✅ Extract complete config from each device group
✅ Generate separate Terraform for each
✅ Capture all routing (BGP, OSPF, static)
✅ Document all interfaces and IPs
✅ Generate VPN configurations

## Workflow

**Original (Manual):**
```bash
# Export each firewall individually - tedious!
ssh admin@ha-pair-1
> show config
ssh admin@ha-pair-2
> show config
ssh admin@ha-pair-3
> show config
```

**New (Automated):**
```bash
# Export once from Panorama
ssh admin@panorama
> show config  # Gets everything

# Split automatically
python3 split_device_groups.py panorama_export.xml
# Creates: DG-Internet.xml, DG-DMZ.xml, DG-Guest.xml

# Convert each
python3 panorama_to_terraform.py split_configs/DG-Internet.xml --output-dir internet-tf
python3 panorama_to_terraform.py split_configs/DG-DMZ.xml --output-dir dmz-tf
python3 panorama_to_terraform.py split_configs/DG-Guest.xml --output-dir guest-tf
```

## What You Need To Do

1. **Export from Panorama** (one command, one file):
   ```bash
   ssh admin@panorama
   > set cli config-output-format xml
   > show
   ```

2. **Run splitter** (automatic device group separation):
   ```bash
   python3 split_device_groups.py panorama_export.xml
   ```

3. **Run converter on each** split config:
   ```bash
   for xml in split_configs/*.xml; do
       base=$(basename "$xml" .xml)
       python3 panorama_to_terraform.py "$xml" --output-dir "${base}-tf"
   done
   ```

2. **Customize virtual router names** in each output:
   ```hcl
   # Change from:
   resource "panos_virtual_router" "default" {
     name = "default"
   
   # To:
   resource "panos_virtual_router" "internet_vr" {
     name = "Internet-VR"
   ```

3. **Update interface assignments** for target platform:
   ```hcl
   # HA Pair 1: Use ethernet1/1-8 on PA-5450
   # HA Pair 2: Use ethernet1/9-16 on PA-5450
   # HA Pair 3: Use ethernet1/17-24 on PA-5450
   ```

4. **Merge and deploy**:
   ```bash
   # Option A: Use separate Terraform modules
   # Option B: Merge into single directory
   terraform apply
   ```

## Benefits of Multi-VR Architecture

✅ **Traffic Isolation** - Each function in separate routing table
✅ **Security Segmentation** - Independent policy enforcement  
✅ **Operational Separation** - Different teams manage different VRs
✅ **Protocol Isolation** - BGP in one VR, OSPF in another
✅ **Resource Optimization** - Single large platform vs. multiple small ones
✅ **Cost Savings** - One PA-5450 vs. three HA pairs

## VR-to-VR Communication

If your VRs need to talk to each other:

```hcl
# Static route from Internet-VR to DMZ networks
resource "panos_static_route_ipv4" "internet_to_dmz" {
  virtual_router = "Internet-VR"
  destination = "172.16.0.0/16"
  type = "next-vr"
  next_vr = "DMZ-VR"
}
```

## Complete Documentation

See **MULTI_VR_MIGRATION_GUIDE.md** for:
- Detailed step-by-step process
- Interface mapping strategies
- VR interconnection patterns
- Security policy considerations
- Lab testing procedures
- Troubleshooting guide
- Real-world examples

## Key Point

The converter extracts everything you need. You just need to:
1. Run it separately on each HA pair config
2. Customize the VR names
3. Map interfaces to different port ranges
4. Deploy to your PA-5450

**This is a well-supported migration pattern!**
