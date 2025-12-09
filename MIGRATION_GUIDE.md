# Palo Alto Firewall Migration Guide

## Overview

This guide provides step-by-step instructions for migrating Palo Alto firewalls to different platforms using the Panorama to Terraform converter. This tool is specifically designed to facilitate migrations between different Palo Alto hardware platforms (e.g., PA-3000 to PA-5000, physical to VM-Series).

## Migration Workflow

```
┌─────────────────────────┐
│  Source Firewall/       │
│  Panorama Export        │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Export Configuration   │
│  (XML Format)           │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Run Converter Script   │
│  panorama_to_terraform  │
└───────────┬─────────────┘
            │
            ├─────────────────────────────┐
            │                             │
            ▼                             ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│  Terraform Files        │   │  Interface Report       │
│  (.tf configs)          │   │  (Migration planning)   │
└───────────┬─────────────┘   └─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│  Review & Adjust        │
│  - Interface mapping    │
│  - Platform differences │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Apply to Target        │
│  Firewall/Panorama      │
└─────────────────────────┘
```

## What Gets Converted

### ✅ Fully Converted (Ready to Apply)
- **Address Objects** - IP addresses, FQDNs, IP ranges
- **Address Groups** - Static and dynamic groups
- **Service Objects** - TCP/UDP services
- **Service Groups** - Service collections
- **Security Rules** - Policy rules with actions, logging
- **NAT Rules** - Source and destination NAT
- **Zones** - Security zones and interface assignments
- **Virtual Routers** - Routing configuration and static routes
- **Security Profile Groups** - Profile group assignments

### ⚠️ Requires Manual Configuration
- **Interfaces** - Generated as reference; must be adjusted for target platform
- **Security Profiles** - Listed but full rules need manual configuration
- **Management Profiles** - Referenced but not fully configured
- **High Availability** - Not included in export
- **VPN Configurations** - Not supported
- **GlobalProtect** - Not supported

## Pre-Migration Steps

### 1. Document Current Environment

Create an inventory of your current setup:

```bash
# From source firewall CLI
show system info
show interface all
show zone all
show routing route
show session meter
```

Save this information for reference during migration.

### 2. Export Configuration from Source

#### Option A: Via Panorama Web UI
1. Log into Panorama
2. Navigate to Panorama → Setup → Operations
3. Click "Save named Panorama configuration snapshot"
4. Download the configuration
5. Extract the XML file

#### Option B: Via Firewall CLI
```bash
ssh admin@firewall
> set cli config-output-format xml
> configure
# show
> save config to export.xml
```

Then download via SCP:
```bash
scp admin@firewall:export.xml ./source-config.xml
```

#### Option C: Via API
```bash
curl -k -X GET \
  'https://firewall/api/?type=export&category=configuration&key=YOUR_API_KEY' \
  -o source-config.xml
```

### 3. Run the Converter

```bash
python3 panorama_to_terraform.py source-config.xml --output-dir migration_configs
```

### 4. Review the Interface Migration Report

The script generates `INTERFACE_MIGRATION_REPORT.txt` which contains:
- All interface names and IP addresses
- Interface types (Layer2, Layer3, VLAN, Loopback)
- Management profiles
- VLAN tags
- Platform-specific guidance

**Example Report Structure:**
```
Interface: ethernet1/1
  Type: ethernet
  Mode: layer3
  Comment: Trust Interface - Internal Network
  IPv4 Addresses:
    - 10.1.1.1/24
  IPv6 Addresses:
    - 2001:db8::1/64
  Management Profile: Ping-Only
```

## Platform-Specific Migration Notes

### PA-200/500 → PA-800/850
- Interface naming remains consistent
- Check for throughput/session limits
- Verify transceiver compatibility

### PA-3000 Series → PA-5000 Series
- Interface slot numbering may differ
- More interfaces available on target
- Enhanced performance capabilities

### Physical → VM-Series
- Interface naming is configurable
- Plan virtual NIC allocation
- License differences (throughput-based)
- No hardware bypass

### VM-Series → Physical
- Map virtual interfaces to physical ports
- Consider hardware bypass capabilities
- Plan for management interface differences

## Interface Mapping Strategy

### Step 1: Create Interface Mapping Table

Create a mapping document like this:

