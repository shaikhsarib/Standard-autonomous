import json
import os
import datetime

# Filename for storing analytics dat
ANALYTICS_FILE = 'chatbot_analytics.json'

def track_event(event_type, details=None):
    """
    Tracks a chatbot event (e.g., 'message_received', 'response_sent').
    Stores data locally for basic analytics.
    """
    data = []
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []

    # Add the new event
    data.append({
        'event': event_type,
        'details': details,
        'timestamp': str(datetime.datetime.now())
    })

    try:
        with open(ANALYTICS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"Error saving analytics: {e}")
