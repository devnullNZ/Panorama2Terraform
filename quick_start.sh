#!/bin/bash
# Quick Start Script for Panorama to Terraform Converter
# This script demonstrates how to use the converter

set -e

echo "================================"
echo "Panorama to Terraform Converter"
echo "Quick Start Example"
echo "================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

echo "✓ Python 3 found"

# Check if the converter script exists
if [ ! -f "panorama_to_terraform.py" ]; then
    echo "Error: panorama_to_terraform.py not found in current directory"
    exit 1
fi

echo "✓ Converter script found"

# Make the script executable
chmod +x panorama_to_terraform.py

echo ""
echo "Running example conversion with sample configuration..."
echo ""

# Run the converter with the sample config
python3 panorama_to_terraform.py sample_panorama_config.xml --output-dir terraform_example

echo ""
echo "================================"
echo "Conversion Complete!"
echo "================================"
echo ""
echo "Generated files are in: ./terraform_example/"
echo ""
echo "Next steps:"
echo "  1. cd terraform_example"
echo "  2. Review the generated .tf files"
echo "  3. Create terraform.tfvars with your Panorama credentials:"
echo ""
echo "     panos_hostname = \"your-panorama-hostname\""
echo "     panos_username = \"admin\""
echo "     panos_password = \"your-password\""
echo "     device_group   = \"Production-DG\""
echo ""
echo "  4. Initialize Terraform:  terraform init"
echo "  5. Review the plan:        terraform plan"
echo "  6. Apply configuration:    terraform apply"
echo ""
echo "For more information, see USAGE_GUIDE.md"
echo ""
