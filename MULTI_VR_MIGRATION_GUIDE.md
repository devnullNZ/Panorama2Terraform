# Multi-HA-Pair to Multi-Virtual-Router Migration Guide

## Overview

This guide addresses a common enterprise migration scenario: migrating multiple HA pairs managed by Panorama to a single larger firewall (e.g., PA-5000 series) with separate virtual routers for traffic isolation.

## Migration Scenario

### Current State (Source)
```
Panorama
    ├── HA Pair 1 (PA-3020) - Internet Edge
    │   ├── VR: default
    │   ├── BGP to ISPs
    │   └── Interfaces: ethernet1/1-4
    │
    ├── HA Pair 2 (PA-3020) - DMZ
    │   ├── VR: default
    │   ├── OSPF internal
    │   └── Interfaces: ethernet1/1-4
    │
    └── HA Pair 3 (PA-3020) - Guest Network
        ├── VR: default
        ├── Static routes
        └── Interfaces: ethernet1/1-4
```

### Target State (After Migration)
```
Single PA-5450
    ├── VR: Internet-VR
    │   ├── BGP to ISPs (from HA Pair 1)
    │   ├── Interfaces: ethernet1/1-8
    │   └── Zones: Untrust, WAN
    │
    ├── VR: DMZ-VR
    │   ├── OSPF internal (from HA Pair 2)
    │   ├── Interfaces: ethernet1/9-16
    │   └── Zones: DMZ, Internal-DMZ
    │
    ├── VR: Guest-VR
    │   ├── Static routes (from HA Pair 3)
    │   ├── Interfaces: ethernet1/17-20
    │   └── Zones: Guest, Guest-Services
    │
    └── VR: Management-VR
        ├── Management traffic
        └── Interfaces: ethernet1/21
```

## Why Multi-VR Architecture?

### Benefits
1. **Traffic Isolation** - Separate routing tables per function
2. **Security Segmentation** - Independent policy enforcement
3. **Operational Flexibility** - Different teams can manage different VRs
4. **Routing Protocol Isolation** - BGP, OSPF in separate instances
5. **Simplified Troubleshooting** - Isolated routing domains
6. **Resource Optimization** - Better utilize single large platform

### Use Cases
- **Service Provider Edge** - Customer VRFs
- **Enterprise Campus** - Department isolation
- **Managed Security Services** - Customer separation
- **Data Center** - Application tier isolation
- **Cloud On-Ramps** - Per-cloud routing domains

## Migration Strategy

### Phase 1: Export and Analyze

#### Step 1: Export Each HA Pair Configuration
```bash
# For each HA pair, export configuration
ssh admin@ha-pair-1
> set cli config-output-format xml
> configure
# show
> save config to ha-pair-1-export.xml

# Repeat for each HA pair
scp admin@ha-pair-1:ha-pair-1-export.xml ./
scp admin@ha-pair-2:ha-pair-2-export.xml ./
scp admin@ha-pair-3:ha-pair-3-export.xml ./
```

#### Step 2: Run Converter on Each Configuration
```bash
# Convert each HA pair separately
python3 panorama_to_terraform.py ha-pair-1-export.xml --output-dir ha-pair-1-tf
python3 panorama_to_terraform.py ha-pair-2-export.xml --output-dir ha-pair-2-tf
python3 panorama_to_terraform.py ha-pair-3-export.xml --output-dir ha-pair-3-tf
```

#### Step 3: Review Interface Reports
```bash
# Review interface assignments for each
cat ha-pair-1-tf/INTERFACE_MIGRATION_REPORT.txt
cat ha-pair-2-tf/INTERFACE_MIGRATION_REPORT.txt
cat ha-pair-3-tf/INTERFACE_MIGRATION_REPORT.txt
```

### Phase 2: Design Virtual Router Architecture

#### Create VR Mapping Document

| Source HA Pair | Source VR | Interfaces | → | Target VR | Target Interfaces | Notes |
|----------------|-----------|------------|---|-----------|-------------------|-------|
| HA Pair 1 | default | eth1/1-4 | → | Internet-VR | eth1/1-8 | More capacity |
| HA Pair 2 | default | eth1/1-4 | → | DMZ-VR | eth1/9-16 | Isolated DMZ |
| HA Pair 3 | default | eth1/1-4 | → | Guest-VR | eth1/17-20 | Guest isolation |

#### Document VR Inter-connectivity