| Source Interface | Source IP       | Zone    | → | Target Interface | Target IP       | Notes               |
|------------------|-----------------|---------|---|------------------|-----------------|---------------------|
| ethernet1/1      | 10.1.1.1/24     | Trust   | → | ethernet1/1      | 10.1.1.1/24     | Direct mapping      |
| ethernet1/2      | 203.0.113.1/30  | Untrust | → | ethernet1/2      | 203.0.113.1/30  | Direct mapping      |
| ethernet1/3      | 172.16.1.1/24   | DMZ     | → | ethernet1/5      | 172.16.1.1/24   | Different port      |
| vlan.10          | 192.168.10.1/24 | Mgmt    | → | vlan.10          | 192.168.10.1/24 | Same VLAN           |

### Step 2: Update Terraform Configurations

Edit `interfaces.tf` to match your target platform:

```hcl
# Before (from converter)
resource "panos_ethernet_interface" "ethernet1_1" {
  name = "ethernet1/1"
  mode = "layer3"
  static_ips = ["10.1.1.1/24"]
}

# After (adjusted for target)
resource "panos_ethernet_interface" "ethernet1_1" {
  name = "ethernet1/1"  # Verify this matches target platform
  mode = "layer3"
  static_ips = ["10.1.1.1/24"]
  management_profile = "Allow-Ping"
  comment = "Trust Interface - Internal Network"
}
```

### Step 3: Update Zone Assignments

Ensure zones reference the correct interfaces:

```hcl
resource "panos_zone" "trust" {
  name = "Trust"
  mode = "layer3"
  interfaces = ["ethernet1/1", "vlan.10"]  # Verify these exist on target
}
```

## Detailed Migration Steps

### Phase 1: Preparation (Day 1-2)

1. **Backup Everything**
   ```bash
   # From firewall
   request system backup
   
   # Download backup
   scp admin@firewall:/opt/pancfg/mgmt/saved-configs/backup.tgz ./
   ```

2. **Run Converter**
   ```bash
   python3 panorama_to_terraform.py source-config.xml --output-dir terraform_migration
   ```

3. **Review Generated Files**
   - Check `INTERFACE_MIGRATION_REPORT.txt`
   - Review all `.tf` files
   - Note any manual adjustments needed

4. **Create Interface Mapping Table**
   - Document source-to-target interface mappings
   - Note any IP address changes
   - Identify zone assignments

### Phase 2: Configuration Adjustment (Day 3-5)

1. **Adjust Interface Configurations**
   - Edit `interfaces.tf` for target platform
   - Update interface names if needed
   - Verify management profiles

2. **Update Zone Configurations**
   - Edit `zones.tf` to match new interfaces
   - Verify zone protection profiles exist

3. **Review Virtual Router**
   - Edit `virtual_routers.tf`
   - Update interface memberships
   - Verify static routes

4. **Test Configuration Syntax**
   ```bash
   cd terraform_migration
   terraform init
   terraform validate
   ```

### Phase 3: Lab Testing (Day 6-8)

1. **Set Up Lab Environment**
   - Deploy target firewall in lab
   - Configure basic connectivity
   - Prepare test clients

2. **Apply Base Configuration**
   ```bash
   terraform plan -out=migration.plan
   terraform apply migration.plan
   ```

3. **Test Core Functions**
   - Verify interface connectivity
   - Test zone-to-zone traffic
   - Validate NAT functionality
   - Check security policies

4. **Document Issues**
   - Note any errors or warnings
   - Document workarounds
   - Update Terraform configs as needed

### Phase 4: Production Cutover (Day 9-10)

1. **Schedule Maintenance Window**
   - Notify stakeholders
   - Plan rollback procedures
   - Prepare backup configurations

2. **Pre-Cutover Checklist**
   - [ ] Backup source firewall
   - [ ] Backup target firewall
   - [ ] Test lab environment
   - [ ] Verify Terraform configs
   - [ ] Prepare rollback plan
   - [ ] Document current routing
   - [ ] Save current sessions

3. **Cutover Procedure**
   ```bash
   # 1. Apply configuration to target
   terraform apply
   
   # 2. Verify critical services
   show interface all
   show zone all
   show routing route
   
   # 3. Test connectivity
   ping source 10.1.1.1 host 8.8.8.8
   
   # 4. Monitor sessions
   show session meter
   ```

4. **Post-Cutover Validation**
   - Test critical applications
   - Verify logging
   - Check security policies
   - Monitor performance
   - Validate redundancy

### Phase 5: Post-Migration (Day 11+)

1. **Monitoring**
   - Watch logs for anomalies
   - Monitor traffic patterns
   - Check for policy hits
   - Review threat logs

