from cloudflare import Cloudflare, APIConnectionError, APIStatusError
from librouteros import connect
from librouteros.exceptions import TrapError
from dataclasses import dataclass
from time import sleep
from os import environ
from logging import basicConfig, getLogger
from typing import Dict, Optional

basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=environ.get("LOG_LEVEL", "INFO")
)
logger = getLogger(__name__)


@dataclass
class Device:
    name: str
    address: str


# MikroTik Router Configuration
MIKROTIK_HOST = environ["MIKROTIK_HOST"]
MIKROTIK_USERNAME = environ["MIKROTIK_USERNAME"]
MIKROTIK_PASSWORD = environ["MIKROTIK_PASSWORD"]

# Cloudflare Configuration
CLOUDFLARE_API_TOKEN = environ["CLOUDFLARE_API_TOKEN"]
CLOUDFLARE_ZONE_ID = environ["CLOUDFLARE_ZONE_ID"]

# Initialize Cloudflare client
client = Cloudflare(api_token=CLOUDFLARE_API_TOKEN)


def get_connected_devices() -> Optional[list[Device]]:
    """
    Connects to MikroTik and returns a list of devices.
    Returns None if connection fails, to distinguish between "No devices" and "Error".
    """
    try:
        api = connect(username=MIKROTIK_USERNAME, password=MIKROTIK_PASSWORD, host=MIKROTIK_HOST)
        devices = []
        device_names = []
        
        # Fetch leases
        leases = api.path("/ip/dhcp-server/lease")
        
        for device in leases:
            # Filter specific server if needed
            if device.get("server") != "dhcp2_devices":
                continue
            
            # Validation
            if not device.get("host-name") or not device.get("expires-after"):
                continue
                
            name = device["host-name"].lower().strip()
            
            # deduplicate names (prefer first found)
            if name in device_names:
                continue
            
            device_names.append(name)
            devices.append(Device(name=name, address=device["address"]))
            
        api.close()
        return devices

    except (TrapError, Exception):
        logger.exception("Failed to connect to MikroTik or retrieve leases")
        return None


def update_cloudflare_dns(devices: list[Device]):
    """
    Fetches current Cloudflare state and updates/creates records where necessary.
    """
    logger.info("Starting Cloudflare synchronization...")
    try:
        # Fetch all A records for the zone
        existing_records_page = client.dns.records.list(
            zone_id=CLOUDFLARE_ZONE_ID, 
            type="A", 
            per_page=500
        )
        
        existing_hostnames = {rec.name: rec for rec in existing_records_page}
        updates_count = 0

        for device in devices:
            record_name = f"{device.name}.lo.f0rth.space"
            record_ip = device.address

            if record_name in existing_hostnames:
                existing_record = existing_hostnames[record_name]
                
                # 1. Check IP equality
                if existing_record.content == record_ip:
                    continue # Completely synonymous, skip

                # 2. Safety Check: Managed Comment
                comment = existing_record.comment
                if not comment or not comment.startswith("@managed"):
                    logger.debug(f"Skipping {record_name}: Not managed by script")
                    continue
                
                # 3. Update Record
                try:
                    client.dns.records.edit(
                        dns_record_id=existing_record.id,
                        zone_id=CLOUDFLARE_ZONE_ID,
                        type="A",
                        name=record_name,
                        content=record_ip,
                        ttl=300,
                        comment="@managed by auto-update script",
                    )
                    logger.info(f"UPDATED: {record_name} -> {record_ip}")
                    updates_count += 1
                except APIStatusError as e:
                    logger.error(f"Failed to update {record_name}: {e}")

            else:
                # 4. Create New Record
                try:
                    client.dns.records.create(
                        zone_id=CLOUDFLARE_ZONE_ID,
                        type="A",
                        name=record_name,
                        content=record_ip,
                        ttl=300,
                        comment="@managed by auto-update script",
                    )
                    logger.info(f"CREATED: {record_name} -> {record_ip}")
                    updates_count += 1
                except APIStatusError as e:
                    logger.error(f"Failed to create {record_name}: {e}")

        if updates_count == 0:
            logger.info("Cloudflare check complete: No actual DNS changes needed.")
        else:
            logger.info(f"Cloudflare check complete: {updates_count} records modified.")

    except (APIConnectionError, APIStatusError) as e:
        logger.error(f"Cloudflare API Error: {e}")
    except Exception:
        logger.exception("Unexpected error during Cloudflare update")


def main():
    # Cache to store the previous state of {hostname: ip}
    last_known_state: Dict[str, str] = {}
    
    logger.info("Starting DHCP DNS Sync Service...")

    while True:
        try:
            devices = get_connected_devices()

            # Handle connection error (None) or empty list
            if devices is None:
                logger.warning("Could not fetch devices from MikroTik. Retrying in 60s...")
            else:
                # Convert current devices list to a dict for comparison
                current_state = {d.name: d.address for d in devices}

                # Logic: Only hit Cloudflare API if the MikroTik list looks different 
                # from the last successful run.
                if current_state != last_known_state:
                    if not last_known_state:
                        logger.info("Initial state loaded (or state reset). Syncing...")
                    else:
                        logger.info("Detected change in local network. Syncing...")
                    
                    # Perform the API operations
                    update_cloudflare_dns(devices)
                    
                    # Update the cache
                    last_known_state = current_state
                else:
                    logger.debug("No changes in DHCP leases. Skipping Cloudflare sync.")

        except Exception:
            logger.exception("Critical error in main loop")
        
        # Wait 60 seconds before next check
        sleep(60)


if __name__ == "__main__":
    main()
