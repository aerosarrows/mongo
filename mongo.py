from pymongo import MongoClient
import json 
from stravalib.client import Client
from datetime import datetime  
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

with open('config.json', 'r') as f:
    cred = json.load(f)

# Replace the uri string with your MongoDB deployment's connection string.
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
    # Load existing token
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


def get_activities(access_token, collection):
    client = Client(access_token=access_token)
    activities = client.get_activities(limit = 1000)
    print('Strava Access Granted\nGrabbing activity details')  

    db = mongoclient["strava"]    
    collection = db["glisch"]
    if collection.find_one():
        print("Dropping Mongo collection for reload")
        collection.drop()
    else:
        print('No existing collections found')

    for activity in activities:
        activity_data = {
            "name": activity.name,
            "start_date": activity.start_date,
            "type": activity.type,
            "photos": activity.total_photo_count,
        }  
        db = mongoclient["strava"]    
        collection = db["glisch"]
        collection.insert_one(activity_data)   #Insert data into MongoDB
    print('Activity details uploaded successfully')
    
def plot_data(collection, access_token):
    # Get and upload activities to MongoDB if they don't exist
    get_activities(access_token, collection)

    cursor = collection.find()
    df = pd.DataFrame(list(cursor))
    # Close the connection to MongoDB 
    mongoclient.close()

    print('Data moved from Mongo to Pandas')
    df['start_date'] = pd.to_datetime(df['start_date'])

    # Extract month and year from 'start_date'
    df['month_year'] = df['start_date'].dt.to_period('M')

    # Count activities per month and type
    activities_per_month_type = df.groupby(['month_year', 'type']).size().unstack(fill_value=0)

    activities_per_month_type.plot(kind='bar', stacked=True, figsize=(12, 8), colormap='viridis')
    plt.title('Activities per Month Separated by Type')
    plt.xlabel('Month-Year')
    plt.ylabel('Number of Activities')
    plt.legend(title='Activity Type', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.show()


def main():
    # Get access token (refresh if necessary)
    access_token = oauth()

    db = mongoclient["strava"]
    collection = db["glisch"]

    plot_data(collection, access_token)

     
if __name__ == "__main__":
    main()