If VRs need to communicate:
```
Internet-VR <--[VR Route]--> DMZ-VR
DMZ-VR <--[VR Route]--> Guest-VR
```

### Phase 3: Customize Terraform Configurations

#### Step 1: Rename Virtual Routers

**ha-pair-1-tf/virtual_routers.tf:**
```hcl
# BEFORE (generated)
resource "panos_virtual_router" "default" {
  name = "default"
  interfaces = ["ethernet1/1", "ethernet1/2", "ethernet1/3", "ethernet1/4"]
}

# AFTER (customized for target)
resource "panos_virtual_router" "internet_vr" {
  name = "Internet-VR"
  interfaces = [
    "ethernet1/1",  # WAN1 
    "ethernet1/2",  # WAN2
    "ethernet1/3",  # Backup WAN
    "ethernet1/4",  # MPLS
    "ethernet1/5",  # Reserved
    "ethernet1/6",  # Reserved
    "ethernet1/7",  # Reserved
    "ethernet1/8"   # Reserved
  ]
}
```

**ha-pair-2-tf/virtual_routers.tf:**
```hcl
# AFTER (customized for target)
resource "panos_virtual_router" "dmz_vr" {
  name = "DMZ-VR"
  interfaces = [
    "ethernet1/9",   # DMZ Subnet 1
    "ethernet1/10",  # DMZ Subnet 2
    "ethernet1/11",  # Internal DMZ
    "ethernet1/12",  # App DMZ
    # ... interfaces 13-16 for growth
  ]
}
```

**ha-pair-3-tf/virtual_routers.tf:**
```hcl
# AFTER (customized for target)
resource "panos_virtual_router" "guest_vr" {
  name = "Guest-VR"
  interfaces = [
    "ethernet1/17",  # Guest WiFi
    "ethernet1/18",  # Guest Services
    "ethernet1/19",  # Contractor Network
    "ethernet1/20"   # Reserved
  ]
}
```

#### Step 2: Update Interface Configurations

Update each interface configuration file to match target platform:

**ha-pair-1-tf/interfaces.tf:**
```hcl
resource "panos_ethernet_interface" "wan1" {
  name = "ethernet1/1"  # Target PA-5450 interface
  mode = "layer3"
  static_ips = ["203.0.113.1/30"]  # Same IP from source
  comment = "WAN1 - ISP A (from HA Pair 1 eth1/1)"
}

resource "panos_ethernet_interface" "wan2" {
  name = "ethernet1/2"  # Target PA-5450 interface
  mode = "layer3"
  static_ips = ["198.51.100.1/30"]  # Same IP from source
  comment = "WAN2 - ISP B (from HA Pair 1 eth1/2)"
}
```

#### Step 3: Update Zone Configurations

**ha-pair-1-tf/zones.tf:**
```hcl
resource "panos_zone" "untrust" {
  name = "Untrust"
  mode = "layer3"
  interfaces = ["ethernet1/1", "ethernet1/2"]  # Updated for target
}

# Must explicitly set VR for zones
resource "panos_zone" "wan" {
  name = "WAN"
  mode = "layer3"
  interfaces = ["ethernet1/3", "ethernet1/4"]
}
```

#### Step 4: Update BGP/OSPF Configurations

**ha-pair-1-tf/bgp.tf:**
```hcl
resource "panos_bgp" "internet_vr_bgp" {
  virtual_router = panos_virtual_router.internet_vr.name  # Updated VR reference
  enable = true
  router_id = "1.1.1.1"
  as_number = "65001"
}

resource "panos_bgp_peer" "isp_a" {
  virtual_router = panos_virtual_router.internet_vr.name
  bgp_peer_group = "ISP-Peers"
  name = "ISP-A"
  peer_as = "65000"
  local_address_interface = "ethernet1/1"  # Updated interface
  peer_address_ip = "203.0.113.2"
}
```

**ha-pair-2-tf/ospf.tf:**
```hcl
resource "panos_ospf" "dmz_vr_ospf" {
  virtual_router = panos_virtual_router.dmz_vr.name  # Updated VR reference
  enable = true
  router_id = "2.2.2.2"  # Different router ID
}
```

### Phase 4: Configure VR Inter-connectivity

If virtual routers need to communicate, configure VR-to-VR routes:

```hcl
# In Internet-VR: Route to DMZ networks via DMZ-VR
resource "panos_static_route_ipv4" "internet_to_dmz" {
  virtual_router = panos_virtual_router.internet_vr.name
  name = "To-DMZ-Networks"
  destination = "172.16.0.0/16"
  type = "next-vr"
  next_vr = "DMZ-VR"
}

# In DMZ-VR: Default route to Internet-VR
resource "panos_static_route_ipv4" "dmz_default" {
  virtual_router = panos_virtual_router.dmz_vr.name
  name = "Default-via-Internet-VR"
  destination = "0.0.0.0/0"
  type = "next-vr"
  next_vr = "Internet-VR"
}

# In Guest-VR: Route via DMZ-VR to internal resources
resource "panos_static_route_ipv4" "guest_to_internal" {
  virtual_router = panos_virtual_router.guest_vr.name
  name = "To-Internal"
  destination = "10.0.0.0/8"
  type = "next-vr"
  next_vr = "DMZ-VR"
}
```

### Phase 5: Merge Terraform Configurations

#### Option A: Separate Terraform Modules (Recommended)
```
terraform/
├── modules/
│   ├── internet-vr/
│   │   ├── main.tf (from ha-pair-1-tf)
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── dmz-vr/
│   │   ├── main.tf (from ha-pair-2-tf)
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── guest-vr/
│       ├── main.tf (from ha-pair-3-tf)
│       ├── variables.tf
│       └── outputs.tf
├── main.tf
└── terraform.tfvars
```

**main.tf:**
```hcl
module "internet_vr" {
  source = "./modules/internet-vr"
  
  panos_hostname = var.panos_hostname
  # Other variables
}

module "dmz_vr" {
  source = "./modules/dmz-vr"
  
  panos_hostname = var.panos_hostname
  depends_on = [module.internet_vr]
}

module "guest_vr" {
  source = "./modules/guest-vr"
  
  panos_hostname = var.panos_hostname
  depends_on = [module.dmz_vr]
}
```

#### Option B: Single Configuration Directory
Merge all .tf files into one directory:
```bash
mkdir merged-config
cp ha-pair-1-tf/*.tf merged-config/
cp ha-pair-2-tf/*.tf merged-config/
cp ha-pair-3-tf/*.tf merged-config/

# Rename to avoid conflicts
cd merged-config
mv virtual_routers.tf vr-internet.tf
mv ../ha-pair-2-tf/virtual_routers.tf vr-dmz.tf
mv ../ha-pair-3-tf/virtual_routers.tf vr-guest.tf
```

### Phase 6: Testing Strategy

#### Lab Testing Sequence

1. **Deploy Internet VR First**
   ```bash
   terraform apply -target=module.internet_vr
   ```
   - Verify BGP peers establish
   - Test external connectivity
   - Validate routing table

2. **Deploy DMZ VR**
   ```bash
   terraform apply -target=module.dmz_vr
   ```
   - Verify OSPF neighbors
   - Test VR-to-VR routing
   - Validate DMZ access

3. **Deploy Guest VR**
   ```bash
   terraform apply -target=module.guest_vr
   ```
   - Test guest isolation
   - Verify limited internal access
   - Validate internet access

4. **Full Integration Test**
   ```bash
   terraform apply
   ```
   - Test all VR inter-connectivity
   - Verify policy enforcement
   - Validate end-to-end flows

## Interface Mapping Strategy

### PA-3000 Series to PA-5000 Series

| Source Model | Interfaces | Target Model | Target Interfaces | Notes |
|--------------|------------|--------------|-------------------|-------|
| PA-3020 | 8x 1GbE | PA-5450 | 16x 25GbE + extras | Massive capacity increase |
| 3x HA Pairs | 24 ports total | Single device | 40+ ports available | Room for growth |

### Best Practices

1. **Group by Function**
   - Interfaces 1-8: External/Internet
   - Interfaces 9-16: DMZ/Services
   - Interfaces 17-24: Internal/Guest
   - Interfaces 25+: Reserved/Future

2. **Document Everything**
   - Create detailed mapping spreadsheet
   - Note cable colors/labeling
   - Document switch port mappings
   - Update network diagrams

3. **Maintain IP Addresses**
   - Keep same IPs where possible
   - Reduces DNS/routing changes
   - Minimizes application impact

## Security Considerations

### Policy Isolation

Each VR should have separate security policies:

