#!/usr/bin/env python3
"""
Panorama Device Group Splitter

Copyright (c) 2025 GSW Systems

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

COMMERCIAL LICENSE AVAILABLE
For use in proprietary applications without AGPL v3 obligations,
contact sales@gswsystems.com for commercial licensing options.
See LICENSE-COMMERCIAL for details.

═══════════════════════════════════════════════════════════════════════

Splits a Panorama export into separate configurations per device group.
Useful for multi-HA-pair to multi-virtual-router migrations.
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

def parse_device_groups(root: ET.Element) -> list:
    """Get list of device groups from Panorama config"""
    device_groups = []
    seen = set()
    
    for dg in root.findall(".//device-group/entry"):
        name = dg.get('name')
        if name and name not in seen:
            device_groups.append(name)
            seen.add(name)
    
    return device_groups

def extract_device_group_config(root: ET.Element, device_group_name: str) -> ET.Element:
    """Extract configuration for a specific device group"""
    # Create new root config element
    new_config = ET.Element('config')
    new_config.set('version', root.get('version', '10.0.0'))
    
    # Create devices structure
    devices = ET.SubElement(new_config, 'devices')
    localhost = ET.SubElement(devices, 'entry')
    localhost.set('name', 'localhost.localdomain')
    
    # Find the specific device group
    dg_xpath = f".//device-group/entry[@name='{device_group_name}']"
    source_dg = root.find(dg_xpath)
    
    if source_dg is None:
        return None
    
    # Copy device-group
    device_group_container = ET.SubElement(localhost, 'device-group')
    device_group_container.append(source_dg)
    
    # Copy shared objects (they're referenced by device groups)
    # Note: Panorama configs can have MULTIPLE <shared> sections
    # We need to merge them all to capture all objects
    shared_sections = root.findall('.//shared')
    if shared_sections:
        # Create a merged shared section
        merged_shared = ET.Element('shared')
        
        # Track what we've added to avoid duplicates
        seen_children = {}
        
        for shared in shared_sections:
            for child in shared:
                child_tag = child.tag
                
                # If we haven't seen this tag yet, add it
                if child_tag not in seen_children:
                    merged_shared.append(child)
                    seen_children[child_tag] = child
                else:
                    # If the tag exists, merge the entries
                    existing = seen_children[child_tag]
                    for entry in child.findall('.//entry'):
                        entry_name = entry.get('name')
                        # Only add if not already present
                        if entry_name:
                            existing_names = [e.get('name') for e in existing.findall('.//entry')]
                            if entry_name not in existing_names:
                                existing.append(entry)
        
        new_config.append(merged_shared)
    
    # Copy template if it exists (network config)
    # Try to find template with matching name or reference
    template_name = device_group_name.replace('DG-', '').replace('dg-', '')
    template_xpath = f".//template/entry[@name='{template_name}']"
    source_template = root.find(template_xpath)
    
    if source_template is None:
        # Try without prefix
        for template in root.findall(".//template/entry"):
            t_name = template.get('name', '')
            if device_group_name.lower() in t_name.lower():
                source_template = template
                break
    
    if source_template is not None:
        template_container = ET.SubElement(localhost, 'template')
        template_container.append(source_template)
    
    # Copy template stack if exists
    for ts in root.findall(".//template-stack/entry"):
        # Check if this stack references our device group
        members = ts.findall('.//devices/entry')
        for member in members:
            if member.get('name') == device_group_name:
                ts_container = ET.SubElement(localhost, 'template-stack')
                ts_container.append(ts)
                break
    
    return new_config

def split_panorama_config(input_file: str, output_dir: str = None):
    """Split Panorama configuration by device group"""
    try:
        tree = ET.parse(input_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML file: {e}")
        return False
    
    # Get list of device groups
    device_groups = parse_device_groups(root)
    
    if not device_groups:
        print("No device groups found in Panorama configuration.")
        print("This may be a single firewall export, not a Panorama export.")
        return False
    
    print(f"\nFound {len(device_groups)} device groups:")
    for dg in device_groups:
        print(f"  - {dg}")
    
    # Create output directory
    if output_dir is None:
        output_dir = Path(input_file).parent / "split_configs"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nSplitting configurations into: {output_dir}")
    
    # Extract and save each device group
    for dg_name in device_groups:
        print(f"\nProcessing device group: {dg_name}")
        
        dg_config = extract_device_group_config(root, dg_name)
        
        if dg_config is None:
            print(f"  ⚠ Warning: Could not extract config for {dg_name}")
            continue
        
        # Sanitize filename
        safe_name = dg_name.replace('/', '_').replace(' ', '_')
        output_file = output_dir / f"{safe_name}.xml"
        
        # Write to file
        tree = ET.ElementTree(dg_config)
        ET.indent(tree, space="  ")
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
        
        print(f"  ✓ Saved to: {output_file}")
    
    print(f"\n✓ Successfully split {len(device_groups)} device groups")
    print(f"\nNext steps:")
    print(f"  1. cd {output_dir}")
    print(f"  2. Run panorama_to_terraform.py on each XML file:")
    print(f"     python3 panorama_to_terraform.py <device-group>.xml --output-dir <device-group>-tf")
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description='Split Panorama configuration by device group',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Split Panorama export into separate device group configs
  python3 split_device_groups.py panorama_export.xml
  
  # Specify custom output directory
  python3 split_device_groups.py panorama_export.xml --output-dir ./device-groups
  
  # Then convert each device group separately
  python3 panorama_to_terraform.py device-groups/DG-Internet.xml --output-dir internet-tf
  python3 panorama_to_terraform.py device-groups/DG-DMZ.xml --output-dir dmz-tf
  python3 panorama_to_terraform.py device-groups/DG-Guest.xml --output-dir guest-tf

Use Case:
  When you have a Panorama managing multiple HA pairs (each with its own
  device group), use this script to split the export so you can migrate
  each HA pair to a separate virtual router on your target firewall.
        '''
    )
    
    parser.add_argument('input_file', help='Panorama XML export file')
    parser.add_argument('--output-dir', '-o', help='Output directory for split configs')
    
    args = parser.parse_args()
    
    if not Path(args.input_file).exists():
        print(f"Error: Input file not found: {args.input_file}")
        return 1
    
    success = split_panorama_config(args.input_file, args.output_dir)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
