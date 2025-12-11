#!/usr/bin/env python3
"""
Palo Alto Panorama to Terraform Converter

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

This script parses Palo Alto Panorama server output (XML format) and converts it
into Terraform configuration files that can be used to configure replacement devices.

Supports:
- Device Groups
- Security Policies
- NAT Policies
- Address Objects
- Address Groups
- Service Objects
- Service Groups
- Zones
- Interfaces
- Virtual Routers
- And many more (36 object types total)

Usage:
    python panorama_to_terraform.py <input_file.xml> [--output-dir <dir>]
"""

import xml.etree.ElementTree as ET
import argparse
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


class PanoramaParser:
    """Parse Palo Alto Panorama XML configuration"""
    
    def __init__(self, xml_file: str):
        self.xml_file = xml_file
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()
        
    def parse_device_groups(self) -> List[Dict]:
        """Parse device groups from Panorama config"""
        device_groups = []
        
        # Find device-group elements
        for dg in self.root.findall(".//device-group/entry"):
            name = dg.get('name')
            if name:
                device_groups.append({
                    'name': name,
                    'description': self._get_text(dg, 'description')
                })
        
        return device_groups
    
    def parse_tags(self) -> List[Dict]:
        """Parse tags"""
        tags = []
        seen_names = set()
        
        paths = [
            ".//tag/entry",
            ".//device-group/entry/tag/entry"
        ]
        
        for path in paths:
            for tag in self.root.findall(path):
                name = tag.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                tag_obj = {
                    'name': name,
                    'color': self._get_text(tag, 'color'),
                    'comments': self._get_text(tag, 'comments')
                }
                
                tags.append(tag_obj)
        
        return tags
    
    def parse_regions(self) -> List[Dict]:
        """Parse regions (geographic locations)"""
        regions = []
        seen_names = set()
        
        paths = [
            ".//region/entry",
            ".//device-group/entry/region/entry"
        ]
        
        for path in paths:
            for region in self.root.findall(path):
                name = region.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                addresses = []
                for addr in region.findall('.//address/member'):
                    if addr.text:
                        addresses.append(addr.text)
                
                region_obj = {
                    'name': name,
                    'addresses': addresses
                }
                
                regions.append(region_obj)
        
        return regions
    
    def parse_custom_url_categories(self) -> List[Dict]:
        """Parse custom URL categories"""
        categories = []
        seen_names = set()
        
        paths = [
            ".//custom-url-category/entry",
            ".//device-group/entry/custom-url-category/entry"
        ]
        
        for path in paths:
            for cat in self.root.findall(path):
                name = cat.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                url_list = []
                for url in cat.findall('.//list/member'):
                    if url.text:
                        url_list.append(url.text)
                
                cat_obj = {
                    'name': name,
                    'type': self._get_text(cat, 'type'),
                    'list': url_list,
                    'description': self._get_text(cat, 'description')
                }
                
                categories.append(cat_obj)
        
        return categories
    
    def parse_application_groups(self) -> List[Dict]:
        """Parse application groups"""
        app_groups = []
        seen_names = set()
        
        paths = [
            ".//application-group/entry",
            ".//device-group/entry/application-group/entry"
        ]
        
        for path in paths:
            for ag in self.root.findall(path):
                name = ag.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                members = []
                for member in ag.findall('.//members/member'):
                    if member.text:
                        members.append(member.text)
                
                ag_obj = {
                    'name': name,
                    'members': members
                }
                
                app_groups.append(ag_obj)
        
        return app_groups
    
    def parse_application_filters(self) -> List[Dict]:
        """Parse application filters"""
        app_filters = []
        seen_names = set()
        
        paths = [
            ".//application-filter/entry",
            ".//device-group/entry/application-filter/entry"
        ]
        
        for path in paths:
            for af in self.root.findall(path):
                name = af.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                af_obj = {
                    'name': name,
                    'category': self._get_members(af, 'category'),
                    'subcategory': self._get_members(af, 'subcategory'),
                    'technology': self._get_members(af, 'technology'),
                    'risk': self._get_members(af, 'risk'),
                    'evasive': self._get_text(af, 'evasive'),
                    'excessive_bandwidth_use': self._get_text(af, 'excessive-bandwidth-use'),
                    'prone_to_misuse': self._get_text(af, 'prone-to-misuse'),
                    'is_saas': self._get_text(af, 'is-saas'),
                    'transfers_files': self._get_text(af, 'transfers-files'),
                    'tunnels_other_apps': self._get_text(af, 'tunnels-other-apps'),
                    'used_by_malware': self._get_text(af, 'used-by-malware'),
                }
                
                app_filters.append(af_obj)
        
        return app_filters
    
    def parse_external_lists(self) -> List[Dict]:
        """Parse external dynamic lists"""
        ext_lists = []
        seen_names = set()
        
        paths = [
            ".//external-list/entry",
            ".//device-group/entry/external-list/entry"
        ]
        
        for path in paths:
            for ext_list in self.root.findall(path):
                name = ext_list.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                # Determine type
                list_type = None
                url = None
                recurring = None
                
                type_elem = ext_list.find('type')
                if type_elem is not None:
                    if type_elem.find('ip') is not None:
                        list_type = 'ip'
                        url = self._get_text(type_elem, 'ip/url')
                        # Check for recurring schedule
                        if type_elem.find('.//recurring/hourly') is not None:
                            recurring = 'hourly'
                        elif type_elem.find('.//recurring/five-minute') is not None:
                            recurring = 'five-minute'
                        elif type_elem.find('.//recurring/daily') is not None:
                            recurring = 'daily'
                    elif type_elem.find('domain') is not None:
                        list_type = 'domain'
                        url = self._get_text(type_elem, 'domain/url')
                        if type_elem.find('.//recurring/hourly') is not None:
                            recurring = 'hourly'
                        elif type_elem.find('.//recurring/five-minute') is not None:
                            recurring = 'five-minute'
                        elif type_elem.find('.//recurring/daily') is not None:
                            recurring = 'daily'
                    elif type_elem.find('url') is not None:
                        list_type = 'url'
                        url = self._get_text(type_elem, 'url/url')
                        if type_elem.find('.//recurring/hourly') is not None:
                            recurring = 'hourly'
                        elif type_elem.find('.//recurring/five-minute') is not None:
                            recurring = 'five-minute'
                        elif type_elem.find('.//recurring/daily') is not None:
                            recurring = 'daily'
                
                ext_list_obj = {
                    'name': name,
                    'type': list_type,
                    'url': url,
                    'recurring': recurring,
                    'description': self._get_text(ext_list, 'description')
                }
                
                ext_lists.append(ext_list_obj)
        
        return ext_lists
    
    def parse_address_objects(self) -> List[Dict]:
        """Parse address objects"""
        # Use dictionary to track objects by name, allowing overrides
        addresses_dict = {}
        
        # Parse in order: device groups first, then shared
        # This allows device-group definitions to override shared references
        paths = [
            ".//device-group/entry/address/entry",
            ".//shared/address/entry",
            ".//address/entry"
        ]
        
        for path in paths:
            for addr in self.root.findall(path):
                name = addr.get('name')
                if not name:
                    continue
                
                # Check if this is just a reference (only has <id> tag, no actual content)
                has_id_only = (addr.find('id') is not None and 
                              addr.find('ip-netmask') is None and 
                              addr.find('ip-range') is None and
                              addr.find('fqdn') is None and
                              addr.find('description') is None)
                
                if has_id_only:
                    # Skip reference-only entries
                    continue
                
                addr_obj = {'name': name}
                
                # Check for IP netmask
                ip_netmask = addr.find('ip-netmask')
                if ip_netmask is not None:
                    addr_obj['type'] = 'ip-netmask'
                    addr_obj['value'] = ip_netmask.text
                
                # Check for IP range
                ip_range = addr.find('ip-range')
                if ip_range is not None:
                    addr_obj['type'] = 'ip-range'
                    addr_obj['value'] = ip_range.text
                
                # Check for FQDN
                fqdn = addr.find('fqdn')
                if fqdn is not None:
                    addr_obj['type'] = 'fqdn'
                    addr_obj['value'] = fqdn.text
                
                # Description
                desc = addr.find('description')
                if desc is not None:
                    addr_obj['description'] = desc.text
                
                # Tags
                tags = []
                tag_member = addr.findall('.//tag/member')
                for tag in tag_member:
                    if tag.text:
                        tags.append(tag.text)
                addr_obj['tags'] = tags
                
                # Only add/override if this entry has content (value defined)
                # OR if we haven't seen this name yet
                if ('value' in addr_obj or name not in addresses_dict):
                    addresses_dict[name] = addr_obj
        
        return list(addresses_dict.values())
    
    def parse_address_groups(self) -> List[Dict]:
        """Parse address groups"""
        # Use dictionary to track groups by name, allowing overrides
        groups_dict = {}
        
        # Parse in order: device groups first, then shared
        # This allows device-group definitions to override shared references
        paths = [
            ".//device-group/entry/address-group/entry",
            ".//shared/address-group/entry",
            ".//address-group/entry"
        ]
        
        for path in paths:
            for grp in self.root.findall(path):
                name = grp.get('name')
                if not name:
                    continue
                
                # Check if this is just a reference (only has <id> tag, no actual content)
                # References are used in Panorama to inherit shared objects
                has_id_only = (grp.find('id') is not None and 
                              grp.find('.//static') is None and 
                              grp.find('.//dynamic') is None and
                              grp.find('description') is None)
                
                if has_id_only:
                    # Skip reference-only entries (they're just pointers to shared objects)
                    continue
                
                # Parse members
                members = []
                static_members = grp.findall('.//static/member')
                for member in static_members:
                    if member.text:
                        members.append(member.text)
                
                dynamic_filter = grp.find('.//dynamic/filter')
                
                group_obj = {
                    'name': name,
                    'static_members': members,
                    'dynamic_filter': dynamic_filter.text if dynamic_filter is not None else None,
                    'description': self._get_text(grp, 'description')
                }
                
                # Only add/override if this entry has content (members or dynamic filter)
                # OR if we haven't seen this name yet
                if (members or dynamic_filter is not None or name not in groups_dict):
                    groups_dict[name] = group_obj
        
        return list(groups_dict.values())
    
    def parse_service_objects(self) -> List[Dict]:
        """Parse service objects"""
        # Use dictionary to track objects by name, allowing overrides
        services_dict = {}
        
        # Parse in order: device groups first, then shared
        paths = [
            ".//device-group/entry/service/entry",
            ".//shared/service/entry",
            ".//service/entry"
        ]
        
        for path in paths:
            for svc in self.root.findall(path):
                name = svc.get('name')
                if not name:
                    continue
                
                # Check if this is just a reference (only has <id> tag, no actual content)
                has_id_only = (svc.find('id') is not None and 
                              svc.find('protocol') is None and
                              svc.find('description') is None)
                
                if has_id_only:
                    # Skip reference-only entries
                    continue
                
                service_obj = {'name': name}
                
                # Protocol and port
                protocol = svc.find('protocol')
                if protocol is not None:
                    tcp = protocol.find('tcp')
                    udp = protocol.find('udp')
                    
                    if tcp is not None:
                        service_obj['protocol'] = 'tcp'
                        port = tcp.find('port')
                        if port is not None:
                            service_obj['port'] = port.text
                    elif udp is not None:
                        service_obj['protocol'] = 'udp'
                        port = udp.find('port')
                        if port is not None:
                            service_obj['port'] = port.text
                
                service_obj['description'] = self._get_text(svc, 'description')
                
                # Only add/override if this entry has content (protocol defined)
                # OR if we haven't seen this name yet
                if ('protocol' in service_obj or name not in services_dict):
                    services_dict[name] = service_obj
        
        return list(services_dict.values())
    
    def parse_service_groups(self) -> List[Dict]:
        """Parse service groups"""
        groups = []
        # Use dictionary to track groups by name, allowing overrides
        groups_dict = {}
        
        # Parse in order: device groups first, then shared
        paths = [
            ".//device-group/entry/service-group/entry",
            ".//shared/service-group/entry",
            ".//service-group/entry"
        ]
        
        for path in paths:
            for grp in self.root.findall(path):
                name = grp.get('name')
                if not name:
                    continue
                
                # Check if this is just a reference (only has <id> tag, no actual content)
                has_id_only = (grp.find('id') is not None and 
                              grp.find('.//members') is None and
                              grp.find('description') is None)
                
                if has_id_only:
                    # Skip reference-only entries
                    continue
                
                members = []
                for member in grp.findall('.//members/member'):
                    if member.text:
                        members.append(member.text)
                
                group_obj = {
                    'name': name,
                    'members': members,
                    'description': self._get_text(grp, 'description')
                }
                
                # Only add/override if this entry has content (members defined)
                # OR if we haven't seen this name yet
                if (members or name not in groups_dict):
                    groups_dict[name] = group_obj
        
        return list(groups_dict.values())
    
    def parse_security_rules(self) -> List[Dict]:
        """Parse security policy rules"""
        rules = []
        seen_names = set()
        
        paths = [
            ".//security/rules/entry",
            ".//device-group/entry/pre-rulebase/security/rules/entry",
            ".//device-group/entry/post-rulebase/security/rules/entry"
        ]
        
        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                rule_obj = {
                    'name': name,
                    'source_zones': self._get_members(rule, 'from'),
                    'source_addresses': self._get_members(rule, 'source'),
                    'destination_zones': self._get_members(rule, 'to'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'applications': self._get_members(rule, 'application'),
                    'services': self._get_members(rule, 'service'),
                    'action': self._get_text(rule, 'action'),
                    'description': self._get_text(rule, 'description')
                }
                
                # Log settings
                log_start = rule.find('log-start')
                log_end = rule.find('log-end')
                rule_obj['log_start'] = log_start.text == 'yes' if log_start is not None else False
                rule_obj['log_end'] = log_end.text == 'yes' if log_end is not None else False
                
                # Disabled status
                disabled = rule.find('disabled')
                rule_obj['disabled'] = disabled.text == 'yes' if disabled is not None else False
                
                rules.append(rule_obj)
        
        return rules
    
    def parse_nat_rules(self) -> List[Dict]:
        """Parse NAT policy rules"""
        rules = []
        seen_names = set()
        
        paths = [
            ".//nat/rules/entry",
            ".//device-group/entry/pre-rulebase/nat/rules/entry",
            ".//device-group/entry/post-rulebase/nat/rules/entry"
        ]
        
        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                rule_obj = {
                    'name': name,
                    'source_zones': self._get_members(rule, 'from'),
                    'destination_zone': self._get_text(rule, 'to-interface'),
                    'source_addresses': self._get_members(rule, 'source'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'service': self._get_text(rule, 'service'),
                    'description': self._get_text(rule, 'description')
                }
                
                # Source translation
                source_translation = rule.find('.//source-translation')
                if source_translation is not None:
                    dynamic_ip_and_port = source_translation.find('dynamic-ip-and-port')
                    if dynamic_ip_and_port is not None:
                        translated_address = dynamic_ip_and_port.find('.//translated-address')
                        if translated_address is not None:
                            members = []
                            for member in translated_address.findall('member'):
                                if member.text:
                                    members.append(member.text)
                            rule_obj['source_translation_type'] = 'dynamic-ip-and-port'
                            rule_obj['source_translation_address'] = members
                
                # Destination translation
                destination_translation = rule.find('.//destination-translation')
                if destination_translation is not None:
                    translated_address = destination_translation.find('translated-address')
                    translated_port = destination_translation.find('translated-port')
                    
                    if translated_address is not None:
                        rule_obj['destination_translation_address'] = translated_address.text
                    if translated_port is not None:
                        rule_obj['destination_translation_port'] = translated_port.text
                
                # Disabled status
                disabled = rule.find('disabled')
                rule_obj['disabled'] = disabled.text == 'yes' if disabled is not None else False
                
                rules.append(rule_obj)
        
        return rules
    
    def parse_schedules(self) -> List[Dict]:
        """Parse schedules"""
        schedules = []
        seen_names = set()
        
        paths = [
            ".//schedule/entry",
            ".//device-group/entry/schedule/entry"
        ]
        
        for path in paths:
            for sched in self.root.findall(path):
                name = sched.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                sched_obj = {
                    'name': name,
                    'schedule_type': None,
                    'recurring': []
                }
                
                # Check for recurring schedule
                recurring = sched.find('schedule-type/recurring')
                if recurring is not None:
                    sched_obj['schedule_type'] = 'recurring'
                    for entry in recurring.findall('entry'):
                        rec_name = entry.get('name')
                        rec_obj = {
                            'name': rec_name
                        }
                        sched_obj['recurring'].append(rec_obj)
                
                # Check for non-recurring schedule
                non_recurring = sched.find('schedule-type/non-recurring')
                if non_recurring is not None:
                    sched_obj['schedule_type'] = 'non-recurring'
                
                schedules.append(sched_obj)
        
        return schedules
    
    def parse_decryption_rules(self) -> List[Dict]:
        """Parse decryption policy rules"""
        rules = []
        seen_names = set()
        
        paths = [
            ".//decryption/rules/entry",
            ".//device-group/entry/pre-rulebase/decryption/rules/entry",
            ".//device-group/entry/post-rulebase/decryption/rules/entry"
        ]
        
        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                rule_obj = {
                    'name': name,
                    'uuid': rule.get('uuid'),
                    'source_zones': self._get_members(rule, 'from'),
                    'destination_zones': self._get_members(rule, 'to'),
                    'source_addresses': self._get_members(rule, 'source'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'source_users': self._get_members(rule, 'source-user'),
                    'categories': self._get_members(rule, 'category'),
                    'services': self._get_members(rule, 'service'),
                    'action': self._get_text(rule, 'action'),
                    'type': None,
                    'profile': self._get_text(rule, 'profile'),
                    'description': self._get_text(rule, 'description'),
                    'disabled': self._get_text(rule, 'disabled') == 'yes',
                    'log_setting': self._get_text(rule, 'log-setting')
                }
                
                # Determine type
                type_elem = rule.find('type')
                if type_elem is not None:
                    if type_elem.find('ssl-forward-proxy') is not None:
                        rule_obj['type'] = 'ssl-forward-proxy'
                    elif type_elem.find('ssl-inbound-inspection') is not None:
                        rule_obj['type'] = 'ssl-inbound-inspection'
                    elif type_elem.find('ssh-proxy') is not None:
                        rule_obj['type'] = 'ssh-proxy'
                
                rules.append(rule_obj)
        
        return rules
    
    def parse_pbf_rules(self) -> List[Dict]:
        """Parse Policy-Based Forwarding rules"""
        rules = []
        seen_names = set()
        
        paths = [
            ".//pbf/rules/entry",
            ".//device-group/entry/pre-rulebase/pbf/rules/entry",
            ".//device-group/entry/post-rulebase/pbf/rules/entry"
        ]
        
        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                rule_obj = {
                    'name': name,
                    'uuid': rule.get('uuid'),
                    'description': self._get_text(rule, 'description'),
                    'disabled': self._get_text(rule, 'disabled') == 'yes',
                    'source_zones': [],
                    'source_addresses': self._get_members(rule, 'source'),
                    'source_users': self._get_members(rule, 'source-user'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'applications': self._get_members(rule, 'application'),
                    'services': self._get_members(rule, 'service'),
                    'action': None
                }
                
                # Get source zones
                from_elem = rule.find('from')
                if from_elem is not None:
                    for zone in from_elem.findall('.//zone/member'):
                        if zone.text:
                            rule_obj['source_zones'].append(zone.text)
                
                # Get action
                action_elem = rule.find('action')
                if action_elem is not None:
                    forward = action_elem.find('forward')
                    if forward is not None:
                        nexthop_ip = self._get_text(forward, 'nexthop/ip-address')
                        egress_iface = self._get_text(forward, 'egress-interface')
                        rule_obj['action'] = {
                            'type': 'forward',
                            'nexthop_ip': nexthop_ip,
                            'egress_interface': egress_iface
                        }
                    
                    discard = action_elem.find('discard')
                    if discard is not None:
                        rule_obj['action'] = {
                            'type': 'discard'
                        }
                    
                    no_pbf = action_elem.find('no-pbf')
                    if no_pbf is not None:
                        rule_obj['action'] = {
                            'type': 'no-pbf'
                        }
                
                # Enforce symmetric return
                enforce_sym = rule.find('.//enforce-symmetric-return/enabled')
                if enforce_sym is not None:
                    rule_obj['enforce_symmetric_return'] = enforce_sym.text == 'yes'
                
                rules.append(rule_obj)
        
        return rules
    
    def parse_application_override_rules(self) -> List[Dict]:
        """Parse Application Override rules"""
        rules = []
        seen_names = set()
        
        paths = [
            ".//application-override/rules/entry",
            ".//device-group/entry/pre-rulebase/application-override/rules/entry",
            ".//device-group/entry/post-rulebase/application-override/rules/entry"
        ]
        
        for path in paths:
            for rule in self.root.findall(path):
                name = rule.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                rule_obj = {
                    'name': name,
                    'description': self._get_text(rule, 'description'),
                    'disabled': self._get_text(rule, 'disabled') == 'yes',
                    'source_zones': self._get_members(rule, 'from'),
                    'destination_zones': self._get_members(rule, 'to'),
                    'source_addresses': self._get_members(rule, 'source'),
                    'destination_addresses': self._get_members(rule, 'destination'),
                    'port': self._get_text(rule, 'port'),
                    'protocol': self._get_text(rule, 'protocol'),
                    'application': self._get_text(rule, 'application')
                }
                
                rules.append(rule_obj)
        
        return rules
    
    def parse_zones(self) -> List[Dict]:
        """Parse zone configurations"""
        zones = []
        seen_names = set()
        
        paths = [
            ".//zone/entry",
            ".//vsys/entry/zone/entry",
            ".//devices/entry/vsys/entry/zone/entry"
        ]
        
        for path in paths:
            for zone in self.root.findall(path):
                name = zone.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                # Determine zone type
                zone_type = 'layer3'
                if zone.find('network/layer2') is not None:
                    zone_type = 'layer2'
                elif zone.find('network/tap') is not None:
                    zone_type = 'tap'
                elif zone.find('network/virtual-wire') is not None:
                    zone_type = 'virtual-wire'
                elif zone.find('network/tunnel') is not None:
                    zone_type = 'tunnel'
                
                # Get interfaces
                interfaces = []
                for iface in zone.findall('.//network/*/member'):
                    if iface.text:
                        interfaces.append(iface.text)
                
                # Get zone protection profile
                zone_profile = zone.find('.//zone-protection-profile')
                
                zone_obj = {
                    'name': name,
                    'type': zone_type,
                    'interfaces': interfaces,
                    'zone_protection_profile': zone_profile.text if zone_profile is not None else None
                }
                
                zones.append(zone_obj)
        
        return zones
    
    def parse_interfaces(self) -> List[Dict]:
        """Parse interface configurations"""
        interfaces = []
        seen_names = set()
        
        # Ethernet interfaces
        eth_paths = [
            ".//network/interface/ethernet/entry",
            ".//devices/entry/network/interface/ethernet/entry"
        ]
        
        for path in eth_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                iface_obj = {
                    'name': name,
                    'type': 'ethernet',
                    'mode': None,
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment')
                }
                
                # Determine mode (layer3, layer2, virtual-wire, tap, ha, aggregate-group)
                if iface.find('layer3') is not None:
                    iface_obj['mode'] = 'layer3'
                    l3 = iface.find('layer3')
                    
                    # Get IP addresses
                    for ip in l3.findall('.//ip/entry'):
                        ip_name = ip.get('name')
                        if ip_name:
                            iface_obj['ip_addresses'].append(ip_name)
                    
                    # Get IPv6 addresses
                    for ip in l3.findall('.//ipv6/address/entry'):
                        ip_name = ip.get('name')
                        if ip_name:
                            iface_obj['ipv6_addresses'].append(ip_name)
                    
                    # Management profile
                    mgmt_profile = l3.find('interface-management-profile')
                    if mgmt_profile is not None:
                        iface_obj['management_profile'] = mgmt_profile.text
                    
                elif iface.find('layer2') is not None:
                    iface_obj['mode'] = 'layer2'
                elif iface.find('virtual-wire') is not None:
                    iface_obj['mode'] = 'virtual-wire'
                elif iface.find('tap') is not None:
                    iface_obj['mode'] = 'tap'
                elif iface.find('ha') is not None:
                    iface_obj['mode'] = 'ha'
                elif iface.find('aggregate-group') is not None:
                    iface_obj['mode'] = 'aggregate-group'
                
                interfaces.append(iface_obj)
        
        # VLAN interfaces
        vlan_paths = [
            ".//network/interface/vlan/units/entry",
            ".//devices/entry/network/interface/vlan/units/entry"
        ]
        
        for path in vlan_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                iface_obj = {
                    'name': f'vlan.{name}',
                    'type': 'vlan',
                    'mode': 'layer3',
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment'),
                    'tag': self._get_text(iface, 'tag')
                }
                
                # Get IP addresses
                for ip in iface.findall('.//ip/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ip_addresses'].append(ip_name)
                
                # Get IPv6 addresses
                for ip in iface.findall('.//ipv6/address/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ipv6_addresses'].append(ip_name)
                
                # Management profile
                mgmt_profile = iface.find('interface-management-profile')
                if mgmt_profile is not None:
                    iface_obj['management_profile'] = mgmt_profile.text
                
                interfaces.append(iface_obj)
        
        # Loopback interfaces
        loopback_paths = [
            ".//network/interface/loopback/units/entry",
            ".//devices/entry/network/interface/loopback/units/entry"
        ]
        
        for path in loopback_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                iface_obj = {
                    'name': f'loopback.{name}',
                    'type': 'loopback',
                    'mode': 'layer3',
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment')
                }
                
                # Get IP addresses
                for ip in iface.findall('.//ip/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ip_addresses'].append(ip_name)
                
                # Get IPv6 addresses
                for ip in iface.findall('.//ipv6/address/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ipv6_addresses'].append(ip_name)
                
                interfaces.append(iface_obj)
        
        # Tunnel interfaces
        tunnel_paths = [
            ".//network/interface/tunnel/units/entry",
            ".//devices/entry/network/interface/tunnel/units/entry"
        ]
        
        for path in tunnel_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                iface_obj = {
                    'name': f'tunnel.{name}',
                    'type': 'tunnel',
                    'mode': 'layer3',
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment')
                }
                
                # Get IP addresses
                for ip in iface.findall('.//ip/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ip_addresses'].append(ip_name)
                
                # Get IPv6 addresses
                for ip in iface.findall('.//ipv6/address/entry'):
                    ip_name = ip.get('name')
                    if ip_name:
                        iface_obj['ipv6_addresses'].append(ip_name)
                
                # Management profile
                mgmt_profile = iface.find('interface-management-profile')
                if mgmt_profile is not None:
                    iface_obj['management_profile'] = mgmt_profile.text
                
                interfaces.append(iface_obj)
        
        # Aggregate interfaces (ae)
        aggregate_paths = [
            ".//network/interface/aggregate-ethernet/entry",
            ".//devices/entry/network/interface/aggregate-ethernet/entry"
        ]
        
        for path in aggregate_paths:
            for iface in self.root.findall(path):
                name = iface.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                iface_obj = {
                    'name': name,
                    'type': 'aggregate',
                    'mode': None,
                    'ip_addresses': [],
                    'ipv6_addresses': [],
                    'zone': None,
                    'virtual_router': None,
                    'management_profile': None,
                    'comment': self._get_text(iface, 'comment')
                }
                
                # Determine mode
                if iface.find('layer3') is not None:
                    iface_obj['mode'] = 'layer3'
                    l3 = iface.find('layer3')
                    
                    # Get IP addresses from main interface
                    for ip in l3.findall('.//ip/entry'):
                        ip_name = ip.get('name')
                        if ip_name:
                            iface_obj['ip_addresses'].append(ip_name)
                    
                    # Management profile
                    mgmt_profile = l3.find('interface-management-profile')
                    if mgmt_profile is not None:
                        iface_obj['management_profile'] = mgmt_profile.text
                    
                    # Get subinterfaces (units)
                    for unit in l3.findall('.//units/entry'):
                        unit_name = unit.get('name')
                        if unit_name and unit_name not in seen_names:
                            seen_names.add(unit_name)
                            
                            unit_obj = {
                                'name': unit_name,
                                'type': 'aggregate-subinterface',
                                'mode': 'layer3',
                                'ip_addresses': [],
                                'ipv6_addresses': [],
                                'zone': None,
                                'virtual_router': None,
                                'management_profile': None,
                                'comment': self._get_text(unit, 'comment'),
                                'tag': self._get_text(unit, 'tag')
                            }
                            
                            # Get IP addresses
                            for ip in unit.findall('.//ip/entry'):
                                ip_name = ip.get('name')
                                if ip_name:
                                    unit_obj['ip_addresses'].append(ip_name)
                            
                            # Management profile
                            unit_mgmt = unit.find('interface-management-profile')
                            if unit_mgmt is not None:
                                unit_obj['management_profile'] = unit_mgmt.text
                            
                            interfaces.append(unit_obj)
                
                elif iface.find('layer2') is not None:
                    iface_obj['mode'] = 'layer2'
                
                interfaces.append(iface_obj)
        
        return interfaces
    
    def parse_virtual_routers(self) -> List[Dict]:
        """Parse virtual router configurations"""
        vrouters_dict = {}
        
        # Parse from templates first (most authoritative source)
        for template in self.root.findall('.//template/entry'):
            template_name = template.get('name')
            
            for vr in template.findall('.//network/virtual-router/entry'):
                name = vr.get('name')
                if not name:
                    continue
                
                # Get interfaces
                interfaces = []
                for iface in vr.findall('.//interface/member'):
                    if iface.text:
                        interfaces.append(iface.text)
                
                # Get static routes
                static_routes = []
                for route in vr.findall('.//routing-table/ip/static-route/entry'):
                    route_name = route.get('name')
                    destination = self._get_text(route, 'destination')
                    nexthop_ip = self._get_text(route, 'nexthop/ip-address')
                    nexthop_iface = self._get_text(route, 'nexthop/next-vr')
                    metric = self._get_text(route, 'metric')
                    
                    if route_name:
                        static_routes.append({
                            'name': route_name,
                            'destination': destination,
                            'nexthop_ip': nexthop_ip,
                            'nexthop_interface': nexthop_iface,
                            'metric': metric
                        })
                
                vr_obj = {
                    'name': name,
                    'template': template_name,
                    'interfaces': interfaces,
                    'static_routes': static_routes
                }
                
                # Create a unique key based on name + interface signature
                # This handles cases where multiple templates have VRs with same name
                interface_signature = ','.join(sorted(interfaces[:5]))  # First 5 interfaces as signature
                unique_key = f"{name}_{interface_signature}"
                
                # Only add if we haven't seen this exact configuration
                # Or if this has more interfaces (more complete definition)
                if unique_key not in vrouters_dict or len(interfaces) > len(vrouters_dict[unique_key]['interfaces']):
                    vrouters_dict[unique_key] = vr_obj
        
        # Also check device-level VRs (less common but possible)
        for vr in self.root.findall('.//devices/entry/network/virtual-router/entry'):
            name = vr.get('name')
            if not name:
                continue
            
            interfaces = []
            for iface in vr.findall('.//interface/member'):
                if iface.text:
                    interfaces.append(iface.text)
            
            static_routes = []
            for route in vr.findall('.//routing-table/ip/static-route/entry'):
                route_name = route.get('name')
                destination = self._get_text(route, 'destination')
                nexthop_ip = self._get_text(route, 'nexthop/ip-address')
                nexthop_iface = self._get_text(route, 'nexthop/next-vr')
                metric = self._get_text(route, 'metric')
                
                if route_name:
                    static_routes.append({
                        'name': route_name,
                        'destination': destination,
                        'nexthop_ip': nexthop_ip,
                        'nexthop_interface': nexthop_iface,
                        'metric': metric
                    })
            
            vr_obj = {
                'name': name,
                'template': 'device-specific',
                'interfaces': interfaces,
                'static_routes': static_routes
            }
            
            interface_signature = ','.join(sorted(interfaces[:5]))
            unique_key = f"{name}_{interface_signature}"
            
            if unique_key not in vrouters_dict or len(interfaces) > len(vrouters_dict[unique_key]['interfaces']):
                vrouters_dict[unique_key] = vr_obj
        
        return list(vrouters_dict.values())
    
    def parse_logical_routers(self) -> List[Dict]:
        """Parse logical router configurations (Advanced Routing Engine)
        
        Logical routers are part of PAN-OS 10.2+ Advanced Routing Engine.
        They replace virtual routers with industry-standard configuration.
        """
        lrouters_dict = {}
        
        # Parse from templates first (most authoritative source)
        for template in self.root.findall('.//template/entry'):
            template_name = template.get('name')
            
            for lr in template.findall('.//network/logical-router/entry'):
                name = lr.get('name')
                if not name:
                    continue
                
                # Get interfaces
                interfaces = []
                for iface in lr.findall('.//interface/member'):
                    if iface.text:
                        interfaces.append(iface.text)
                
                # Get static routes
                static_routes = []
                for route in lr.findall('.//routing-table/ip/static-route/entry'):
                    route_name = route.get('name')
                    destination = self._get_text(route, 'destination')
                    nexthop_ip = self._get_text(route, 'nexthop/ip-address')
                    nexthop_iface = self._get_text(route, 'nexthop/next-lr')  # next-lr for logical routers
                    metric = self._get_text(route, 'metric')
                    
                    if route_name:
                        static_routes.append({
                            'name': route_name,
                            'destination': destination,
                            'nexthop_ip': nexthop_ip,
                            'nexthop_interface': nexthop_iface,
                            'metric': metric
                        })
                
                lr_obj = {
                    'name': name,
                    'template': template_name,
                    'router_type': 'logical',  # Mark as logical router
                    'interfaces': interfaces,
                    'static_routes': static_routes
                }
                
                # Create a unique key based on name + interface signature
                interface_signature = ','.join(sorted(interfaces[:5]))
                unique_key = f"{name}_{interface_signature}"
                
                if unique_key not in lrouters_dict or len(interfaces) > len(lrouters_dict[unique_key]['interfaces']):
                    lrouters_dict[unique_key] = lr_obj
        
        # Also check device-level logical routers
        for lr in self.root.findall('.//devices/entry/network/logical-router/entry'):
            name = lr.get('name')
            if not name:
                continue
            
            interfaces = []
            for iface in lr.findall('.//interface/member'):
                if iface.text:
                    interfaces.append(iface.text)
            
            static_routes = []
            for route in lr.findall('.//routing-table/ip/static-route/entry'):
                route_name = route.get('name')
                destination = self._get_text(route, 'destination')
                nexthop_ip = self._get_text(route, 'nexthop/ip-address')
                nexthop_iface = self._get_text(route, 'nexthop/next-lr')
                metric = self._get_text(route, 'metric')
                
                if route_name:
                    static_routes.append({
                        'name': route_name,
                        'destination': destination,
                        'nexthop_ip': nexthop_ip,
                        'nexthop_interface': nexthop_iface,
                        'metric': metric
                    })
            
            lr_obj = {
                'name': name,
                'template': 'device-specific',
                'router_type': 'logical',
                'interfaces': interfaces,
                'static_routes': static_routes
            }
            
            interface_signature = ','.join(sorted(interfaces[:5]))
            unique_key = f"{name}_{interface_signature}"
            
            if unique_key not in lrouters_dict or len(interfaces) > len(lrouters_dict[unique_key]['interfaces']):
                lrouters_dict[unique_key] = lr_obj
        
        return list(lrouters_dict.values())
    
    def parse_security_profiles(self) -> Dict[str, List[Dict]]:
        """Parse security profiles (antivirus, vulnerability, spyware, url-filtering, file-blocking, wildfire)"""
        profiles = {
            'antivirus': [],
            'vulnerability': [],
            'anti_spyware': [],
            'url_filtering': [],
            'file_blocking': [],
            'wildfire_analysis': []
        }
        
        seen_names = {key: set() for key in profiles.keys()}
        
        # Antivirus profiles
        av_paths = [
            ".//profiles/virus/entry",
            ".//device-group/entry/profiles/virus/entry",
            ".//shared/profiles/virus/entry"
        ]
        
        for path in av_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['antivirus']:
                    continue
                
                seen_names['antivirus'].add(name)
                profiles['antivirus'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })
        
        # Vulnerability profiles
        vuln_paths = [
            ".//profiles/vulnerability/entry",
            ".//device-group/entry/profiles/vulnerability/entry",
            ".//shared/profiles/vulnerability/entry"
        ]
        
        for path in vuln_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['vulnerability']:
                    continue
                
                seen_names['vulnerability'].add(name)
                profiles['vulnerability'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })
        
        # Anti-spyware profiles
        spy_paths = [
            ".//profiles/spyware/entry",
            ".//device-group/entry/profiles/spyware/entry",
            ".//shared/profiles/spyware/entry"
        ]
        
        for path in spy_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['anti_spyware']:
                    continue
                
                seen_names['anti_spyware'].add(name)
                profiles['anti_spyware'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })
        
        # URL filtering profiles
        url_paths = [
            ".//profiles/url-filtering/entry",
            ".//device-group/entry/profiles/url-filtering/entry",
            ".//shared/profiles/url-filtering/entry"
        ]
        
        for path in url_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['url_filtering']:
                    continue
                
                seen_names['url_filtering'].add(name)
                profiles['url_filtering'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })
        
        # File blocking profiles
        fb_paths = [
            ".//profiles/file-blocking/entry",
            ".//device-group/entry/profiles/file-blocking/entry",
            ".//shared/profiles/file-blocking/entry"
        ]
        
        for path in fb_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['file_blocking']:
                    continue
                
                seen_names['file_blocking'].add(name)
                profiles['file_blocking'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })
        
        # WildFire analysis profiles
        wf_paths = [
            ".//profiles/wildfire-analysis/entry",
            ".//device-group/entry/profiles/wildfire-analysis/entry",
            ".//shared/profiles/wildfire-analysis/entry"
        ]
        
        for path in wf_paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names['wildfire_analysis']:
                    continue
                
                seen_names['wildfire_analysis'].add(name)
                profiles['wildfire_analysis'].append({
                    'name': name,
                    'description': self._get_text(prof, 'description')
                })
        
        return profiles
    
    def parse_security_profile_groups(self) -> List[Dict]:
        """Parse security profile groups"""
        groups = []
        seen_names = set()
        
        paths = [
            ".//profile-group/entry",
            ".//device-group/entry/profile-group/entry",
            ".//shared/profile-group/entry"
        ]
        
        for path in paths:
            for grp in self.root.findall(path):
                name = grp.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                group_obj = {
                    'name': name,
                    'virus': self._get_members(grp, 'virus'),
                    'spyware': self._get_members(grp, 'spyware'),
                    'vulnerability': self._get_members(grp, 'vulnerability'),
                    'url_filtering': self._get_members(grp, 'url-filtering'),
                    'file_blocking': self._get_members(grp, 'file-blocking'),
                    'wildfire_analysis': self._get_members(grp, 'wildfire-analysis')
                }
                
                groups.append(group_obj)
        
        return groups
    
    def parse_zone_protection_profiles(self) -> List[Dict]:
        """Parse zone protection profiles"""
        profiles = []
        seen_names = set()
        
        paths = [
            ".//zone-protection-profile/entry",
            ".//device-group/entry/zone-protection-profile/entry",
            ".//network/profiles/zone-protection-profile/entry"
        ]
        
        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                prof_obj = {
                    'name': name,
                    'description': self._get_text(prof, 'description')
                }
                
                profiles.append(prof_obj)
        
        return profiles
    
    def parse_log_settings(self) -> List[Dict]:
        """Parse log forwarding profiles"""
        profiles = []
        seen_names = set()
        
        paths = [
            ".//log-settings/profiles/entry",
            ".//device-group/entry/log-settings/profiles/entry",
            ".//shared/log-settings/profiles/entry"
        ]
        
        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                prof_obj = {
                    'name': name,
                    'description': self._get_text(prof, 'description')
                }
                
                profiles.append(prof_obj)
        
        return profiles
    
    def parse_qos_profiles(self) -> List[Dict]:
        """Parse QoS profiles"""
        profiles = []
        seen_names = set()
        
        paths = [
            ".//qos/profile/entry",
            ".//device-group/entry/qos/profile/entry",
            ".//network/qos/profile/entry"
        ]
        
        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                prof_obj = {
                    'name': name,
                    'class_bandwidth_type': {}
                }
                
                # Parse class bandwidth settings
                for cls in prof.findall('.//class/entry'):
                    cls_name = cls.get('name')
                    if cls_name:
                        prof_obj['class_bandwidth_type'][cls_name] = {
                            'priority': self._get_text(cls, 'priority')
                        }
                
                profiles.append(prof_obj)
        
        return profiles
    
    def parse_tunnel_monitor_profiles(self) -> List[Dict]:
        """Parse tunnel monitor profiles"""
        profiles = []
        seen_names = set()
        
        paths = [
            ".//network/tunnel/global-protect-gateway/Default/tunnel-monitor/monitor-profile/entry",
            ".//network/tunnel-monitor/monitor-profile/entry",
            ".//devices/entry/network/tunnel-monitor/monitor-profile/entry"
        ]
        
        for path in paths:
            for prof in self.root.findall(path):
                name = prof.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                prof_obj = {
                    'name': name,
                    'interval': self._get_text(prof, 'interval'),
                    'threshold': self._get_text(prof, 'threshold'),
                    'action': self._get_text(prof, 'action')
                }
                
                profiles.append(prof_obj)
        
        return profiles
    
    def parse_bgp(self) -> Dict[str, Any]:
        """Parse BGP configuration"""
        bgp_config = {
            'enabled': False,
            'router_id': None,
            'as_number': None,
            'peer_groups': [],
            'peers': [],
            'redistribution_rules': []
        }
        
        paths = [
            ".//network/virtual-router/entry/protocol/bgp",
            ".//devices/entry/network/virtual-router/entry/protocol/bgp"
        ]
        
        for path in paths:
            for bgp in self.root.findall(path):
                if bgp.find('enable') is not None and bgp.find('enable').text == 'yes':
                    bgp_config['enabled'] = True
                    
                    # Router ID
                    router_id = bgp.find('router-id')
                    if router_id is not None:
                        bgp_config['router_id'] = router_id.text
                    
                    # AS Number
                    local_as = bgp.find('local-as')
                    if local_as is not None:
                        bgp_config['as_number'] = local_as.text
                    
                    # Peer Groups
                    for pg in bgp.findall('.//peer-group/entry'):
                        pg_name = pg.get('name')
                        if pg_name:
                            peer_group = {
                                'name': pg_name,
                                'type': self._get_text(pg, 'type'),
                                'export_nexthop': self._get_text(pg, 'export-nexthop'),
                                'import_nexthop': self._get_text(pg, 'import-nexthop')
                            }
                            bgp_config['peer_groups'].append(peer_group)
                    
                    # BGP Peers
                    for peer in bgp.findall('.//peer/entry'):
                        peer_name = peer.get('name')
                        if peer_name:
                            peer_config = {
                                'name': peer_name,
                                'peer_as': self._get_text(peer, 'peer-as'),
                                'local_address_interface': self._get_text(peer, 'local-address/interface'),
                                'local_address_ip': self._get_text(peer, 'local-address/ip'),
                                'peer_address_ip': self._get_text(peer, 'peer-address/ip'),
                                'enable': self._get_text(peer, 'enable') == 'yes',
                                'peer_group': self._get_text(peer, 'peer-group')
                            }
                            bgp_config['peers'].append(peer_config)
                    
                    # Redistribution rules
                    for redist in bgp.findall('.//redist-rules/entry'):
                        rule_name = redist.get('name')
                        if rule_name:
                            redist_rule = {
                                'name': rule_name,
                                'enable': self._get_text(redist, 'enable') == 'yes',
                                'address_family': self._get_text(redist, 'address-family-identifier')
                            }
                            bgp_config['redistribution_rules'].append(redist_rule)
        
        return bgp_config if bgp_config['enabled'] else None
    
    def parse_ospf(self) -> Dict[str, Any]:
        """Parse OSPF configuration"""
        ospf_config = {
            'enabled': False,
            'router_id': None,
            'areas': [],
            'interfaces': []
        }
        
        paths = [
            ".//network/virtual-router/entry/protocol/ospf",
            ".//devices/entry/network/virtual-router/entry/protocol/ospf"
        ]
        
        for path in paths:
            for ospf in self.root.findall(path):
                if ospf.find('enable') is not None and ospf.find('enable').text == 'yes':
                    ospf_config['enabled'] = True
                    
                    # Router ID
                    router_id = ospf.find('router-id')
                    if router_id is not None:
                        ospf_config['router_id'] = router_id.text
                    
                    # OSPF Areas
                    for area in ospf.findall('.//area/entry'):
                        area_id = area.get('name')
                        if area_id:
                            area_config = {
                                'area_id': area_id,
                                'type': 'normal'
                            }
                            
                            # Check for stub/nssa
                            if area.find('type/stub') is not None:
                                area_config['type'] = 'stub'
                            elif area.find('type/nssa') is not None:
                                area_config['type'] = 'nssa'
                            
                            # Area ranges
                            ranges = []
                            for range_entry in area.findall('.//range/entry'):
                                range_name = range_entry.get('name')
                                if range_name:
                                    ranges.append(range_name)
                            area_config['ranges'] = ranges
                            
                            ospf_config['areas'].append(area_config)
                    
                    # OSPF Interfaces
                    for iface in ospf.findall('.//interface/entry'):
                        iface_name = iface.get('name')
                        if iface_name:
                            iface_config = {
                                'interface': iface_name,
                                'enable': self._get_text(iface, 'enable') == 'yes',
                                'passive': self._get_text(iface, 'passive') == 'yes',
                                'link_type': self._get_text(iface, 'link-type'),
                                'metric': self._get_text(iface, 'metric')
                            }
                            ospf_config['interfaces'].append(iface_config)
        
        return ospf_config if ospf_config['enabled'] else None
    
    def parse_ipsec_tunnels(self) -> List[Dict]:
        """Parse IPsec VPN tunnel configurations"""
        tunnels = []
        seen_names = set()
        
        paths = [
            ".//network/tunnel/ipsec/entry",
            ".//devices/entry/network/tunnel/ipsec/entry"
        ]
        
        for path in paths:
            for tunnel in self.root.findall(path):
                name = tunnel.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                tunnel_config = {
                    'name': name,
                    'tunnel_interface': self._get_text(tunnel, 'tunnel-interface'),
                    'type': 'auto-key',  # Default
                    'peer_address': None,
                    'local_address': None,
                    'auth_type': None,
                    'preshared_key': None,
                    'ike_gateway': None,
                    'ipsec_crypto_profile': None
                }
                
                # Check for auto-key (most common)
                auto_key = tunnel.find('auto-key')
                if auto_key is not None:
                    tunnel_config['type'] = 'auto-key'
                    
                    # IKE Gateway
                    ike_gw = auto_key.find('ike-gateway/entry')
                    if ike_gw is not None:
                        tunnel_config['ike_gateway'] = ike_gw.get('name')
                    
                    # IPsec Crypto Profile
                    ipsec_profile = auto_key.find('ipsec-crypto-profile')
                    if ipsec_profile is not None:
                        tunnel_config['ipsec_crypto_profile'] = ipsec_profile.text
                    
                    # Proxy IDs
                    proxy_ids = []
                    for proxy in auto_key.findall('.//proxy-id/entry'):
                        proxy_name = proxy.get('name')
                        if proxy_name:
                            proxy_config = {
                                'name': proxy_name,
                                'local': self._get_text(proxy, 'local'),
                                'remote': self._get_text(proxy, 'remote'),
                                'protocol': self._get_text(proxy, 'protocol/number')
                            }
                            proxy_ids.append(proxy_config)
                    tunnel_config['proxy_ids'] = proxy_ids
                
                # Check for manual key
                manual_key = tunnel.find('manual-key')
                if manual_key is not None:
                    tunnel_config['type'] = 'manual-key'
                
                tunnels.append(tunnel_config)
        
        return tunnels
    
    def parse_ike_gateways(self) -> List[Dict]:
        """Parse IKE gateway configurations"""
        gateways = []
        seen_names = set()
        
        paths = [
            ".//network/ike/gateway/entry",
            ".//devices/entry/network/ike/gateway/entry"
        ]
        
        for path in paths:
            for gw in self.root.findall(path):
                name = gw.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                gateway_config = {
                    'name': name,
                    'version': 'ikev1',  # Default
                    'peer_address': None,
                    'local_address': None,
                    'pre_shared_key': '***CHANGE_ME***',  # Generic placeholder
                    'auth_type': 'pre-shared-key',
                    'ike_crypto_profile': None,
                    'local_id': None,
                    'peer_id': None
                }
                
                # Version
                protocol = gw.find('protocol')
                if protocol is not None:
                    if protocol.find('ikev1') is not None:
                        gateway_config['version'] = 'ikev1'
                    elif protocol.find('ikev2') is not None:
                        gateway_config['version'] = 'ikev2'
                    
                    # IKE Crypto Profile
                    version_node = protocol.find(gateway_config['version'])
                    if version_node is not None:
                        ike_profile = version_node.find('ike-crypto-profile')
                        if ike_profile is not None:
                            gateway_config['ike_crypto_profile'] = ike_profile.text
                
                # Peer address
                peer_addr = gw.find('.//peer-address/ip')
                if peer_addr is not None:
                    gateway_config['peer_address'] = peer_addr.text
                
                peer_fqdn = gw.find('.//peer-address/fqdn')
                if peer_fqdn is not None:
                    gateway_config['peer_address'] = peer_fqdn.text
                    gateway_config['peer_address_type'] = 'fqdn'
                
                # Local address
                local_addr = gw.find('.//local-address/ip')
                if local_addr is not None:
                    gateway_config['local_address'] = local_addr.text
                
                local_iface = gw.find('.//local-address/interface')
                if local_iface is not None:
                    gateway_config['local_address_interface'] = local_iface.text
                
                # Authentication
                auth = gw.find('authentication')
                if auth is not None:
                    # Check for pre-shared key (won't have actual value in export for security)
                    if auth.find('pre-shared-key') is not None:
                        gateway_config['auth_type'] = 'pre-shared-key'
                        # Note: Actual key not in export for security reasons
                        gateway_config['pre_shared_key'] = '***CHANGE_ME***'
                    elif auth.find('certificate') is not None:
                        gateway_config['auth_type'] = 'certificate'
                        cert = auth.find('certificate')
                        if cert is not None:
                            gateway_config['certificate_profile'] = self._get_text(cert, 'profile')
                
                # Local/Peer IDs
                gateway_config['local_id'] = self._get_text(gw, 'local-id/id')
                gateway_config['peer_id'] = self._get_text(gw, 'peer-id/id')
                
                gateways.append(gateway_config)
        
        return gateways
    
    def parse_ike_crypto_profiles(self) -> List[Dict]:
        """Parse IKE crypto profiles"""
        profiles = []
        seen_names = set()
        
        paths = [
            ".//network/ike/crypto-profiles/ike-crypto-profiles/entry",
            ".//devices/entry/network/ike/crypto-profiles/ike-crypto-profiles/entry"
        ]
        
        for path in paths:
            for profile in self.root.findall(path):
                name = profile.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                profile_config = {
                    'name': name,
                    'dh_groups': self._get_members(profile, 'dh-group'),
                    'authentications': self._get_members(profile, 'authentication'),
                    'encryptions': self._get_members(profile, 'encryption'),
                    'lifetime_hours': self._get_text(profile, 'lifetime/hours')
                }
                
                profiles.append(profile_config)
        
        return profiles
    
    def parse_ipsec_crypto_profiles(self) -> List[Dict]:
        """Parse IPsec crypto profiles"""
        profiles = []
        seen_names = set()
        
        paths = [
            ".//network/ike/crypto-profiles/ipsec-crypto-profiles/entry",
            ".//devices/entry/network/ike/crypto-profiles/ipsec-crypto-profiles/entry"
        ]
        
        for path in paths:
            for profile in self.root.findall(path):
                name = profile.get('name')
                if not name or name in seen_names:
                    continue
                
                seen_names.add(name)
                
                profile_config = {
                    'name': name,
                    'protocol': 'esp',  # Default
                    'encryptions': self._get_members(profile, 'esp/encryption'),
                    'authentications': self._get_members(profile, 'esp/authentication'),
                    'dh_group': self._get_text(profile, 'dh-group'),
                    'lifetime_hours': self._get_text(profile, 'lifetime/hours'),
                    'lifetime_kb': self._get_text(profile, 'lifetime/kilobytes')
                }
                
                # Check if AH is used instead of ESP
                if profile.find('ah') is not None:
                    profile_config['protocol'] = 'ah'
                    profile_config['authentications'] = self._get_members(profile, 'ah/authentication')
                
                profiles.append(profile_config)
        
        return profiles
    
    def _get_text(self, element: ET.Element, path: str) -> Optional[str]:
        """Safely get text from an XML element"""
        elem = element.find(path)
        return elem.text if elem is not None else None
    
    def _get_members(self, element: ET.Element, path: str) -> List[str]:
        """Get list of members from an XML element"""
        members = []
        for member in element.findall(f'.//{path}/member'):
            if member.text:
                members.append(member.text)
        return members