```hcl
# Internet-VR policies
resource "panos_security_rule_group" "internet_vr_outbound" {
  position_keyword = "bottom"
  
  rule {
    name = "Internet-Outbound"
    source_zones = ["WAN"]
    destination_zones = ["Untrust"]
    # ... Internet-specific policies
  }
}

# DMZ-VR policies  
resource "panos_security_rule_group" "dmz_vr_policies" {
  position_keyword = "bottom"
  
  rule {
    name = "DMZ-to-Internal"
    source_zones = ["DMZ"]
    destination_zones = ["Internal-DMZ"]
    # ... DMZ-specific policies
  }
}
```

### VR-to-VR Traffic Control

Control inter-VR traffic with policies:

```hcl
resource "panos_security_rule_group" "vr_to_vr" {
  position_keyword = "top"  # Higher priority
  
  rule {
    name = "Guest-to-Internet-Only"
    source_zones = ["Guest"]
    destination_zones = ["Untrust"]
    action = "allow"
  }
  
  rule {
    name = "Block-Guest-to-Internal"
    source_zones = ["Guest"]
    destination_zones = ["DMZ", "Internal"]
    action = "deny"
    log_end = true
  }
}
```

## Migration Checklist

### Pre-Migration
- [ ] Export configs from all HA pairs
- [ ] Run converter on each export
- [ ] Create VR architecture design
- [ ] Create interface mapping document
- [ ] Create IP address mapping document
- [ ] Design VR inter-connectivity
- [ ] Update all Terraform files
- [ ] Merge configurations (modules or single dir)
- [ ] Review security policies for each VR
- [ ] Plan VR-to-VR policy enforcement
- [ ] Test in lab environment

### During Migration
- [ ] Apply Internet VR configuration
- [ ] Verify external connectivity
- [ ] Apply DMZ VR configuration
- [ ] Test VR-to-VR routing
- [ ] Apply Guest VR configuration
- [ ] Verify all VR routing
- [ ] Test inter-VR policies
- [ ] Validate end-to-end connectivity

### Post-Migration
- [ ] Monitor all BGP/OSPF sessions
- [ ] Verify routing tables in each VR
- [ ] Test application connectivity
- [ ] Review security policy hits
- [ ] Update documentation
- [ ] Update monitoring systems
- [ ] Decommission old HA pairs

## Troubleshooting

### VR Routing Issues

**Problem**: Routes not appearing in VR
```bash
# Check VR configuration
show routing virtual-router Internet-VR

# Verify interface membership
show network virtual-router Internet-VR

# Check routing protocol status
show routing protocol bgp summary virtual-router Internet-VR
```

**Solution**: Verify interfaces are assigned to correct VR in Terraform

### Inter-VR Routing Not Working

**Problem**: Cannot route between VRs
```bash
# Check VR-to-VR routes
show routing route virtual-router Internet-VR

# Verify next-vr configuration
show network virtual-router all
```

**Solution**: Add static routes with `type = "next-vr"`

### Policy Not Matching

**Problem**: Traffic not hitting correct policies
```bash
# Check policy match
test security-policy-match from Internet to DMZ

# Monitor traffic logs
tail -f /var/log/pan/traffic.log
```

**Solution**: Ensure zones are in correct VR

## Advanced Scenarios

### Scenario 1: BGP in Multiple VRs

If multiple VRs run BGP (e.g., different ISPs per VR):

```hcl
# Internet-VR: Primary BGP
resource "panos_bgp" "internet_bgp" {
  virtual_router = "Internet-VR"
  as_number = "65001"
  router_id = "1.1.1.1"
}

# Backup-VR: Backup BGP
resource "panos_bgp" "backup_bgp" {
  virtual_router = "Backup-VR"
  as_number = "65001"  # Same AS
  router_id = "1.1.1.2"  # Different router ID
}
```

### Scenario 2: OSPF Redistribution Between VRs

Not directly supported - use static routes or policy-based forwarding

### Scenario 3: Multi-Tenancy

Each customer/department gets own VR:
```
PA-5450
├── VR: Customer-A-VR
├── VR: Customer-B-VR
└── VR: Customer-C-VR
```

## Conclusion

Migrating multiple HA pairs to a single large firewall with separate virtual routers:
- Improves security through isolation
- Simplifies management (single device)
- Reduces hardware costs
- Provides better resource utilization
- Enables clearer operational ownership

The converter script extracts all necessary configuration from each HA pair. You customize the virtual router names and interface mappings to match your target architecture.

**Key Success Factor**: Detailed planning and documentation of the VR architecture before starting the migration!
