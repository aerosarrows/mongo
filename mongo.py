from pymongo import MongoClient
import json 
from stravalib.client import Client  

with open('config.json', 'r') as f:
    cred = json.load(f)
  
client_id = cred['strava']['client_id']
client_secret = cred['strava']['client_secret']
username = cred['mongo_cloud']['username']
pw = cred['mongo_cloud']['pw']

uri = f"mongodb+srv://{username}:{pw}@glisch.erfhilu.mongodb.net/?retryWrites=true&w=majority"
mongoclient = MongoClient(uri) 

token_file = 'strava.json'

def save_tokens(access_token, refresh_token):
    # Save tokens to a file
    with open(token_file, 'w') as f:
        json.dump({'access_token': access_token, 'refresh_token': refresh_token}, f)

def load_tokens():
    # Load tokens from the file
    try:
        with open(token_file, 'r') as f:
            tokens = json.load(f)
            return tokens['access_token'], tokens['refresh_token']
    except FileNotFoundError:
        return None, None

def refresh_access_token(client_id, client_secret, refresh_token):
    client = Client()
    token_response = client.refresh_access_token(client_id=client_id, client_secret=client_secret, refresh_token=refresh_token)
    return token_response['access_token']

def oauth():
    # Load existing tokens
    access_token, refresh_token = load_tokens()

    if not access_token or not refresh_token:
        # Perform OAuth flow to get initial tokens
        client = Client()
        token_url = client.authorization_url(client_id=client_id, redirect_uri='http://localhost:8282/authorized')
        print(f'Please go to {token_url} to authorize access') 
        code = input('Enter the code from the authorization page: ') 
        token_response = client.exchange_code_for_token(client_id=client_id, client_secret=client_secret, code=code)
        print('Saving authorization information')
        access_token = token_response['access_token']
        refresh_token = token_response['refresh_token']
        save_tokens(access_token, refresh_token)

    return access_token

def get_activities(access_token):
    client = Client(access_token=access_token)
    activities = client.get_activities(limit=10)
    print('Strava Access Granted\nGrabbing activity details')  

    for activity in activities:
        activity_data = {
            "name": activity.name,
            "start_date": activity.start_date,
            "type": activity.type,
            "photos": activity.total_photo_count,
        }
        db = mongoclient["strava"]
        collection = db["glisch"]
        collection.insert_one(activity_data)
    mongoclient.close()
    print('Activity details uploaded successfully')

# Close the connection to MongoDB when you're done.

def main():
    # Get access token (refresh if necessary)
    access_token = oauth()

    # Get and upload activities to MongoDB
    get_activities(access_token)

if __name__ == "__main__":
    main()


