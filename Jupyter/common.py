import requests
import json
import common
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

        self.params = {"query[]":query}
        
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


if __name__ == "__main__":
  # Pass: spreadsheet_id, and range_name
  get_values("1CM29gwKIzeXsAppeNwrc8lbYaVMmUclprLuLYuHog4k", "A1:C2")