class TerraformGenerator:
    """Generate Terraform configuration files from Panorama data"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Terraform resource names"""
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f'_{sanitized}'
        return sanitized.lower()
    
    def escape_string(self, value: str) -> str:
        """Escape strings for Terraform"""
        if value is None:
            return '""'
        # Escape special characters
        value = value.replace('\\', '\\\\')
        value = value.replace('"', '\\"')
        value = value.replace('\n', '\\n')
        return f'"{value}"'
    
    def generate_provider_config(self):
        """Generate provider.tf file"""
        content = '''# Palo Alto Networks PAN-OS Provider Configuration
terraform {
  required_providers {
    panos = {
      source  = "PaloAltoNetworks/panos"
      version = "~> 2.0.7"
    }
  }
}

provider "panos" {
  # Configure these variables or use environment variables:
  # PANOS_HOSTNAME, PANOS_USERNAME, PANOS_PASSWORD
  # hostname = var.panos_hostname
  # username = var.panos_username
  # password = var.panos_password
}
'''
        
        with open(self.output_dir / 'provider.tf', 'w') as f:
            f.write(content)
    
    def generate_variables(self):
        """Generate variables.tf file"""
        content = '''# Variables for Palo Alto Configuration
variable "panos_hostname" {
  description = "Hostname or IP of the Palo Alto firewall/Panorama"
  type        = string
  sensitive   = true
}

variable "panos_username" {
  description = "Username for authentication"
  type        = string
  sensitive   = true
}

variable "panos_password" {
  description = "Password for authentication"
  type        = string
  sensitive   = true
}

variable "device_group" {
  description = "Device group name for Panorama"
  type        = string
  default     = "shared"
}
'''
        
        with open(self.output_dir / 'variables.tf', 'w') as f:
            f.write(content)
    
    def generate_address_objects(self, addresses: List[Dict]):
        """Generate address objects Terraform configuration"""
        if not addresses:
            return
        
        content = '# Address Objects\n\n'
        
        for addr in addresses:
            resource_name = self.sanitize_name(addr['name'])
            
            content += f'resource "panos_address_object" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(addr["name"])}\n'
            
            if addr.get('description'):
                content += f'  description = {self.escape_string(addr["description"])}\n'
            
            addr_type = addr.get('type', 'ip-netmask')
            value = addr.get('value', '')
            
            if addr_type == 'ip-netmask':
                content += f'  value = {self.escape_string(value)}\n'
            elif addr_type == 'ip-range':
                content += f'  type = "ip-range"\n'
                content += f'  value = {self.escape_string(value)}\n'
            elif addr_type == 'fqdn':
                content += f'  type = "fqdn"\n'
                content += f'  value = {self.escape_string(value)}\n'
            
            if addr.get('tags'):
                tags_str = ', '.join([self.escape_string(tag) for tag in addr['tags']])
                content += f'  tags = [{tags_str}]\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'address_objects.tf', 'w') as f:
            f.write(content)
    
    def generate_address_groups(self, groups: List[Dict]):
        """Generate address groups Terraform configuration"""
        if not groups:
            return
        
        content = '# Address Groups\n\n'
        
        for grp in groups:
            resource_name = self.sanitize_name(grp['name'])
            
            content += f'resource "panos_address_group" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(grp["name"])}\n'
            
            if grp.get('description'):
                content += f'  description = {self.escape_string(grp["description"])}\n'
            
            if grp.get('static_members'):
                members_str = ', '.join([self.escape_string(m) for m in grp['static_members']])
                content += f'  static_value = [{members_str}]\n'
            
            if grp.get('dynamic_filter'):
                content += f'  dynamic_value = {self.escape_string(grp["dynamic_filter"])}\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'address_groups.tf', 'w') as f:
            f.write(content)
    
    def generate_service_objects(self, services: List[Dict]):
        """Generate service objects Terraform configuration"""
        if not services:
            return
        
        content = '# Service Objects\n\n'
        
        for svc in services:
            resource_name = self.sanitize_name(svc['name'])
            
            content += f'resource "panos_service_object" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(svc["name"])}\n'
            
            if svc.get('description'):
                content += f'  description = {self.escape_string(svc["description"])}\n'
            
            protocol = svc.get('protocol', 'tcp')
            content += f'  protocol = {self.escape_string(protocol)}\n'
            
            if svc.get('port'):
                content += f'  destination_port = {self.escape_string(svc["port"])}\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'service_objects.tf', 'w') as f:
            f.write(content)
    
    def generate_service_groups(self, groups: List[Dict]):
        """Generate service groups Terraform configuration"""
        if not groups:
            return
        
        content = '# Service Groups\n\n'
        
        for grp in groups:
            resource_name = self.sanitize_name(grp['name'])
            
            content += f'resource "panos_service_group" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(grp["name"])}\n'
            
            if grp.get('description'):
                content += f'  description = {self.escape_string(grp["description"])}\n'
            
            if grp.get('members'):
                members_str = ', '.join([self.escape_string(m) for m in grp['members']])
                content += f'  services = [{members_str}]\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'service_groups.tf', 'w') as f:
            f.write(content)
    
    def generate_tags(self, tags: List[Dict]):
        """Generate tags Terraform configuration"""
        if not tags:
            return
        
        content = '# Tags\n\n'
        
        for tag in tags:
            resource_name = self.sanitize_name(tag['name'])
            
            content += f'resource "panos_administrative_tag" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(tag["name"])}\n'
            
            if tag.get('color'):
                content += f'  color = {self.escape_string(tag["color"])}\n'
            
            if tag.get('comments'):
                content += f'  comment = {self.escape_string(tag["comments"])}\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'tags.tf', 'w') as f:
            f.write(content)
    
    def generate_custom_url_categories(self, categories: List[Dict]):
        """Generate custom URL categories Terraform configuration"""
        if not categories:
            return
        
        content = '# Custom URL Categories\n\n'
        
        for cat in categories:
            resource_name = self.sanitize_name(cat['name'])
            
            content += f'resource "panos_custom_url_category" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(cat["name"])}\n'
            
            if cat.get('description'):
                content += f'  description = {self.escape_string(cat["description"])}\n'
            
            if cat.get('list'):
                # Split into sites
                sites_str = ', '.join([self.escape_string(url) for url in cat['list']])
                content += f'  sites = [{sites_str}]\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'custom_url_categories.tf', 'w') as f:
            f.write(content)
    
    def generate_application_groups(self, app_groups: List[Dict]):
        """Generate application groups Terraform configuration"""
        if not app_groups:
            return
        
        content = '# Application Groups\n\n'
        
        for ag in app_groups:
            resource_name = self.sanitize_name(ag['name'])
            
            content += f'resource "panos_application_group" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(ag["name"])}\n'
            
            if ag.get('members'):
                members_str = ', '.join([self.escape_string(m) for m in ag['members']])
                content += f'  applications = [{members_str}]\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'application_groups.tf', 'w') as f:
            f.write(content)
    
    def generate_application_filters(self, app_filters: List[Dict]):
        """Generate application filters Terraform configuration"""
        if not app_filters:
            return
        
        content = '# Application Filters\n'
        content += '# Note: Application filters may require manual configuration of all attributes\n\n'
        
        for af in app_filters:
            resource_name = self.sanitize_name(af['name'])
            
            content += f'resource "panos_application_filter" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(af["name"])}\n'
            
            if af.get('category'):
                cat_str = ', '.join([self.escape_string(c) for c in af['category']])
                content += f'  category = [{cat_str}]\n'
            
            if af.get('subcategory'):
                subcat_str = ', '.join([self.escape_string(s) for s in af['subcategory']])
                content += f'  subcategory = [{subcat_str}]\n'
            
            if af.get('technology'):
                tech_str = ', '.join([self.escape_string(t) for t in af['technology']])
                content += f'  technology = [{tech_str}]\n'
            
            if af.get('risk'):
                risk_str = ', '.join([self.escape_string(r) for r in af['risk']])
                content += f'  risk = [{risk_str}]\n'
            
            if af.get('evasive') == 'yes':
                content += f'  evasive = true\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'application_filters.tf', 'w') as f:
            f.write(content)
    
    def generate_external_lists(self, ext_lists: List[Dict]):
        """Generate external dynamic lists Terraform configuration"""
        if not ext_lists:
            return
        
        content = '# External Dynamic Lists\n\n'
        
        for ext_list in ext_lists:
            resource_name = self.sanitize_name(ext_list['name'])
            
            content += f'resource "panos_external_list" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(ext_list["name"])}\n'
            
            if ext_list.get('type'):
                content += f'  type = {self.escape_string(ext_list["type"])}\n'
            
            if ext_list.get('url'):
                content += f'  url = {self.escape_string(ext_list["url"])}\n'
            
            if ext_list.get('recurring'):
                content += f'  recurring = {self.escape_string(ext_list["recurring"])}\n'
            
            if ext_list.get('description'):
                content += f'  description = {self.escape_string(ext_list["description"])}\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'external_lists.tf', 'w') as f:
            f.write(content)
    
    def generate_schedules(self, schedules: List[Dict]):
        """Generate schedules Terraform configuration"""
        if not schedules:
            return
        
        content = '# Schedules\n'
        content += '# Note: Schedules require detailed recurring/non-recurring configuration\n'
        content += '# Manual configuration may be needed for complex schedules\n\n'
        
        for sched in schedules:
            resource_name = self.sanitize_name(sched['name'])
            
            content += f'# Schedule: {sched["name"]}\n'
            content += f'# Type: {sched.get("schedule_type", "unknown")}\n'
            content += f'# Manual Terraform configuration required\n\n'
        
        with open(self.output_dir / 'schedules.tf', 'w') as f:
            f.write(content)
    
    def generate_security_rules(self, rules: List[Dict]):
        """Generate security policy rules Terraform configuration"""
        if not rules:
            return
        
        content = '# Security Policy Rules\n\n'
        
        for idx, rule in enumerate(rules, start=1):
            resource_name = self.sanitize_name(rule['name'])
            
            content += f'resource "panos_security_rule_group" "{resource_name}" {{\n'
            content += f'  position_keyword = "bottom"\n\n'
            content += f'  rule {{\n'
            content += f'    name = {self.escape_string(rule["name"])}\n'
            
            if rule.get('description'):
                content += f'    description = {self.escape_string(rule["description"])}\n'
            
            if rule.get('source_zones'):
                zones_str = ', '.join([self.escape_string(z) for z in rule['source_zones']])
                content += f'    source_zones = [{zones_str}]\n'
            
            if rule.get('source_addresses'):
                addrs_str = ', '.join([self.escape_string(a) for a in rule['source_addresses']])
                content += f'    source_addresses = [{addrs_str}]\n'
            
            if rule.get('destination_zones'):
                zones_str = ', '.join([self.escape_string(z) for z in rule['destination_zones']])
                content += f'    destination_zones = [{zones_str}]\n'
            
            if rule.get('destination_addresses'):
                addrs_str = ', '.join([self.escape_string(a) for a in rule['destination_addresses']])
                content += f'    destination_addresses = [{addrs_str}]\n'
            
            if rule.get('applications'):
                apps_str = ', '.join([self.escape_string(a) for a in rule['applications']])
                content += f'    applications = [{apps_str}]\n'
            
            if rule.get('services'):
                svcs_str = ', '.join([self.escape_string(s) for s in rule['services']])
                content += f'    services = [{svcs_str}]\n'
            
            action = rule.get('action', 'allow')
            content += f'    action = {self.escape_string(action)}\n'
            
            if rule.get('log_start'):
                content += f'    log_start = true\n'
            
            if rule.get('log_end'):
                content += f'    log_end = true\n'
            
            if rule.get('disabled'):
                content += f'    disabled = true\n'
            
            content += '  }\n'
            content += '}\n\n'
        
        with open(self.output_dir / 'security_rules.tf', 'w') as f:
            f.write(content)
    
    def generate_nat_rules(self, rules: List[Dict]):
        """Generate NAT policy rules Terraform configuration"""
        if not rules:
            return
        
        content = '# NAT Policy Rules\n\n'
        
        for idx, rule in enumerate(rules, start=1):
            resource_name = self.sanitize_name(rule['name'])
            
            content += f'resource "panos_nat_rule_group" "{resource_name}" {{\n'
            content += f'  position_keyword = "bottom"\n\n'
            content += f'  rule {{\n'
            content += f'    name = {self.escape_string(rule["name"])}\n'
            
            if rule.get('description'):
                content += f'    description = {self.escape_string(rule["description"])}\n'
            
            if rule.get('source_zones'):
                zones_str = ', '.join([self.escape_string(z) for z in rule['source_zones']])
                content += f'    original_packet {{\n'
                content += f'      source_zones = [{zones_str}]\n'
            
            if rule.get('destination_zone'):
                content += f'      destination_zone = {self.escape_string(rule["destination_zone"])}\n'
            
            if rule.get('source_addresses'):
                addrs_str = ', '.join([self.escape_string(a) for a in rule['source_addresses']])
                content += f'      source_addresses = [{addrs_str}]\n'
            
            if rule.get('destination_addresses'):
                addrs_str = ', '.join([self.escape_string(a) for a in rule['destination_addresses']])
                content += f'      destination_addresses = [{addrs_str}]\n'
            
            if rule.get('service'):
                content += f'      service = {self.escape_string(rule["service"])}\n'
            
            content += f'    }}\n\n'
            
            # Source translation
            if rule.get('source_translation_type'):
                content += f'    source_translation {{\n'
                content += f'      type = {self.escape_string(rule["source_translation_type"])}\n'
                if rule.get('source_translation_address'):
                    addrs_str = ', '.join([self.escape_string(a) for a in rule['source_translation_address']])
                    content += f'      translated_addresses = [{addrs_str}]\n'
                content += f'    }}\n\n'
            
            # Destination translation
            if rule.get('destination_translation_address'):
                content += f'    destination_translation {{\n'
                content += f'      translated_address = {self.escape_string(rule["destination_translation_address"])}\n'
                if rule.get('destination_translation_port'):
                    content += f'      translated_port = {self.escape_string(rule["destination_translation_port"])}\n'
                content += f'    }}\n\n'
            
            if rule.get('disabled'):
                content += f'    disabled = true\n'
            
            content += '  }\n'
            content += '}\n\n'
        
        with open(self.output_dir / 'nat_rules.tf', 'w') as f:
            f.write(content)
    
    def generate_decryption_rules(self, rules: List[Dict]):
        """Generate decryption rules - placeholder for manual configuration"""
        if not rules:
            return
        
        content = '# Decryption Rules\n'
        content += '# Note: Decryption rules require detailed SSL/TLS configuration\n'
        content += '# Manual Terraform configuration is required\n\n'
        
        for rule in rules:
            content += f'# Rule: {rule["name"]}\n'
            content += f'#   Type: {rule.get("type", "unknown")}\n'
            content += f'#   Action: {rule.get("action", "unknown")}\n'
            content += f'#   Profile: {rule.get("profile", "none")}\n'
            if rule.get('description'):
                content += f'#   Description: {rule["description"]}\n'
            content += '\n'
        
        with open(self.output_dir / 'decryption_rules.tf', 'w') as f:
            f.write(content)
    
    def generate_pbf_rules(self, rules: List[Dict]):
        """Generate Policy-Based Forwarding rules - placeholder"""
        if not rules:
            return
        
        content = '# Policy-Based Forwarding Rules\n'
        content += '# Note: PBF rules require careful configuration with virtual routers\n'
        content += '# Manual Terraform configuration is required\n\n'
        
        for rule in rules:
            content += f'# Rule: {rule["name"]}\n'
            if rule.get('action'):
                action = rule['action']
                if action.get('type') == 'forward':
                    content += f'#   Action: Forward to {action.get("nexthop_ip")} via {action.get("egress_interface")}\n'
                else:
                    content += f'#   Action: {action.get("type")}\n'
            if rule.get('description'):
                content += f'#   Description: {rule["description"]}\n'
            content += '\n'
        
        with open(self.output_dir / 'pbf_rules.tf', 'w') as f:
            f.write(content)
    
    def generate_application_override_rules(self, rules: List[Dict]):
        """Generate application override rules - placeholder"""
        if not rules:
            return
        
        content = '# Application Override Rules\n'
        content += '# Note: Application override rules require manual configuration\n\n'
        
        for rule in rules:
            content += f'# Rule: {rule["name"]}\n'
            content += f'#   Protocol: {rule.get("protocol", "unknown")}\n'
            content += f'#   Port: {rule.get("port", "any")}\n'
            content += f'#   Application: {rule.get("application", "unknown")}\n'
            content += '\n'
        
        with open(self.output_dir / 'application_override_rules.tf', 'w') as f:
            f.write(content)
    
    def generate_zone_protection_profiles(self, profiles: List[Dict]):
        """Generate zone protection profiles - placeholder"""
        if not profiles:
            return
        
        content = '# Zone Protection Profiles\n'
        content += '# Note: Zone protection profiles require detailed configuration\n'
        content += '# Manual Terraform configuration is required\n\n'
        
        for prof in profiles:
            content += f'# Profile: {prof["name"]}\n'
            if prof.get('description'):
                content += f'#   Description: {prof["description"]}\n'
            content += '\n'
        
        with open(self.output_dir / 'zone_protection_profiles.tf', 'w') as f:
            f.write(content)
    
    def generate_log_settings(self, profiles: List[Dict]):
        """Generate log forwarding profiles - placeholder"""
        if not profiles:
            return
        
        content = '# Log Forwarding Profiles\n'
        content += '# Note: Log forwarding profiles require syslog/email configuration\n'
        content += '# Manual Terraform configuration is required\n\n'
        
        for prof in profiles:
            content += f'# Profile: {prof["name"]}\n'
            if prof.get('description'):
                content += f'#   Description: {prof["description"]}\n'
            content += '\n'
        
        with open(self.output_dir / 'log_settings.tf', 'w') as f:
            f.write(content)
    
    def generate_qos_profiles(self, profiles: List[Dict]):
        """Generate QoS profiles - placeholder"""
        if not profiles:
            return
        
        content = '# QoS Profiles\n'
        content += '# Note: QoS profiles require bandwidth and class configuration\n'
        content += '# Manual Terraform configuration is required\n\n'
        
        for prof in profiles:
            content += f'# Profile: {prof["name"]}\n'
            if prof.get('class_bandwidth_type'):
                content += f'#   Classes: {", ".join(prof["class_bandwidth_type"].keys())}\n'
            content += '\n'
        
        with open(self.output_dir / 'qos_profiles.tf', 'w') as f:
            f.write(content)
    
    def generate_tunnel_monitor_profiles(self, profiles: List[Dict]):
        """Generate tunnel monitor profiles - placeholder"""
        if not profiles:
            return
        
        content = '# Tunnel Monitor Profiles\n'
        content += '# Note: Tunnel monitor profiles require destination IP configuration\n'
        content += '# Manual Terraform configuration is required\n\n'
        
        for prof in profiles:
            content += f'# Profile: {prof["name"]}\n'
            content += f'#   Interval: {prof.get("interval", "unknown")}\n'
            content += f'#   Threshold: {prof.get("threshold", "unknown")}\n'
            content += f'#   Action: {prof.get("action", "unknown")}\n'
            content += '\n'
        
        with open(self.output_dir / 'tunnel_monitor_profiles.tf', 'w') as f:
            f.write(content)
    
    
    def generate_zones(self, zones: List[Dict]):
        """Generate zone Terraform configuration"""
        if not zones:
            return
        
        content = '# Zone Configurations\n\n'
        
        for zone in zones:
            resource_name = self.sanitize_name(zone['name'])
            
            content += f'resource "panos_zone" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(zone["name"])}\n'
            content += f'  mode = {self.escape_string(zone["type"])}\n'
            
            if zone.get('interfaces'):
                ifaces_str = ', '.join([self.escape_string(i) for i in zone['interfaces']])
                content += f'  interfaces = [{ifaces_str}]\n'
            
            if zone.get('zone_protection_profile'):
                content += f'  zone_protection_profile = {self.escape_string(zone["zone_protection_profile"])}\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'zones.tf', 'w') as f:
            f.write(content)
    
    def generate_virtual_routers(self, vrouters: List[Dict]):
        """Generate virtual/logical router Terraform configuration
        
        Supports both:
        - Virtual Routers (legacy routing engine)
        - Logical Routers (Advanced Routing Engine - PAN-OS 10.2+)
        """
        if not vrouters:
            return
        
        # Separate routers by type
        virtual_routers = [r for r in vrouters if r.get('router_type') != 'logical']
        logical_routers = [r for r in vrouters if r.get('router_type') == 'logical']
        
        content = '# Router Configurations\n'
        content += '# Supports both Virtual Routers (legacy) and Logical Routers (Advanced Routing Engine)\n\n'
        
        if logical_routers:
            content += f'# NOTE: Your config uses Advanced Routing Engine (PAN-OS 10.2+)\n'
            content += f'# - {len(virtual_routers)} Virtual Routers (legacy)\n'
            content += f'# - {len(logical_routers)} Logical Routers (advanced)\n'
            content += f'#\n'
            content += f'# Terraform provider panos supports both types.\n'
            content += f'# Virtual routers use: panos_virtual_router\n'
            content += f'# Logical routers use: panos_logical_router (if supported by provider version)\n'
            content += f'# Check: https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs\n\n'
        
        # Track resource names to handle duplicates
        resource_name_counts = {}
        
        for router in vrouters:
            # Generate base resource name
            base_resource_name = self.sanitize_name(router['name'])
            
            # If we've seen this name before, add a suffix
            if base_resource_name in resource_name_counts:
                resource_name_counts[base_resource_name] += 1
                resource_name = f"{base_resource_name}_{resource_name_counts[base_resource_name]}"
            else:
                resource_name_counts[base_resource_name] = 1
                resource_name = base_resource_name
            
            # Determine router type and resource type
            router_type = router.get('router_type', 'virtual')
            is_logical = router_type == 'logical'
            
            # Add comment showing source and type
            template = router.get('template', 'unknown')
            content += f'# Source: {template}\n'
            content += f'# Type: {"Logical Router (Advanced Routing Engine)" if is_logical else "Virtual Router (Legacy)"}\n'
            
            if is_logical:
                # Note: panos_logical_router may not exist in all provider versions
                # Users may need to use panos_virtual_router even for logical routers
                content += f'# NOTE: Terraform provider may use panos_virtual_router for logical routers\n'
                content += f'# Check provider documentation for logical router support\n'
                content += f'resource "panos_virtual_router" "{resource_name}" {{\n'
            else:
                content += f'resource "panos_virtual_router" "{resource_name}" {{\n'
            
            content += f'  name = {self.escape_string(router["name"])}\n'
            
            if router.get('interfaces'):
                ifaces_str = ', '.join([self.escape_string(i) for i in router['interfaces']])
                content += f'  interfaces = [{ifaces_str}]\n'
            
            content += '}\n\n'
            
            # Generate static routes
            if router.get('static_routes'):
                for route in router['static_routes']:
                    route_resource = self.sanitize_name(f"{resource_name}_{route['name']}")
                    
                    content += f'resource "panos_static_route_ipv4" "{route_resource}" {{\n'
                    content += f'  name = {self.escape_string(route["name"])}\n'
                    content += f'  virtual_router = panos_virtual_router.{resource_name}.name\n'
                    
                    if route.get('destination'):
                        content += f'  destination = {self.escape_string(route["destination"])}\n'
                    
                    if route.get('nexthop_ip'):
                        content += f'  next_hop = {self.escape_string(route["nexthop_ip"])}\n'
                    elif route.get('nexthop_interface'):
                        content += f'  interface = {self.escape_string(route["nexthop_interface"])}\n'
                    
                    if route.get('metric'):
                        content += f'  metric = {route["metric"]}\n'
                    
                    content += '}\n\n'
        
        with open(self.output_dir / 'virtual_routers.tf', 'w') as f:
            f.write(content)
    
    def generate_ethernet_interfaces(self, interfaces: List[Dict]):
        """Generate ethernet interface Terraform configuration"""
        if not interfaces:
            return
        
        content = '# Ethernet Interface Configurations\n'
        content += '# Note: These are reference configurations. Adjust for your hardware platform.\n\n'
        
        for iface in interfaces:
            if iface['type'] != 'ethernet':
                continue
            
            resource_name = self.sanitize_name(iface['name'])
            
            if iface['mode'] == 'layer3':
                content += f'resource "panos_ethernet_interface" "{resource_name}" {{\n'
                content += f'  name = {self.escape_string(iface["name"])}\n'
                content += f'  mode = "layer3"\n'
                
                if iface.get('comment'):
                    content += f'  comment = {self.escape_string(iface["comment"])}\n'
                
                if iface.get('ip_addresses'):
                    ips_str = ', '.join([self.escape_string(ip) for ip in iface['ip_addresses']])
                    content += f'  static_ips = [{ips_str}]\n'
                
                if iface.get('management_profile'):
                    content += f'  management_profile = {self.escape_string(iface["management_profile"])}\n'
                
                content += '}\n\n'
            
            elif iface['mode'] == 'layer2':
                content += f'resource "panos_layer2_subinterface" "{resource_name}" {{\n'
                content += f'  name = {self.escape_string(iface["name"])}\n'
                
                if iface.get('comment'):
                    content += f'  comment = {self.escape_string(iface["comment"])}\n'
                
                content += '}\n\n'
        
        with open(self.output_dir / 'interfaces.tf', 'w') as f:
            f.write(content)
    
    def generate_interface_report(self, interfaces: List[Dict]):
        """Generate a text report of interfaces and their IP addresses"""
        if not interfaces:
            return
        
        content = '=' * 80 + '\n'
        content += 'INTERFACE AND IP ADDRESS MIGRATION REPORT\n'
        content += 'Generated for Firewall Migration Planning\n'
        content += '=' * 80 + '\n\n'
        
        content += 'This report lists all interfaces and their assigned IP addresses from the\n'
        content += 'source configuration. Use this to plan interface mapping for the new platform.\n\n'
        
        content += '=' * 80 + '\n'
        content += 'INTERFACE SUMMARY\n'
        content += '=' * 80 + '\n\n'
        
        # Group by type
        by_type = {}
        for iface in interfaces:
            iface_type = iface['type']
            if iface_type not in by_type:
                by_type[iface_type] = []
            by_type[iface_type].append(iface)
        
        for iface_type, iface_list in sorted(by_type.items()):
            content += f'\n{iface_type.upper()} INTERFACES ({len(iface_list)})\n'
            content += '-' * 80 + '\n'
            
            for iface in sorted(iface_list, key=lambda x: x['name']):
                content += f'\nInterface: {iface["name"]}\n'
                content += f'  Type: {iface["type"]}\n'
                content += f'  Mode: {iface["mode"]}\n'
                
                if iface.get('comment'):
                    content += f'  Comment: {iface["comment"]}\n'
                
                if iface.get('ip_addresses'):
                    content += f'  IPv4 Addresses:\n'
                    for ip in iface['ip_addresses']:
                        content += f'    - {ip}\n'
                
                if iface.get('ipv6_addresses'):
                    content += f'  IPv6 Addresses:\n'
                    for ip in iface['ipv6_addresses']:
                        content += f'    - {ip}\n'
                
                if iface.get('management_profile'):
                    content += f'  Management Profile: {iface["management_profile"]}\n'
                
                if iface.get('tag'):
                    content += f'  VLAN Tag: {iface["tag"]}\n'
        
        content += '\n' + '=' * 80 + '\n'
        content += 'MIGRATION CHECKLIST\n'
        content += '=' * 80 + '\n\n'
        
        content += '1. Review interface naming differences between platforms\n'
        content += '2. Map source interfaces to target platform interfaces\n'
        content += '3. Verify IP addressing scheme is compatible\n'
        content += '4. Check for interface-specific features that may not translate\n'
        content += '5. Update zone and virtual router configurations accordingly\n'
        content += '6. Test connectivity after migration\n\n'
        
        content += '=' * 80 + '\n'
        content += 'PLATFORM MIGRATION NOTES\n'
        content += '=' * 80 + '\n\n'
        
        content += 'Common Interface Naming Patterns:\n\n'
        content += '  PA-200/500 Series:    ethernet1/1 - ethernet1/8\n'
        content += '  PA-800 Series:        ethernet1/1 - ethernet1/8\n'
        content += '  PA-3000 Series:       ethernet1/1 - ethernet1/20+\n'
        content += '  PA-5000 Series:       ethernet1/1 - ethernet1/24+\n'
        content += '  PA-7000 Series:       ethernet1/1 - ethernet1/48+ (per slot)\n'
        content += '  VM-Series:            ethernet1/1 - ethernet1/X (configurable)\n\n'
        
        content += 'Remember:\n'
        content += '  - Management interface naming varies by platform\n'
        content += '  - Some platforms support additional interface types (QSFP, SFP+, etc.)\n'
        content += '  - Aggregate interfaces may have different limitations\n'
        content += '  - Verify transceiver compatibility for the new platform\n\n'
        
        with open(self.output_dir / 'INTERFACE_MIGRATION_REPORT.txt', 'w') as f:
            f.write(content)
    
    def generate_security_profiles(self, profiles: Dict[str, List[Dict]]):
        """Generate security profile Terraform configuration"""
        if not any(profiles.values()):
            return
        
        content = '# Security Profiles\n'
        content += '# Note: These are simplified profile references.\n'
        content += '# Detailed profile rules must be configured manually or imported.\n\n'
        
        # Note: Full profile configuration with all rules is complex
        # This generates basic profile declarations that can be enhanced
        
        # Antivirus profiles
        if profiles.get('antivirus'):
            content += '# Antivirus Profiles\n'
            for prof in profiles['antivirus']:
                resource_name = self.sanitize_name(prof['name'])
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_antivirus_security_profile.{resource_name}\n\n'
        
        # Vulnerability profiles
        if profiles.get('vulnerability'):
            content += '# Vulnerability Protection Profiles\n'
            for prof in profiles['vulnerability']:
                resource_name = self.sanitize_name(prof['name'])
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_vulnerability_security_profile.{resource_name}\n\n'
        
        # Anti-spyware profiles
        if profiles.get('anti_spyware'):
            content += '# Anti-Spyware Profiles\n'
            for prof in profiles['anti_spyware']:
                resource_name = self.sanitize_name(prof['name'])
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_anti_spyware_security_profile.{resource_name}\n\n'
        
        # URL filtering profiles  
        if profiles.get('url_filtering'):
            content += '# URL Filtering Profiles\n'
            for prof in profiles['url_filtering']:
                resource_name = self.sanitize_name(prof['name'])
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_url_filtering_security_profile.{resource_name}\n\n'
        
        # File blocking profiles
        if profiles.get('file_blocking'):
            content += '# File Blocking Profiles\n'
            for prof in profiles['file_blocking']:
                resource_name = self.sanitize_name(prof['name'])
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_file_blocking_security_profile.{resource_name}\n\n'
        
        # WildFire profiles
        if profiles.get('wildfire_analysis'):
            content += '# WildFire Analysis Profiles\n'
            for prof in profiles['wildfire_analysis']:
                resource_name = self.sanitize_name(prof['name'])
                content += f'# Profile: {prof["name"]}\n'
                if prof.get('description'):
                    content += f'# Description: {prof["description"]}\n'
                content += f'# Resource: panos_wildfire_analysis_security_profile.{resource_name}\n\n'
        
        with open(self.output_dir / 'security_profiles.tf', 'w') as f:
            f.write(content)
    
    def generate_security_profile_groups(self, groups: List[Dict]):
        """Generate security profile group Terraform configuration"""
        if not groups:
            return
        
        content = '# Security Profile Groups\n\n'
        
        for grp in groups:
            resource_name = self.sanitize_name(grp['name'])
            
            content += f'resource "panos_security_profile_group" "{resource_name}" {{\n'
            content += f'  name = {self.escape_string(grp["name"])}\n'
            
            if grp.get('virus') and grp['virus']:
                content += f'  virus = {self.escape_string(grp["virus"][0])}\n'
            
            if grp.get('spyware') and grp['spyware']:
                content += f'  spyware = {self.escape_string(grp["spyware"][0])}\n'
            
            if grp.get('vulnerability') and grp['vulnerability']:
                content += f'  vulnerability = {self.escape_string(grp["vulnerability"][0])}\n'
            
            if grp.get('url_filtering') and grp['url_filtering']:
                content += f'  url_filtering = {self.escape_string(grp["url_filtering"][0])}\n'
            
            if grp.get('file_blocking') and grp['file_blocking']:
                content += f'  file_blocking = {self.escape_string(grp["file_blocking"][0])}\n'
            
            if grp.get('wildfire_analysis') and grp['wildfire_analysis']:
                content += f'  wildfire_analysis = {self.escape_string(grp["wildfire_analysis"][0])}\n'
            
            content += '}\n\n'
        
        with open(self.output_dir / 'security_profile_groups.tf', 'w') as f:
            f.write(content)
    
    
    def generate_bgp_config(self, bgp_config: Dict[str, Any]):
        """Generate BGP Terraform configuration"""
        if not bgp_config:
            return
        
        content = '# BGP Configuration\n'
        content += '# Note: BGP configuration requires careful validation.\n'
        content += '# Verify all peer addresses and AS numbers before applying.\n\n'
        
        content += f'resource "panos_bgp" "default" {{\n'
        content += f'  virtual_router = panos_virtual_router.default.name\n'
        content += f'  enable = true\n'
        
        if bgp_config.get('router_id'):
            content += f'  router_id = {self.escape_string(bgp_config["router_id"])}\n'
        
        if bgp_config.get('as_number'):
            content += f'  as_number = {self.escape_string(bgp_config["as_number"])}\n'
        
        content += '}\n\n'
        
        # BGP Peer Groups
        for pg in bgp_config.get('peer_groups', []):
            resource_name = self.sanitize_name(f"pg_{pg['name']}")
            content += f'resource "panos_bgp_peer_group" "{resource_name}" {{\n'
            content += f'  virtual_router = panos_virtual_router.default.name\n'
            content += f'  name = {self.escape_string(pg["name"])}\n'
            
            if pg.get('type'):
                content += f'  type = {self.escape_string(pg["type"])}\n'
            
            content += f'  depends_on = [panos_bgp.default]\n'
            content += '}\n\n'
        
        # BGP Peers
        for peer in bgp_config.get('peers', []):
            resource_name = self.sanitize_name(f"peer_{peer['name']}")
            content += f'resource "panos_bgp_peer" "{resource_name}" {{\n'
            content += f'  virtual_router = panos_virtual_router.default.name\n'
            content += f'  bgp_peer_group = {self.escape_string(peer.get("peer_group", ""))}\n'
            content += f'  name = {self.escape_string(peer["name"])}\n'
            content += f'  enable = {str(peer.get("enable", True)).lower()}\n'
            
            if peer.get('peer_as'):
                content += f'  peer_as = {self.escape_string(peer["peer_as"])}\n'
            
            if peer.get('local_address_interface'):
                content += f'  local_address_interface = {self.escape_string(peer["local_address_interface"])}\n'
            
            if peer.get('local_address_ip'):
                content += f'  local_address_ip = {self.escape_string(peer["local_address_ip"])}\n'
            
            if peer.get('peer_address_ip'):
                content += f'  peer_address_ip = {self.escape_string(peer["peer_address_ip"])}\n'
            
            content += f'  depends_on = [panos_bgp.default]\n'
            content += '}\n\n'
        
        with open(self.output_dir / 'bgp.tf', 'w') as f:
            f.write(content)
    
    def generate_ospf_config(self, ospf_config: Dict[str, Any]):
        """Generate OSPF Terraform configuration"""
        if not ospf_config:
            return
        
        content = '# OSPF Configuration\n'
        content += '# Note: OSPF configuration requires careful validation.\n'
        content += '# Verify all area configurations and interface assignments.\n\n'
        
        content += f'resource "panos_ospf" "default" {{\n'
        content += f'  virtual_router = panos_virtual_router.default.name\n'
        content += f'  enable = true\n'
        
        if ospf_config.get('router_id'):
            content += f'  router_id = {self.escape_string(ospf_config["router_id"])}\n'
        
        content += '}\n\n'
        
        # OSPF Areas
        for area in ospf_config.get('areas', []):
            resource_name = self.sanitize_name(f"area_{area['area_id']}")
            content += f'resource "panos_ospf_area" "{resource_name}" {{\n'
            content += f'  virtual_router = panos_virtual_router.default.name\n'
            content += f'  name = {self.escape_string(area["area_id"])}\n'
            
            if area['type'] != 'normal':
                content += f'  type = {self.escape_string(area["type"])}\n'
            
            content += f'  depends_on = [panos_ospf.default]\n'
            content += '}\n\n'
        
        # OSPF Interfaces
        for iface in ospf_config.get('interfaces', []):
            resource_name = self.sanitize_name(f"ospf_{iface['interface']}")
            content += f'resource "panos_ospf_area_interface" "{resource_name}" {{\n'
            content += f'  virtual_router = panos_virtual_router.default.name\n'
            content += f'  ospf_area = "0.0.0.0"  # Adjust to correct area\n'
            content += f'  name = {self.escape_string(iface["interface"])}\n'
            content += f'  enable = {str(iface.get("enable", True)).lower()}\n'
            
            if iface.get('passive'):
                content += f'  passive = true\n'
            
            if iface.get('metric'):
                content += f'  metric = {iface["metric"]}\n'
            
            content += f'  depends_on = [panos_ospf.default]\n'
            content += '}\n\n'
        
        with open(self.output_dir / 'ospf.tf', 'w') as f:
            f.write(content)
    
    def generate_vpn_config(self, ike_gateways: List[Dict], ipsec_tunnels: List[Dict], 
                           ike_profiles: List[Dict], ipsec_profiles: List[Dict]):
        """Generate VPN Terraform configuration"""
        if not (ike_gateways or ipsec_tunnels):
            return
        
        content = '# IPsec VPN Configuration\n'
        content += '# IMPORTANT: Pre-shared keys are set to generic placeholders.\n'
        content += '# You MUST update all pre-shared keys before applying!\n'
        content += '# Search for "***CHANGE_ME***" and replace with actual keys.\n\n'
        
        # IKE Crypto Profiles
        if ike_profiles:
            content += '# IKE Crypto Profiles\n\n'
            for profile in ike_profiles:
                resource_name = self.sanitize_name(f"ike_profile_{profile['name']}")
                content += f'resource "panos_ike_crypto_profile" "{resource_name}" {{\n'
                content += f'  name = {self.escape_string(profile["name"])}\n'
                
                if profile.get('dh_groups'):
                    dh_str = ', '.join([self.escape_string(dh) for dh in profile['dh_groups']])
                    content += f'  dh_groups = [{dh_str}]\n'
                
                if profile.get('authentications'):
                    auth_str = ', '.join([self.escape_string(a) for a in profile['authentications']])
                    content += f'  authentications = [{auth_str}]\n'
                
                if profile.get('encryptions'):
                    enc_str = ', '.join([self.escape_string(e) for e in profile['encryptions']])
                    content += f'  encryptions = [{enc_str}]\n'
                
                if profile.get('lifetime_hours'):
                    content += f'  lifetime_hours = {profile["lifetime_hours"]}\n'
                
                content += '}\n\n'
        
        # IPsec Crypto Profiles
        if ipsec_profiles:
            content += '# IPsec Crypto Profiles\n\n'
            for profile in ipsec_profiles:
                resource_name = self.sanitize_name(f"ipsec_profile_{profile['name']}")
                content += f'resource "panos_ipsec_crypto_profile" "{resource_name}" {{\n'
                content += f'  name = {self.escape_string(profile["name"])}\n'
                content += f'  protocol = {self.escape_string(profile.get("protocol", "esp"))}\n'
                
                if profile.get('encryptions'):
                    enc_str = ', '.join([self.escape_string(e) for e in profile['encryptions']])
                    content += f'  encryptions = [{enc_str}]\n'
                
                if profile.get('authentications'):
                    auth_str = ', '.join([self.escape_string(a) for a in profile['authentications']])
                    content += f'  authentications = [{auth_str}]\n'
                
                if profile.get('dh_group'):
                    content += f'  dh_group = {self.escape_string(profile["dh_group"])}\n'
                
                if profile.get('lifetime_hours'):
                    content += f'  lifetime_hours = {profile["lifetime_hours"]}\n'
                
                content += '}\n\n'
        
        # IKE Gateways
        if ike_gateways:
            content += '# IKE Gateways\n'
            content += '# WARNING: Pre-shared keys use placeholder "***CHANGE_ME***"\n'
            content += '# Update these with actual keys from your key management system!\n\n'
            
            for gw in ike_gateways:
                resource_name = self.sanitize_name(f"ike_gw_{gw['name']}")
                content += f'resource "panos_ike_gateway" "{resource_name}" {{\n'
                content += f'  name = {self.escape_string(gw["name"])}\n'
                content += f'  version = {self.escape_string(gw.get("version", "ikev1"))}\n'
                
                if gw.get('peer_address'):
                    if gw.get('peer_address_type') == 'fqdn':
                        content += f'  peer_address_type = "fqdn"\n'
                        content += f'  peer_address_value = {self.escape_string(gw["peer_address"])}\n'
                    else:
                        content += f'  peer_address_type = "ip"\n'
                        content += f'  peer_address_value = {self.escape_string(gw["peer_address"])}\n'
                
                if gw.get('local_address_interface'):
                    content += f'  interface = {self.escape_string(gw["local_address_interface"])}\n'
                elif gw.get('local_address'):
                    content += f'  local_address_value = {self.escape_string(gw["local_address"])}\n'
                
                content += f'  auth_type = {self.escape_string(gw.get("auth_type", "pre-shared-key"))}\n'
                
                if gw.get('auth_type') == 'pre-shared-key':
                    # Use placeholder - actual key not in export for security
                    content += f'  pre_shared_key = {self.escape_string(gw["pre_shared_key"])}  # *** CHANGE THIS KEY ***\n'
                
                if gw.get('ike_crypto_profile'):
                    profile_ref = self.sanitize_name(f"ike_profile_{gw['ike_crypto_profile']}")
                    content += f'  ike_crypto_profile = panos_ike_crypto_profile.{profile_ref}.name\n'
                
                if gw.get('local_id'):
                    content += f'  local_id_type = "ufqdn"\n'
                    content += f'  local_id_value = {self.escape_string(gw["local_id"])}\n'
                
                if gw.get('peer_id'):
                    content += f'  peer_id_type = "ufqdn"\n'
                    content += f'  peer_id_value = {self.escape_string(gw["peer_id"])}\n'
                
                content += '}\n\n'
        
        # IPsec Tunnels
        if ipsec_tunnels:
            content += '# IPsec Tunnels\n\n'
            for tunnel in ipsec_tunnels:
                resource_name = self.sanitize_name(f"tunnel_{tunnel['name']}")
                content += f'resource "panos_ipsec_tunnel" "{resource_name}" {{\n'
                content += f'  name = {self.escape_string(tunnel["name"])}\n'
                
                if tunnel.get('tunnel_interface'):
                    content += f'  tunnel_interface = {self.escape_string(tunnel["tunnel_interface"])}\n'
                
                if tunnel.get('type') == 'auto-key':
                    content += f'  type = "auto-key"\n'
                    
                    if tunnel.get('ike_gateway'):
                        gw_ref = self.sanitize_name(f"ike_gw_{tunnel['ike_gateway']}")
                        content += f'  ak_ike_gateway = panos_ike_gateway.{gw_ref}.name\n'
                    
                    if tunnel.get('ipsec_crypto_profile'):
                        profile_ref = self.sanitize_name(f"ipsec_profile_{tunnel['ipsec_crypto_profile']}")
                        content += f'  ak_ipsec_crypto_profile = panos_ipsec_crypto_profile.{profile_ref}.name\n'
                
                content += '}\n\n'
                
                # Proxy IDs
                for proxy in tunnel.get('proxy_ids', []):
                    proxy_resource = self.sanitize_name(f"proxy_{tunnel['name']}_{proxy['name']}")
                    content += f'resource "panos_ipsec_tunnel_proxy_id_ipv4" "{proxy_resource}" {{\n'
                    content += f'  ipsec_tunnel = panos_ipsec_tunnel.{resource_name}.name\n'
                    content += f'  name = {self.escape_string(proxy["name"])}\n'
                    
                    if proxy.get('local'):
                        content += f'  local = {self.escape_string(proxy["local"])}\n'
                    
                    if proxy.get('remote'):
                        content += f'  remote = {self.escape_string(proxy["remote"])}\n'
                    
                    if proxy.get('protocol'):
                        content += f'  protocol_number = {proxy["protocol"]}\n'
                    
                    content += '}\n\n'
        
        with open(self.output_dir / 'vpn.tf', 'w') as f:
            f.write(content)
    
    def generate_vpn_report(self, ike_gateways: List[Dict], ipsec_tunnels: List[Dict]):
        """Generate VPN migration report with key management instructions"""
        if not (ike_gateways or ipsec_tunnels):
            return
        
        content = '=' * 80 + '\n'
        content += 'VPN CONFIGURATION MIGRATION REPORT\n'
        content += '=' * 80 + '\n\n'
        
        content += '⚠️  CRITICAL: PRE-SHARED KEY MANAGEMENT\n\n'
        content += 'Pre-shared keys are NOT included in Panorama exports for security reasons.\n'
        content += 'All VPN configurations use placeholder keys: ***CHANGE_ME***\n\n'
        content += 'REQUIRED ACTIONS:\n'
        content += '1. Retrieve actual pre-shared keys from your secure key management system\n'
        content += '2. Update vpn.tf file with real keys before applying\n'
        content += '3. Consider using Terraform variables or secrets management\n'
        content += '4. Never commit actual keys to version control\n\n'
        
        content += '=' * 80 + '\n'
        content += 'IKE GATEWAYS\n'
        content += '=' * 80 + '\n\n'
        
        for gw in ike_gateways:
            content += f'Gateway: {gw["name"]}\n'
            content += f'  Version: {gw.get("version", "ikev1")}\n'
            content += f'  Peer Address: {gw.get("peer_address", "N/A")}\n'
            content += f'  Local Address: {gw.get("local_address") or gw.get("local_address_interface", "N/A")}\n'
            content += f'  Auth Type: {gw.get("auth_type", "pre-shared-key")}\n'
            
            if gw.get('auth_type') == 'pre-shared-key':
                content += f'  ⚠️  Pre-Shared Key: ***MUST BE UPDATED***\n'
                content += f'     Current placeholder: ***CHANGE_ME***\n'
                content += f'     Action: Replace with actual key in vpn.tf\n'
            
            content += f'  IKE Crypto Profile: {gw.get("ike_crypto_profile", "N/A")}\n'
            content += '\n'
        
        content += '=' * 80 + '\n'
        content += 'IPSEC TUNNELS\n'
        content += '=' * 80 + '\n\n'
        
        for tunnel in ipsec_tunnels:
            content += f'Tunnel: {tunnel["name"]}\n'
            content += f'  Type: {tunnel.get("type", "auto-key")}\n'
            content += f'  Tunnel Interface: {tunnel.get("tunnel_interface", "N/A")}\n'
            content += f'  IKE Gateway: {tunnel.get("ike_gateway", "N/A")}\n'
            content += f'  IPsec Crypto Profile: {tunnel.get("ipsec_crypto_profile", "N/A")}\n'
            
            if tunnel.get('proxy_ids'):
                content += f'  Proxy IDs:\n'
                for proxy in tunnel['proxy_ids']:
                    content += f'    - {proxy["name"]}: {proxy.get("local", "any")} <-> {proxy.get("remote", "any")}\n'
            
            content += '\n'
        
        content += '=' * 80 + '\n'
        content += 'KEY MANAGEMENT BEST PRACTICES\n'
        content += '=' * 80 + '\n\n'
        
        content += 'Option 1: Terraform Variables (Recommended)\n'
        content += '-' * 40 + '\n'
        content += 'Create terraform.tfvars (DO NOT COMMIT):\n'
        content += '  vpn_psk_gateway1 = "actual-pre-shared-key-here"\n'
        content += '  vpn_psk_gateway2 = "actual-pre-shared-key-here"\n\n'
        
        content += 'Update vpn.tf:\n'
        content += '  pre_shared_key = var.vpn_psk_gateway1\n\n'
        
        content += 'Option 2: Environment Variables\n'
        content += '-' * 40 + '\n'
        content += 'Set environment variables:\n'
        content += '  export TF_VAR_vpn_psk_gateway1="actual-key"\n\n'
        
        content += 'Option 3: Secrets Management\n'
        content += '-' * 40 + '\n'
        content += 'Use HashiCorp Vault, AWS Secrets Manager, or similar:\n'
        content += '  data "vault_generic_secret" "vpn_keys" {\n'
        content += '    path = "secret/vpn-keys"\n'
        content += '  }\n\n'
        
        content += 'Option 4: Manual Entry (Least Secure)\n'
        content += '-' * 40 + '\n'
        content += 'Directly in vpn.tf (NOT RECOMMENDED):\n'
        content += '  pre_shared_key = "actual-key"  # DO NOT COMMIT TO GIT\n\n'
        
        content += '=' * 80 + '\n'
        content += 'MIGRATION CHECKLIST\n'
        content += '=' * 80 + '\n\n'
        
        content += '[ ] Retrieve all VPN pre-shared keys from secure storage\n'
        content += '[ ] Update vpn.tf with actual keys (use variables/secrets)\n'
        content += '[ ] Verify IKE gateway peer addresses\n'
        content += '[ ] Confirm tunnel interface assignments\n'
        content += '[ ] Check proxy ID configurations\n'
        content += '[ ] Validate crypto profile settings\n'
        content += '[ ] Test VPN connectivity in lab\n'
        content += '[ ] Verify routing through tunnels\n'
        content += '[ ] Monitor Phase 1 and Phase 2 negotiations\n'
        content += '[ ] Ensure .gitignore includes terraform.tfvars\n\n'
        
        content += '=' * 80 + '\n'
        content += 'IMPORTANT SECURITY NOTES\n'
        content += '=' * 80 + '\n\n'
        
        content += '1. Never commit pre-shared keys to version control\n'
        content += '2. Use .gitignore to exclude terraform.tfvars and *.auto.tfvars\n'
        content += '3. Rotate keys regularly according to security policy\n'
        content += '4. Use strong, unique keys for each VPN tunnel\n'
        content += '5. Consider using certificate-based authentication\n'
        content += '6. Implement proper key escrow and recovery procedures\n'
        content += '7. Audit key access and usage\n\n'
        
        with open(self.output_dir / 'VPN_MIGRATION_REPORT.txt', 'w') as f:
            f.write(content)
    
    def generate_readme(self):
        """Generate README with usage instructions"""
        content = '''# Palo Alto Terraform Configuration

This directory contains Terraform configuration files generated from Palo Alto Panorama export.

## Prerequisites

1. Install Terraform (>= 1.0)
2. Install the Palo Alto Networks PAN-OS provider

## Configuration

1. Set up authentication variables in `terraform.tfvars`:

```hcl
panos_hostname = "your-panorama-hostname-or-ip"
panos_username = "admin"
panos_password = "your-password"
device_group   = "your-device-group"
```

Or use environment variables:
```bash
export PANOS_HOSTNAME="your-panorama-hostname-or-ip"
export PANOS_USERNAME="admin"
export PANOS_PASSWORD="your-password"
```

2. Initialize Terraform:
```bash
terraform init
```

3. Review the plan:
```bash
terraform plan
```

4. Apply the configuration:
```bash
terraform apply
```

## File Structure

- `provider.tf` - Provider configuration
- `variables.tf` - Variable definitions
- `address_objects.tf` - Address object configurations
- `address_groups.tf` - Address group configurations
- `service_objects.tf` - Service object configurations
- `service_groups.tf` - Service group configurations
- `security_rules.tf` - Security policy rules
- `nat_rules.tf` - NAT policy rules

## Important Notes

- Review all configurations before applying
- Test in a non-production environment first
- Back up your existing configuration
- Adjust rule ordering as needed
- Some features may require manual adjustment

## Provider Documentation

For more information on the PAN-OS Terraform provider:
https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs
'''
        
        with open(self.output_dir / 'README.md', 'w') as f:
            f.write(content)