2. **Optimization**
   - Tune policies as needed
   - Adjust logging levels
   - Optimize performance
   - Update documentation

3. **Decommission Source**
   - Archive configuration
   - Remove from monitoring
   - Update network diagrams
   - Update asset inventory

## Troubleshooting Common Issues

### Issue: Interface Names Don't Match

**Symptom:** Terraform fails with "interface not found"

**Solution:**
1. Check target platform's interface naming
2. Update `interfaces.tf` with correct names
3. Update zone assignments in `zones.tf`
4. Update virtual router in `virtual_routers.tf`

```bash
# Verify available interfaces on target
show interface all
```

### Issue: Zone Assignment Fails

**Symptom:** Zone creation fails or interface not assigned

**Solution:**
1. Ensure interfaces exist before creating zones
2. Use Terraform depends_on if needed:
```hcl
resource "panos_zone" "trust" {
  name = "Trust"
  interfaces = ["ethernet1/1"]
  
  depends_on = [
    panos_ethernet_interface.ethernet1_1
  ]
}
```

### Issue: Security Profiles Not Found

**Symptom:** Security rules reference non-existent profiles

**Solution:**
1. Create profiles manually or import existing ones
2. Update profile references in security rules
3. Consider using default profiles initially

### Issue: Virtual Router Interface Membership

**Symptom:** Interfaces not routing properly

**Solution:**
1. Verify all interfaces in virtual router exist
2. Check for typos in interface names
3. Ensure interfaces are Layer3 mode

### Issue: NAT Rules Not Working

**Symptom:** NAT translations not occurring

**Solution:**
1. Verify zone-to-zone policies allow traffic
2. Check NAT rule ordering
3. Confirm interface IPs are correct
4. Review NAT logs

## Best Practices

### Do's ✅
- Always test in lab first
- Document all changes
- Keep source config as backup
- Use version control for Terraform files
- Monitor logs post-migration
- Plan rollback procedures
- Test incrementally
- Verify before and after migration

### Don'ts ❌
- Don't skip lab testing
- Don't assume interface names match
- Don't forget to backup
- Don't rush the cutover
- Don't ignore warnings
- Don't forget zone assignments
- Don't overlook management profiles

## Rollback Procedures

### Quick Rollback (If detected within 1 hour)
1. Restore source firewall to active
2. Update routing to point to source
3. Verify connectivity
4. Investigate issues

### Configuration Rollback (If Terraform applied)
```bash
# Destroy Terraform-managed resources
terraform destroy

# Restore from backup
load config from backup.xml
commit
```

### Full Rollback (If major issues)
1. Power off target firewall
2. Restore source firewall
3. Verify all services
4. Schedule new migration window

## Migration Checklist Template

```
PRE-MIGRATION
[ ] Export source configuration
[ ] Run converter script
[ ] Review generated files
[ ] Create interface mapping table
[ ] Adjust Terraform configs
[ ] Test in lab environment
[ ] Document test results
[ ] Prepare rollback plan
[ ] Schedule maintenance window
[ ] Notify stakeholders

MIGRATION DAY
[ ] Backup source firewall
[ ] Backup target firewall
[ ] Verify Terraform configs
[ ] Run terraform plan
[ ] Review plan output
[ ] Run terraform apply
[ ] Verify interfaces
[ ] Verify zones
[ ] Verify routing
[ ] Test connectivity
[ ] Verify NAT
[ ] Test security policies
[ ] Monitor logs
[ ] Document issues

POST-MIGRATION
[ ] Monitor for 24 hours
[ ] Review all logs
[ ] Test all applications
[ ] Update documentation
[ ] Update monitoring
[ ] Archive source config
[ ] Schedule decommission
[ ] Conduct lessons learned
```

## Additional Resources

- **Interface Report**: `INTERFACE_MIGRATION_REPORT.txt` - Detailed interface inventory
- **Terraform Docs**: https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs
- **PAN-OS API**: https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api
- **Migration Guide**: This document

## Support

For issues with the converter script:
1. Review the generated files
2. Check Terraform validation output
3. Consult the Terraform provider documentation
4. Test in lab environment first

For firewall-specific issues:
1. Consult Palo Alto support
2. Review PAN-OS documentation
3. Check compatibility matrix
4. Verify platform-specific features

---

**Remember**: This is a complex migration. Always test thoroughly in a lab environment before attempting production cutover. Good luck!
