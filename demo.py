from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from bottle import Bottle
import time
import json
from api import Create_Service
from datetime import datetime, timedelta

CLIENT_SECRET_FILE = 'credentials.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']

service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)


def create_folder(name, parent_folder_name=None):
    try:
        parent_folder_id = None
        
        # Get the ID of the parent folder if parent_folder_name is provided
        if parent_folder_name:
            query = f"name='{parent_folder_name}' and mimeType='application/vnd.google-apps.folder'"
            response = service.files().list(q=query, fields='files(id)').execute()
            parent_folder = response.get('files', [])
            
            if parent_folder:
                parent_folder_id = parent_folder[0]['id']
        
        # Create the new folder with the provided name and optional parent folder ID
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id] if parent_folder_id else None
        }
        
        file = service.files().create(body=file_metadata, fields='id').execute()
        print(F'Folder ID: "{file.get("id")}".')
        return file.get('id')
    except HttpError as error:
        print(F'An error occurred: {error}')
        return None



def upload_to_folder(file_to_upload, New_File_Name, parent_folder_name):
    try:
        # Get the ID of the parent folder based on its name
        query = f"name='{parent_folder_name}' and mimeType='application/vnd.google-apps.folder'"
        response = service.files().list(q=query, fields='files(id)').execute()
        parent_folder = response.get('files', [])
        
        if not parent_folder:
            print(f"Parent folder '{parent_folder_name}' not found.")
            return None
        
        parent_folder_id = parent_folder[0]['id']
        
        # Upload files to the specified parent folder
        for i in range(len(New_File_Name)):
            file_metadata = {
                'name': New_File_Name[i],
                'parents': [parent_folder_id]
            }
            media = MediaFileUpload(file_to_upload[i], mimetype='image/jpeg', resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(F'File ID: "{file.get("id")}".')
        
        return file.get('id')
    except HttpError as error:
        print(F'An error occurred: {error}')
        return None



def move_file_to_folder(file_id, folder_id):
    try:
        file = service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        file = service.files().update(fileId=file_id, addParents=folder_id,
                                      removeParents=previous_parents,
                                      fields='id, parents').execute()
        return file.get('parents')
    except HttpError as error:
        print(F'An error occurred: {error}')
        return None


# Convert the timestamp to datetime object
timestamp = 1672215379.5045543
utc_time = datetime.utcfromtimestamp(timestamp)

# Add the timezone offset
timezone_offset = timedelta(hours=5, minutes=30)
local_Time = utc_time + timezone_offset

# Format the local time
local_time = local_Time.strftime('%H:%M:%S %d-%m-%Y')
app = Bottle()

# Google Drive credentials and folder ID
credentials_path = 'credentials.json'
folder_id = '1akp5KP5TLlmtE-eZw-vfHruKrOEd1Mzg'

# Global variables for caching
cache_file = 'cache.json'
cached_files = None
last_updated = None

# Function to fetch the list of files from Google Drive
def fetch_files_from_drive():
    response = service.files().list(q=f"'{folder_id}' in parents", fields='files').execute()
    files = response.get('files', [])
    return files


# Function to load data from cache file
def load_cache():
    global cached_files, last_updated

    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
            cached_files = cache_data.get('files', None)
            last_updated = cache_data.get('last_updated', None)
    except FileNotFoundError:
        cached_files = None
        last_updated = None


# Function to save the tree structure to cache file
def save_cache():
    global cached_files, last_updated

    cache_data = {'tree': cached_files['tree'], 'last_updated': last_updated}
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f, indent=4)
        
def build_tree(parent_folder_id, parent_folder_name):
    tree = []

    # Fetch files and subfolders from the parent folder
    response = service.files().list(q=f"'{parent_folder_id}' in parents", fields='files(id, name, mimeType, webViewLink)').execute()
    items = response.get('files', [])

    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            # If the item is a folder, recursively build its subtree
            subfolder = build_tree(item['id'], item['name'])
            if subfolder:
                tree.append({item['name']: subfolder})
        else:
            # If the item is a file, add it to the tree with the modified file link
            file_id = item['id']
            file_link = f"https://drive.google.com/uc?export=view&id={file_id}"
            file_info = {'name': item['name'], 'Link': file_link}
            tree.append(file_info)

    return tree



# Function to get the files, either from cache or by fetching from Google Drive
def get_files():
    global cached_files, last_updated

    load_cache()

    # Check if the cache is up to date
    if cached_files is not None and last_updated is not None:
        current_files = fetch_files_from_drive()

        if current_files == cached_files['files'] and local_time <= last_updated:
            return cached_files['tree']

    # Fetch the updated list of files from Google Drive and build the tree structure
    files = fetch_files_from_drive()
    tree = build_tree(folder_id, 'NSS')

    # Update the cache
    cached_files = {'files': files, 'tree': tree}
    last_updated = local_time
    save_cache()

    return tree


# Function to be called whenever you need to access the data
def access_data():
    files = get_files()
    return files




# Example usage
#create_folder('NIC Camp','NSS')
#upload_to_folder(['photo1.png', 'photo2.png'], ['me.png','you.jpg'], 'NIC Camp')
access_data()
#move_file_to_folder()