def main():
    parser = argparse.ArgumentParser(
        description='Convert Palo Alto Panorama XML output to Terraform configuration'
    )
    parser.add_argument(
        'input_file',
        help='Input XML file from Panorama'
    )
    parser.add_argument(
        '--output-dir',
        default='terraform_output',
        help='Output directory for Terraform files (default: terraform_output)'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1
    
    try:
        print(f"Parsing Panorama configuration from {args.input_file}...")
        panorama = PanoramaParser(args.input_file)
        
        print("Extracting configuration elements...")
        device_groups = panorama.parse_device_groups()
        
        # New: Tags and Regions
        tags = panorama.parse_tags()
        regions = panorama.parse_regions()
        
        # New: URL and Application objects
        custom_url_categories = panorama.parse_custom_url_categories()
        application_groups = panorama.parse_application_groups()
        application_filters = panorama.parse_application_filters()
        external_lists = panorama.parse_external_lists()
        schedules = panorama.parse_schedules()
        
        # Address and Service objects
        addresses = panorama.parse_address_objects()
        address_groups = panorama.parse_address_groups()
        services = panorama.parse_service_objects()
        service_groups = panorama.parse_service_groups()
        
        # Rules
        security_rules = panorama.parse_security_rules()
        nat_rules = panorama.parse_nat_rules()
        decryption_rules = panorama.parse_decryption_rules()
        pbf_rules = panorama.parse_pbf_rules()
        app_override_rules = panorama.parse_application_override_rules()
        
        # Network
        zones = panorama.parse_zones()
        interfaces = panorama.parse_interfaces()
        virtual_routers = panorama.parse_virtual_routers()
        logical_routers = panorama.parse_logical_routers()  # Advanced Routing Engine
        
        # Combine virtual and logical routers for unified handling
        all_routers = virtual_routers + logical_routers
        
        # Security Profiles
        security_profiles = panorama.parse_security_profiles()
        security_profile_groups = panorama.parse_security_profile_groups()
        zone_protection_profiles = panorama.parse_zone_protection_profiles()
        log_settings = panorama.parse_log_settings()
        qos_profiles = panorama.parse_qos_profiles()
        tunnel_monitor_profiles = panorama.parse_tunnel_monitor_profiles()
        
        # Dynamic routing
        bgp_config = panorama.parse_bgp()
        ospf_config = panorama.parse_ospf()
        
        # VPN configurations
        ike_gateways = panorama.parse_ike_gateways()
        ipsec_tunnels = panorama.parse_ipsec_tunnels()
        ike_crypto_profiles = panorama.parse_ike_crypto_profiles()
        ipsec_crypto_profiles = panorama.parse_ipsec_crypto_profiles()
        
        print(f"\nFound:")
        print(f"  - {len(device_groups)} device groups")
        print(f"  - {len(tags)} tags")
        print(f"  - {len(regions)} regions")
        print(f"  - {len(custom_url_categories)} custom URL categories")
        print(f"  - {len(application_groups)} application groups")
        print(f"  - {len(application_filters)} application filters")
        print(f"  - {len(external_lists)} external lists")
        print(f"  - {len(schedules)} schedules")
        print(f"  - {len(addresses)} address objects")
        print(f"  - {len(address_groups)} address groups")
        print(f"  - {len(services)} service objects")
        print(f"  - {len(service_groups)} service groups")
        print(f"  - {len(security_rules)} security rules")
        print(f"  - {len(nat_rules)} NAT rules")
        print(f"  - {len(decryption_rules)} decryption rules")
        print(f"  - {len(pbf_rules)} policy-based forwarding rules")
        print(f"  - {len(app_override_rules)} application override rules")
        print(f"  - {len(zones)} zones")
        print(f"  - {len(interfaces)} interfaces")
        if logical_routers:
            print(f"  - {len(virtual_routers)} virtual routers (legacy)")
            print(f"  - {len(logical_routers)} logical routers (advanced routing)")
            print(f"  - {len(all_routers)} total routers")
        else:
            print(f"  - {len(virtual_routers)} virtual routers")
        
        # Count profiles
        profile_count = sum(len(profs) for profs in security_profiles.values())
        print(f"  - {profile_count} security profiles")
        print(f"  - {len(security_profile_groups)} security profile groups")
        print(f"  - {len(zone_protection_profiles)} zone protection profiles")
        print(f"  - {len(log_settings)} log forwarding profiles")
        print(f"  - {len(qos_profiles)} QoS profiles")
        print(f"  - {len(tunnel_monitor_profiles)} tunnel monitor profiles")
        
        # Dynamic routing
        if bgp_config:
            peer_count = len(bgp_config.get('peers', []))
            print(f"  - BGP enabled with {peer_count} peers")
        if ospf_config:
            area_count = len(ospf_config.get('areas', []))
            print(f"  - OSPF enabled with {area_count} areas")
        
        # VPN
        print(f"  - {len(ike_gateways)} IKE gateways")
        print(f"  - {len(ipsec_tunnels)} IPsec tunnels")
        
        print(f"\nGenerating Terraform configuration in {args.output_dir}...")
        tf_gen = TerraformGenerator(args.output_dir)
        
        # Core configuration
        tf_gen.generate_provider_config()
        tf_gen.generate_variables()
        
        # New: Tags and URL/App objects
        tf_gen.generate_tags(tags)
        tf_gen.generate_custom_url_categories(custom_url_categories)
        tf_gen.generate_application_groups(application_groups)
        tf_gen.generate_application_filters(application_filters)
        tf_gen.generate_external_lists(external_lists)
        tf_gen.generate_schedules(schedules)
        
        # Address and Service objects
        tf_gen.generate_address_objects(addresses)
        tf_gen.generate_address_groups(address_groups)
        tf_gen.generate_service_objects(services)
        tf_gen.generate_service_groups(service_groups)
        
        # Network
        tf_gen.generate_zones(zones)
        tf_gen.generate_virtual_routers(all_routers)  # Handles both virtual & logical routers
        tf_gen.generate_ethernet_interfaces(interfaces)
        
        # Security Profiles
        tf_gen.generate_security_profiles(security_profiles)
        tf_gen.generate_security_profile_groups(security_profile_groups)
        tf_gen.generate_zone_protection_profiles(zone_protection_profiles)
        tf_gen.generate_log_settings(log_settings)
        tf_gen.generate_qos_profiles(qos_profiles)
        tf_gen.generate_tunnel_monitor_profiles(tunnel_monitor_profiles)
        
        # Rules
        tf_gen.generate_security_rules(security_rules)
        tf_gen.generate_nat_rules(nat_rules)
        tf_gen.generate_decryption_rules(decryption_rules)
        tf_gen.generate_pbf_rules(pbf_rules)
        tf_gen.generate_application_override_rules(app_override_rules)
        
        # Dynamic routing
        if bgp_config:
            tf_gen.generate_bgp_config(bgp_config)
        if ospf_config:
            tf_gen.generate_ospf_config(ospf_config)
        
        # VPN
        if ike_gateways or ipsec_tunnels:
            tf_gen.generate_vpn_config(ike_gateways, ipsec_tunnels, 
                                      ike_crypto_profiles, ipsec_crypto_profiles)
            tf_gen.generate_vpn_report(ike_gateways, ipsec_tunnels)
        
        # Reports
        tf_gen.generate_interface_report(interfaces)
        tf_gen.generate_readme()
        
        print(f"\n✓ Successfully generated Terraform configuration!")
        print(f"\n📄 Generated Migration Reports:")
        print(f"  - INTERFACE_MIGRATION_REPORT.txt (Interface and IP inventory)")
        if ike_gateways or ipsec_tunnels:
            print(f"  - VPN_MIGRATION_REPORT.txt ⚠️  (VPN config with key management instructions)")
        print(f"\nNext steps:")
        print(f"  1. cd {args.output_dir}")
        print(f"  2. Review INTERFACE_MIGRATION_REPORT.txt for interface mapping")
        if ike_gateways or ipsec_tunnels:
            print(f"  3. ⚠️  Review VPN_MIGRATION_REPORT.txt and update pre-shared keys!")
        print(f"  4. Review the generated .tf files")
        print(f"  5. Create terraform.tfvars with your credentials")
        if ike_gateways or ipsec_tunnels:
            print(f"  6. ⚠️  Add VPN pre-shared keys to terraform.tfvars (DO NOT COMMIT)")
        print(f"  7. Run: terraform init")
        print(f"  8. Run: terraform plan")
        print(f"  9. Run: terraform apply")
        
        return 0
        
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML file: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
