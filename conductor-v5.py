import requests
import json
import urllib3
import getpass
from datetime import datetime

# Disable SSL warnings due to self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Function to authenticate and get an access token
def authenticate(base_url):
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    login_url = f"{base_url}/api/v1/login"
    payload = {
        "username": username,
        "password": password
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(login_url, json=payload, headers=headers, verify=False)
    
    if response.status_code == 200:
        return response.json()['token']
    else:
        raise Exception(f"Authentication failed: {response.text}")

# Function to get the running configuration
def get_running_config(token, base_url):
    headers = {"Authorization": f"Bearer {token}"}
    config_url = f"{base_url}/api/v1/config/running"
    response = requests.get(config_url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch config: {response.text}")

# Function to get asset information
def get_asset_info(token, base_url):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    registry_url = f"{base_url}/api/v1/asset?verbose=false"
    response = requests.get(registry_url, headers=headers, verify=False)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch asset info: {response.text}")

# Function to get adjacency information for each router and node
def get_adjacency_info(token, base_url, router, node):
    headers = {"Authorization": f"Bearer {token}"}
    adjacency_url = f"{base_url}/api/v1/router/{router}/node/{node}/adjacency"
    response = requests.get(adjacency_url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()
    elif "Target router did not respond to any connection attempts" in response.text:
        return "Down"
    else:
        print(f"Failed to fetch adjacency for router {router}, node {node}")
        return []

def main():
    try:
        # Get base URL at runtime
        base_url = input("Enter the base URL (e.g., https://192.168.0.1): ")
        if not base_url.endswith('/'):
            base_url += '/'  # Ensure base URL ends with a slash

        # Authenticate
        token = authenticate(base_url)
        
        # Get running configuration
        config = get_running_config(token, base_url)

        # Generate filename with current date and timestamp
        current_datetime = datetime.now().strftime("%Y%m%d-%H%M%S")
        config_filename = f"conductor-config-{current_datetime}.txt"
        stats_filename = f"conductor-stats-{current_datetime}.txt"

        # Save running configuration to file in JSON format
        with open(config_filename, 'w') as outfile:
            json.dump(config, outfile, indent=2)
        
        print(f"Configuration saved to {config_filename}")

        # Display and save asset and adjacency information
        with open(stats_filename, 'w') as outfile:
            asset_info = get_asset_info(token, base_url)
            
            # Write asset information
            outfile.write("Asset Information:\n")
            outfile.write(f"{'Router':<20}{'Node':<15}{'Status':<15}{'Time in Status':<20}\n")
            outfile.write('-' * 70 + "\n")
            print("Asset Information:")
            print(f"{'Router':<20}{'Node':<15}{'Status':<15}{'Time in Status':<20}")
            print('-' * 70)
            for asset in asset_info:
                duration = asset.get('statusDurationSeconds', 0)
                time_in_status = f"{duration // 86400}d {(duration % 86400) // 3600}h {(duration % 3600) // 60}m"
                line = f"{asset.get('routerName', 'N/A'):<20}"
                line += f"{asset.get('nodeName', 'N/A'):<15}"
                line += f"{asset.get('status', 'N/A'):<15}"
                line += f"{time_in_status:<20}"
                outfile.write(line + "\n")
                print(line)

            # Write adjacency information
            outfile.write("\n\nAdjacency Information:\n")
            outfile.write(f"{'Router':<20}{'Node':<15}{'Status':<10}{'IPAddress':<50}{'DeviceInterface':<20}{'NetworkInterface':<20}\n")
            outfile.write('-' * 130 + "\n")
            print("\nAdjacency Information:")
            print(f"{'Router':<20}{'Node':<15}{'Status':<10}{'IPAddress':<50}{'DeviceInterface':<20}{'NetworkInterface':<20}")
            print('-' * 130)
            for asset in asset_info:
                router = asset.get('routerName', '')
                node = asset.get('nodeName', '')
                if router and node:
                    adjacency_data = get_adjacency_info(token, base_url, router, node)
                    if adjacency_data == "Down":
                        line = f"{router:<20}{node:<15}{'Down':<10}" + "N/A".ljust(50) + "N/A".ljust(20) + "N/A".ljust(20)
                        outfile.write(line + "\n")
                        print(line)
                    else:
                        for adj in adjacency_data:
                            status = "Up" if all(adj.get(prop, None) is not None for prop in ['jitter', 'linkLatency', 'packetLoss']) else "Down"
                            line = f"{router:<20}{node:<15}{status:<10}"
                            line += f"{adj.get('ipAddress', 'N/A'):<50}"
                            line += f"{adj.get('deviceInterface', 'N/A'):<20}"
                            line += f"{adj.get('networkInterface', 'N/A'):<20}"
                            outfile.write(line + "\n")
                            print(line)

        print(f"Asset and adjacency information saved to {stats_filename}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
