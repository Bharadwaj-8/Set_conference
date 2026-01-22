#!/usr/bin/env python3
"""
Test monitor implementations
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.monitors.factory import MonitorFactory

print("Testing monitor factory...")

# Test battery monitor
print("\n1. Testing Battery Monitor:")
battery = MonitorFactory.create_battery_monitor()
print(f"  Type: {type(battery)}")
print(f"  Available methods: {[m for m in dir(battery) if not m.startswith('_')]}")

# Test network monitor
print("\n2. Testing Network Monitor:")
network = MonitorFactory.create_network_monitor(use_speedtest=True)
print(f"  Type: {type(network)}")
print(f"  Available methods: {[m for m in dir(network) if not m.startswith('_')]}")

# Test carbon monitor
print("\n3. Testing Carbon Monitor:")
carbon = MonitorFactory.create_carbon_monitor(api_key=None, use_simulation_if_no_key=True)
print(f"  Type: {type(carbon)}")
print(f"  Available methods: {[m for m in dir(carbon) if not m.startswith('_')]}")

# Try to read values
print("\n" + "=" * 50)
print("ATTEMPTING TO READ VALUES:")
print("=" * 50)

monitors = {
    "battery": battery,
    "network": network,
    "carbon": carbon
}

for name, monitor in monitors.items():
    print(f"\n{name.upper()}:")

    # Try different method names
    reading_methods = ['read', 'get_value', 'get_reading', 'value', 'level', 'speed', 'intensity']
    found = False

    for method in reading_methods:
        if hasattr(monitor, method):
            try:
                value = getattr(monitor, method)()
                print(f"  Using {method}(): {value}")
                found = True
                break
            except Exception as e:
                print(f"  {method}() failed: {e}")

    if not found:
        print(f"  No readable method found. Available: {[m for m in dir(monitor) if not m.startswith('_')]}")