import requests
import json
import os
import pandas as pd

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import google.auth

# Create class for global config
class GrConf:
    def __init__(self,file='localEnv.json'):
        env=open(file,'r')
        config=json.load(env)
        env.close()
        #class decs
        self.apikey = config['LocalUser']['APIKey']
        self.entrypoint = config['LocalUser']['URL Root']
        self.interface = config['Interface']
        self.tz = config['LocalUser']['Timezone']
        global CONF
        CONF = self

# Create class for API calls
class GrGetAPI:
    def __init__(self,category,obj):
        self.endpoint = CONF.entrypoint+CONF.interface[category][obj]['path']
        self.key = CONF.apikey
        self.headers = {
            "accept": "application/json",
            "GROCY-API-KEY": self.key} # What headers for Put or Post?
        self.params = {}
        self.r = 0
        self.reference = CONF.interface[category][obj]
    def buildParam(self,*query):
        for x in query:
            #param is in Grocy query statements
            self.params['query[]'] = x
    def buildFreeParam(self,param):
        #param is in request Dict
        self.params.update(param)
    def get(self):
        if bool(self.reference['get']):
            self.r = requests.get(self.endpoint,headers=self.headers,params=self.params)
        else:
            self.r = "Failure: get not enabled for this API"

# Create a function for timezone handling of pandas series
def tz(series):
    series = pd.to_datetime(series,utc=True)
    if CONF.tz:
        series = series.dt.tz_convert(CONF.tz)
    return series

# Google reference functions
#Oauth

def GoogleOAuth():
    SCOPES = ["https://www.googleapis.com/auth/drive.file",]
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    #Instead of file token.json, get config token
    localConfigR = json.load(open("localEnv.json","r"))
    if localConfigR['GoogleAPI']['token'] != "":
        creds = Credentials.from_authorized_user_info(localConfigR['GoogleAPI']['token'], SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials = localConfigR['GoogleAPI']['credentials']
            flow = InstalledAppFlow.from_client_config(
                credentials, SCOPES
            )
            creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    #creds.to_json() did not appear to work right
    cold = json.loads(creds.to_json())
    localConfigR['GoogleAPI']['token'] = cold
    new = open("localEnv.json","w")
    json.dump(localConfigR,new)
    new.close()
    return creds  
# Create a sheet

def create(title,creds):
    """
    Creates the Sheet the user has access to.
    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    #creds, _ = google.auth.default() #turn off ADC for now???
    # pylint: disable=maybe-no-member
    try:
        service = build("sheets", "v4", credentials=creds)
        spreadsheet = {"properties": {"title": title}}
        spreadsheet = (
                service.spreadsheets()
                .create(body=spreadsheet, fields="spreadsheetId")
                .execute()
        )
        print(f"Spreadsheet ID: {(spreadsheet.get('spreadsheetId'))}")
        return spreadsheet.get("spreadsheetId")
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error
    if __name__ == "__main__":
            # Pass: title
            create("mysheet1")

#Read a sheet
def spreadsheet_get(creds,spreadsheet_id, range_name=''):
    """
    Creates the batch_update the user has access to.
    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    #creds, _ = google.auth.default()
    # pylint: disable=maybe-no-member
    try:
        service = build("sheets", "v4", credentials=creds)

        result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
        )
        rows = result.get("values", [])
        print(f"{len(rows)} rows retrieved")
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error


#Update a sheet
# sheets_batch_update - utilizes batching functionality to limit API calls. Not sure I'll need it?
# sheets_append - simply appends a list to the requested sheet

def sheets_append(creds,spreadsheet_id,sheetname,data):
    service = build("sheets", "v4", credentials=creds)
    response = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId = spreadsheet_id,
                    range=f'{sheetname}!A1',
                    valueInputOption="USER_ENTERED",
                    body = {
                            'values': data,
                            })
                .execute()
    )
    return response

'''
Leaving this for reference - I've implemented a class handler containing this as a call method to match my other REST calls
def sheets_batch_update(creds,spreadsheet_id, title='', find='', replacement='', append=''):
    """
    Update the sheet details in batch, the user has access to.
    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """

    #creds, _ = google.auth.default()
    # pylint: disable=maybe-no-member

    try:
        service = build("sheets", "v4", credentials=creds)

        requests = []
        # Change the spreadsheet's title.
        if title != '':
            requests.append(
                    {
                            "updateSpreadsheetProperties": {
                                    "properties": {"title": title},
                                    "fields": "title",
                            }
                    }
            )
        # Find and replace text
        if find != '' and replacement != '':
            requests.append(
                    {
                            "findReplace": {
                                    "find": find,
                                    "replacement": replacement,
                                    "allSheets": True,
                            }
                    }
            )
        #Append requests
        
        # Add additional requests (operations) ...


        if requests == []:
            print('No ops to do?!')
            return 'Noop'
        body = {"requests": requests}
        response = (
                service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
        )
        return response
    except HttpError as error:
        print(f"An error occurred: {error}")
        return error
'''

class GoBatchUpdate:
    def __init__(self,creds,spreadsheet_id):
        self.creds = creds
        self.spreadsheet_id = spreadsheet_id
        self.requests = []

    def addReq(self,req):
        self.requests.append(req)
    
    def call(self):
        """
        Update the sheet details in batch, the user has access to.
        Load pre-authorized user credentials from the environment.
        TODO(developer) - See https://developers.google.com/identity
        for guides on implementing OAuth2 for the application.
    
        requests is a list of JSON requests in dict format 
        ex.
        [{
    "addSheet": {
        "properties": {
            "title": "APISHeet"
            }
        }
        }]        
        """
    
        #creds, _ = google.auth.default()
        # pylint: disable=maybe-no-member
        creds = self.creds
        spreadsheet_id = self.spreadsheet_id
        requests = self.requests
        try:
            service = build("sheets", "v4", credentials=creds)
            if not len(requests) > 0:
                print('No ops to do?!')
                return 'Noop'
            body = {"requests": requests}
            print(body)
            response = (
                    service.spreadsheets()
                    .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                    .execute()
            )
            self.r = response
        except HttpError as error:
            #print(f"An error occurred: {error}")
            self.r = error