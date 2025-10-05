"""
Generate complete mockup data for today and recent days
"""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

APPS = ["Chrome", "Firefox", "Excel", "Word", "Outlook", "Teams", "Slack", "Code", "PowerPoint", "Spotify"]

def generate_hour(hour_num):
    """Generate exactly 60 minutes of data for one hour"""
    num_apps = random.randint(3, 5)
    selected_apps = random.sample(APPS, num_apps)
    
    # Distribute 3600 seconds among apps
    weights = [random.uniform(1, 5) for _ in selected_apps]
    total_weight = sum(weights)
    
    usage = {}
    allocated = 0
    for i, app in enumerate(selected_apps[:-1]):
        seconds = int((weights[i] / total_weight) * 3600)
        usage[app] = seconds
        allocated += seconds
    
    # Last app gets remainder
    usage[selected_apps[-1]] = 3600 - allocated
    
    return usage

def generate_day(date_str):
    """Generate data for all working hours of a day"""
    hourly_data = {}
    
    # Generate for 9am to 5pm (9-17)
    for hour in range(9, 18):
        hour_key = f"{date_str}_{hour:02d}"
        hourly_data[hour_key] = generate_hour(hour)
    
    return hourly_data

# Generate data for last 7 days including today
data = {"hourly_data": {}, "last_updated": datetime.now().timestamp()}

for days_ago in range(6, -1, -1):
    date = datetime.now() - timedelta(days=days_ago)
    date_str = date.strftime("%Y-%m-%d")
    day_data = generate_day(date_str)
    data["hourly_data"].update(day_data)

# Save
output_path = Path("data/app_usage.json")
output_path.parent.mkdir(exist_ok=True)

with open(output_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"✅ Generated {len(data['hourly_data'])} hours of data")
print(f"📅 Dates: {(datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
print(f"⏰ Hours per day: 9:00 - 17:00 (9 hours)")
print(f"💾 Saved to {output_path}")

