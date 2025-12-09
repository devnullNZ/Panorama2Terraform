# Example VPN and Routing Configuration Snippet

This file shows examples of BGP, OSPF, and VPN configurations that the
converter script can parse. Add these sections to your Panorama XML export.

## BGP Configuration Example

```xml
<protocol>
  <bgp>
    <enable>yes</enable>
    <router-id>1.1.1.1</router-id>
    <local-as>65001</local-as>
    <peer-group>
      <entry name="ISP-Peers">
        <type>ebgp</type>
      </entry>
    </peer-group>
    <peer>
      <entry name="ISP1">
        <peer-as>65000</peer-as>
        <enable>yes</enable>
        <peer-address>
          <ip>203.0.113.2</ip>
        </peer-address>
        <local-address>
          <interface>ethernet1/2</interface>
          <ip>203.0.113.1/30</ip>
        </local-address>
        <peer-group>ISP-Peers</peer-group>
      </entry>
    </peer>
  </bgp>
</protocol>
```

## OSPF Configuration Example

```xml
<protocol>
  <ospf>
    <enable>yes</enable>
    <router-id>1.1.1.1</router-id>
    <area>
      <entry name="0.0.0.0">
        <type>
          <normal/>
        </type>
      </entry>
    </area>
    <interface>
      <entry name="ethernet1/1">
        <enable>yes</enable>
        <passive>no</passive>
        <link-type>broadcast</link-type>
        <metric>10</metric>
      </entry>
    </interface>
  </ospf>
</protocol>
```

## IKE Crypto Profiles Example

```xml
<ike>
  <crypto-profiles>
    <ike-crypto-profiles>
      <entry name="default">
        <encryption>
          <member>aes-256-cbc</member>
          <member>aes-128-cbc</member>
        </encryption>
        <authentication>
          <member>sha256</member>
          <member>sha1</member>
        </authentication>
        <dh-group>
          <member>group14</member>
          <member>group5</member>
        </dh-group>
        <lifetime>
          <hours>8</hours>
        </lifetime>
      </entry>
    </ike-crypto-profiles>
    <ipsec-crypto-profiles>
      <entry name="default">
        <esp>
          <encryption>
            <member>aes-256-cbc</member>
          </encryption>
          <authentication>
            <member>sha256</member>
          </authentication>
        </esp>
        <dh-group>group14</dh-group>
        <lifetime>
          <hours>1</hours>
        </lifetime>
      </entry>
    </ipsec-crypto-profiles>
  </crypto-profiles>
</ike>
```

## IKE Gateway Example

```xml
<gateway>
  <entry name="Branch-Office-IKE-GW">
    <authentication>
      <pre-shared-key>
        <key/>
      </pre-shared-key>
    </authentication>
    <protocol>
      <ikev1>
        <ike-crypto-profile>default</ike-crypto-profile>
      </ikev1>
    </protocol>
    <local-address>
      <interface>ethernet1/2</interface>
    </local-address>
    <peer-address>
      <ip>198.51.100.10</ip>
    </peer-address>
    <local-id>
      <id>headquarters@example.com</id>
    </local-id>
    <peer-id>
      <id>branch@example.com</id>
    </peer-id>
  </entry>
</gateway>
```

## IPsec Tunnel Example

```xml
<tunnel>
  <ipsec>
    <entry name="Branch-Office-Tunnel">
      <tunnel-interface>tunnel.1</tunnel-interface>
      <auto-key>
        <ike-gateway>
          <entry name="Branch-Office-IKE-GW"/>
        </ike-gateway>
        <ipsec-crypto-profile>default</ipsec-crypto-profile>
        <proxy-id>
          <entry name="Proxy-HQ-to-Branch">
            <local>10.1.0.0/16</local>
            <remote>10.2.0.0/16</remote>
            <protocol>
              <number>0</number>
            </protocol>
          </entry>
        </proxy-id>
      </auto-key>
    </entry>
  </ipsec>
</tunnel>
```

## What the Converter Generates

When these configurations are present in your export, the converter will generate:

### For BGP:
- `bgp.tf` with BGP configuration
- Peer groups and peer definitions
- Automatic dependency management

### For OSPF:
- `ospf.tf` with OSPF configuration
- Area definitions
- Interface assignments

### For VPN:
- `vpn.tf` with complete VPN configuration
- IKE and IPsec crypto profiles
- IKE gateways with **placeholder pre-shared keys**
- IPsec tunnels with proxy IDs
- `VPN_MIGRATION_REPORT.txt` with key management instructions

## Important Note About Pre-Shared Keys

**Pre-shared keys are NOT included in Panorama exports for security reasons.**

The converter will:
1. Use placeholder: `***CHANGE_ME***`
2. Generate a VPN_MIGRATION_REPORT.txt with instructions
3. Warn you prominently to update keys before applying

You must:
1. Retrieve actual keys from your secure key management system
2. Update the keys in terraform.tfvars (recommended) or vpn.tf
3. NEVER commit actual keys to version control
