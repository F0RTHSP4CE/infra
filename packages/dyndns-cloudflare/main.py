import requests
import time
from os import environ
from cloudflare import Cloudflare, APIConnectionError, APIStatusError

# Your Cloudflare credentials and zone information
API_TOKEN = environ['CLOUDFLARE_API_TOKEN']
ZONE_ID = environ['CLOUDFLARE_ZONE_ID']
DNS_RECORD_ID = environ['CLOUDFLARE_DNS_RECORD_ID']
RECORD_NAME = environ['CLOUDFLARE_RECORD_NAME']

# Initialize Cloudflare client (v4)
client = Cloudflare(api_token=API_TOKEN)

def get_public_ip():
    """Fetches public IP address from eth0.me"""
    try:
        response = requests.get('https://eth0.me', timeout=10)
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException as e:
        print(f"Error fetching public IP: {e}")
        return None

def update_dns_record(ip_address):
    """Updates the DNS A record on Cloudflare with the new IP address"""
    try:
        # v4 SDK: Uses .edit() with named arguments instead of a data dict
        response = client.dns.records.edit(
            dns_record_id=DNS_RECORD_ID,
            zone_id=ZONE_ID,
            content=ip_address,
            name=RECORD_NAME,
            type="A",
            ttl=120
        )
        return response
    except APIStatusError as e:
        print(f"Cloudflare API error: {e}")
        raise
    except APIConnectionError as e:
        print(f"Cloudflare connection error: {e}")
        raise

def main():
    last_ip = None
    
    print(f"Starting DDNS Service for {RECORD_NAME}...")

    while True:
        current_ip = get_public_ip()

        if current_ip:
            # Only update if the IP has changed since the last successful run
            if current_ip != last_ip:
                print(f"IP Change detected ({last_ip} -> {current_ip}). Updating Cloudflare...")
                try:
                    update_response = update_dns_record(current_ip)
                    # v4 returns an object, we can access attributes directly
                    print(f"Success! DNS record updated. New IP: {update_response.content}")
                    last_ip = current_ip
                except Exception:
                    print("Failed to update DNS record. Will retry next cycle.")
            else:
                # Optional: Comment this out if you want total silence when nothing happens
                print(f"No change in IP ({current_ip}). Skipping update.")
        
        time.sleep(600)  # Sleep for 10 minutes

if __name__ == "__main__":
    main()
