from pyexpat.errors import messages
from twilio.rest import Client
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
load_dotenv()
import re
account_sid = os.getenv('ACCOUNT_SID')
auth_token = os.getenv('AUTH_TOKEN')
client = Client(account_sid, auth_token)


processed_messages = set()


def display(messages):
    for msg in messages:
        print(f"SID: {msg.sid}")
        print(f"Account SID: {msg.account_sid}")
        print(f"From: {msg.from_}")
        print(f"To: {msg.to}")
        print(f"Body: {msg.body}")
        print(f"Date Created: {msg.date_created}")
        print(f"Date Sent: {msg.date_sent}")
        print(f"Date Updated: {msg.date_updated}")
        print(f"Direction: {msg.direction}")
        print(f"Error Code: {msg.error_code}")
        print(f"Error Message: {msg.error_message}")
        print(f"Messaging Service SID: {msg.messaging_service_sid}")
        print(f"Number of Media: {msg.num_media}")
        print(f"Number of Segments: {msg.num_segments}")
        print(f"Price: {msg.price}")
        print(f"Price Unit: {msg.price_unit}")
        print(f"Status: {msg.status}")
        print(f"Subresource URIs: {msg.subresource_uris}")
        print(f"URI: {msg.uri}")
        print("=" * 60)

def message_monitor():
  new_messages = client.messages.list(limit=1)
  display(new_messages)


def utc_time():
  utc_time = datetime.now(timezone.utc)
  return utc_time

if __name__ == "__main__":
  utc = utc_time()
  new_messages = client.messages.list(limit=10)
  for msg in new_messages:
    print(msg.body)
    var = utc - timedelta(minutes=5)
    time_diff = var - msg.date_created
    if time_diff.total_seconds() > 0:
      pass
    else:
      print(f"Negative: {time_diff}")
    print()
