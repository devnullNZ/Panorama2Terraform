# Palo Alto Panorama to Terraform Converter

## Overview

This tool converts Palo Alto Panorama XML configuration exports into Terraform configuration files. It's designed to help migrate Palo Alto firewall configurations to infrastructure-as-code, making it easier to manage, version control, and deploy replacement devices.

## Features

### Supported Configuration Elements

- **Address Objects** (IP netmask, IP range, FQDN)
- **Address Groups** (static and dynamic)
- **Service Objects** (TCP/UDP ports)
- **Service Groups**
- **Security Policy Rules**
- **NAT Policy Rules**
- **Device Groups**

### Key Capabilities

- Parses standard Panorama XML export format
- Handles both device group and shared configurations
- Generates clean, readable Terraform code
- Includes proper resource dependencies
- Preserves descriptions, tags, and metadata
- Automatic deduplication of resources
- Sanitizes names for Terraform compatibility

## Requirements

- Python 3.6 or higher
- Terraform 1.0 or higher
- Access to Palo Alto Panorama or firewall

## Installation

No installation required - just download the script:

```bash
# Make the script executable
chmod +x panorama_to_terraform.py
```

## Exporting Configuration from Panorama

### Method 1: Via Web UI

1. Log in to Panorama web interface
2. Navigate to **Device** → **Setup** → **Operations**
3. Click **Save named Panorama configuration snapshot**
4. Download the configuration file
5. Extract the XML from the archive

### Method 2: Via CLI

```bash
# SSH into Panorama
ssh admin@panorama-hostname

# Export configuration
> set cli config-output-format xml
> configure
# show
> save config to <filename>.xml

# Download the file using SCP
scp admin@panorama-hostname:<filename>.xml ./
```

### Method 3: API Export

```bash
# Using curl
curl -k -X GET 'https://panorama-hostname/api/?type=export&category=configuration&key=YOUR_API_KEY' -o config.xml
```

## Usage

### Basic Usage

```bash
python3 panorama_to_terraform.py <input_file.xml>
```

This will create a `terraform_output` directory with all Terraform files.

### Custom Output Directory

```bash
python3 panorama_to_terraform.py <input_file.xml> --output-dir /path/to/output
```

### Example

```bash
python3 panorama_to_terraform.py panorama_config.xml --output-dir ./terraform/palo_alto
```

## Output Structure

The script generates the following Terraform files:

```
terraform_output/
├── provider.tf           # Provider configuration
├── variables.tf          # Variable definitions
├── address_objects.tf    # Address object resources
├── address_groups.tf     # Address group resources
├── service_objects.tf    # Service object resources
├── service_groups.tf     # Service group resources
├── security_rules.tf     # Security policy rules
├── nat_rules.tf         # NAT policy rules
└── README.md            # Deployment instructions
```

## Terraform Deployment

### Step 1: Configure Authentication

Create a `terraform.tfvars` file:

```hcl
panos_hostname = "panorama.example.com"
panos_username = "admin"
panos_password = "your-secure-password"
device_group   = "Production-DG"
```

Or use environment variables:

```bash
export PANOS_HOSTNAME="panorama.example.com"
export PANOS_USERNAME="admin"
export PANOS_PASSWORD="your-secure-password"
```

### Step 2: Initialize Terraform

```bash
cd terraform_output
terraform init
```

### Step 3: Review the Plan

```bash
terraform plan
```

Review the output carefully to ensure all resources are correct.

### Step 4: Apply Configuration

```bash
# Dry run first
terraform plan -out=tfplan

# Apply the plan
terraform apply tfplan
```

## Advanced Usage

### Filtering Specific Device Groups

Edit the generated files to include only specific device groups by modifying the `device_group` variable or adding conditional logic.

### Customizing Resource Names

The script automatically sanitizes resource names, but you can modify the `sanitize_name()` function in the script to customize naming conventions.

### Handling Large Configurations

For very large configurations (1000+ rules), consider splitting the output:

```python
# Modify the script to generate separate files per device group
# or split rules into multiple files
```

## Troubleshooting

### Common Issues

**Issue**: "ParseError: not well-formed"
- **Solution**: Ensure the XML file is valid and complete. Try re-exporting from Panorama.

**Issue**: Duplicate resource names in Terraform
- **Solution**: The script automatically handles duplicates. If issues persist, check for naming conflicts in the original config.

**Issue**: Authentication failed when running Terraform
- **Solution**: Verify credentials and network connectivity. Ensure API access is enabled on Panorama.

**Issue**: Resources not found during apply
- **Solution**: Ensure the device group exists and you have proper permissions. Check that shared resources are accessible.

### Debug Mode

To see detailed parsing information:

```python
# Add to the script before main():
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

### Before Migration

1. **Test in non-production** first
2. **Backup existing configuration** using Panorama's native backup
3. **Review generated Terraform** for accuracy
4. **Validate rule ordering** matches your requirements
5. **Check for deprecated features** that may not translate

### During Migration

1. **Use Terraform workspaces** for different environments
2. **Apply in stages** (objects first, then rules)
3. **Monitor logs** for any errors
4. **Keep the XML source** for reference

### After Migration

1. **Commit Terraform to version control**
2. **Document any manual adjustments**
3. **Set up CI/CD** for future changes
4. **Regular state backups** using remote state

## Limitations

### Current Limitations

- Does not support all Panorama features (work in progress)
- Zone configuration must be manually created
- Interface configuration requires manual setup
- Virtual router configuration not included
- Some advanced features may need manual adjustment

### Manual Configuration Required

The following must be configured manually or added separately:

- Network interfaces
- Zones
- Virtual routers
- VPN configurations
- User-ID settings
- GlobalProtect configurations
- High Availability settings

## Extending the Script

### Adding New Resource Types

To add support for additional resource types:

1. Add a new parsing method in `PanoramaParser` class
2. Add a new generation method in `TerraformGenerator` class
3. Call both methods in `main()`

Example:

```python
# In PanoramaParser:
def parse_zones(self) -> List[Dict]:
    zones = []
    # Add parsing logic
    return zones

# In TerraformGenerator:
def generate_zones(self, zones: List[Dict]):
    # Add generation logic
    pass

# In main():
zones = panorama.parse_zones()
tf_gen.generate_zones(zones)
```

## Support and Contribution

### Getting Help

- Review the generated README.md in the output directory
- Check Palo Alto Networks Terraform provider documentation
- Consult the script's inline comments

### Contributing

To improve this script:
1. Add support for additional resource types
2. Improve error handling
3. Add unit tests
4. Enhance XML path detection

## Version History

- v1.0 - Initial release with core functionality
  - Address objects and groups
  - Service objects and groups
  - Security and NAT rules
  - Basic device group support

## License

This script is provided as-is for use with Palo Alto Networks devices.

## Additional Resources

- [Palo Alto Terraform Provider Documentation](https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)
- [Palo Alto API Documentation](https://docs.paloaltonetworks.com/pan-os/9-1/pan-os-panorama-api)
