import requests
import json
import os
import csv
import pandas as pd
import re
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

import google.auth

# Set up logging object with local data
def start_logger(suffix,level):
    logging.basicConfig(
        filename=f"..\\Jupyter\\Logs\\{suffix}.log",
        encoding="utf-8",
        filemode="a",
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
        level=eval(f'logging.{level}')
    )
    return logging



# Create class for global config
class GrConf:
    def __init__(self,file='localEnv.json',ddic='ddic.csv'):
        env=open(file,'r')
        config=json.load(env)
        env.close()
        with open(ddic,'r') as infile:
            reader = csv.DictReader(infile)
            self.dataDic = list(reader)
        
        #unpack JSON to readable class 
        self.apikey = config['LocalUser']['APIKey']
        self.entrypoint = config['LocalUser']['URL Root']
        self.interface = config['Interface']
        self.tz = config['LocalUser']['Timezone']
        global CONF
        CONF = self
        logging.info('Config (re)loaded')
    def explainfield(self,field):
        # Gives the data dictionary result in list format if it exists or error string if it does not
        for x in self.dataDic:
            if field == x['field']:
                return x
        return 'Not Found'
    def build_alias(self,APIresult):
        # Builds a dictionary of field aliases to apply
        
        alias={}
        for x in APIresult[0]:
            aliasListing=[]
            fieldDef = self.explainfield(x)
            try: 
                if fieldDef['aliasObj']:
                    iterCaller = GrGetAPI('Objects',fieldDef['aliasObj'])
                    if fieldDef['aliasParam']:
                        iterCaller.buildParam(fieldDef['aliasParam'])
                    iterCaller.get()
                    if "200" not in str(iterCaller.r):
                        print(r+' API failure')
                        continue
                    #Build a dictionary of aliases to apply in dataframes with boolean loc
                    aliasPull=iterCaller.r.json()        
                    for y in aliasPull:
                        aliasListing.append({y['id']:y[fieldDef['aliasObjField']]})
                    alias[x]=aliasListing
            except TypeError:
                continue
        if alias:
            return alias
        else:
            print("No aliasing found for these results")



# Create class for Get API calls
class GrGetAPI:
    def __init__(self,category,obj):
        self.origEndpoint = CONF.entrypoint+CONF.interface[category][obj]['path']
        self.endpoint = self.origEndpoint #assume generally object gets until told otherwise by buildTx
        self.key = CONF.apikey
        self.headers = {
            "accept": "application/json",
            "GROCY-API-KEY": self.key} # What headers for Put or Post?
        self.params = {}
        self.r = 0
        self.reference = CONF.interface[category][obj]
    def buildParam(self,*query):
        for x in query:
            #param is in Grocy query statements (str)
            self.params['query[]'] = x
    def buildFreeParam(self,param):
        #param is in request Dict
        self.params.update(param)

    def buildTx(self,target,tx):
        #simpler Tx builder for the Tx type gets
        if 'txType' in self.reference and (tx=="" or target==""):
            print("Not enough info for this type of post")
        elif 'txType' in self.reference:
            self.endpoint = self.origEndpoint+str(target)+'/'+tx
        else:
            self.endpoint = self.origEndpoint #rebuild lost endpoints for simple objects
        self.body = body
        
    def get(self):
        if bool(self.reference['get']):
            self.r = requests.get(self.endpoint,headers=self.headers,params=self.params)
        else:
            self.r = "Failure: get not enabled for this API"

# Create class for Post API calls
class GrPostAPI:
    def __init__(self,category,obj):
        self.key = CONF.apikey
        self.headers = {
            "accept": "application/json",
            "GROCY-API-KEY": self.key,
            'Content-Type': 'application/json'
        }
        self.r = 0
        self.body = {}
        self.origEndpoint = CONF.entrypoint+CONF.interface[category][obj]['path']
        self.reference = CONF.interface[category][obj]
    def buildTx(self,body,target="",tx=""):
        if 'txType' in self.reference and (tx=="" or target==""):
            print("Not enough info for this type of post")
            #del the endpoint to stop from trying to post a malformed call after an earlier one that worked
            del self.endpoint
        elif 'txType' in self.reference:
            self.endpoint = self.origEndpoint+str(target)+'/'+tx
        else:
            self.endpoint = self.origEndpoint
        self.body = body

    def post(self):
        self.r = requests.post(self.endpoint,headers=self.headers,json=self.body)

#A1 notation converter adapted from gspread
def rowcol_to_a1(row: int, col: int):
    """Translates a row and column cell address to A1 notation.

    :param row: The row of the cell to be converted.
        Rows start at index 1.
    :type row: int, str

    :param col: The column of the cell to be converted.
        Columns start at index 1.
    :type row: int, str

    :returns: a string containing the cell's coordinates in A1 notation.

    Example:

    >>> rowcol_to_a1(1, 1)
    A1

    """
    if row < 1 or col < 1:
        raise IncorrectCellLabel("({}, {})".format(row, col))

    div = col
    column_label = ""

    while div:
        (div, mod) = divmod(div, 26)
        if mod == 0:
            mod = 26
            div -= 1
        column_label = chr(mod + 64) + column_label

    label = "{}{}".format(column_label, row)

    return label

#A1 notation converter adapated from gspread

def a1_to_rowcol(label: str):
    """Translates a cell's address in A1 notation to a tuple of integers.

    :param str label: A cell label in A1 notation, e.g. 'B1'.
        Letter case is ignored.
    :returns: a tuple containing `row` and `column` numbers. Both indexed
              from 1 (one).
    :rtype: tuple

    Example:

    >>> a1_to_rowcol('A1')
    (1, 1)

    """
    CELL_ADDR_RE = re.compile(r"([A-Za-z]+)([1-9]\d*)")
    m = CELL_ADDR_RE.match(label)
    if m:
        column_label = m.group(1).upper()
        row = int(m.group(2))

        col = 0
        for i, c in enumerate(reversed(column_label)):
            col += (ord(c) - 64) * (26**i)
    else:
        raise IncorrectCellLabel(label)

    return (row, col)

# use a1 utilities to find a corner bound from a start A1 and a data set
def a1_from_table(startA1,data):
    # Get width and height
    width = 0
    for x in data:
        if len(x) > width:
            width = len(x)
    height = len(data)
    # Get numerical row and column, add data dimensions, and convert back to A1
    row,column = a1_to_rowcol(startA1)
    row = row + height - 1
    column = column + width - 1
    converted = rowcol_to_a1(row,column)
    return converted

# Create a function for timezone handling of pandas series
# Localize a series into default timezone
def tz(series):
    series = pd.to_datetime(series)
    if CONF.tz:
        series = series.dt.tz_localize(CONF.tz)
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
            try:
                creds.refresh(Request())
            except RefreshError:
                # Catch token expiration for dev projects and just log in again
                del localConfigR['GoogleAPI']['token']
                credentials = localConfigR['GoogleAPI']['credentials']
                flow = InstalledAppFlow.from_client_config(
                credentials, SCOPES
                )
                creds = flow.run_local_server(port=0)
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
        logging.info(f"Spreadsheet ID: {(spreadsheet.get('spreadsheetId'))}")
        return spreadsheet.get("spreadsheetId")
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
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
        logging.info(f"{len(rows)} rows retrieved")
        return result
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        return error


#Update a sheet

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

def sheets_update(creds,spreadsheet_id,sheetname,shRange,data):
    service = build("sheets", "v4", credentials=creds)
    response = (
        service.spreadsheets()
        .values()
        .batchUpdate(
            spreadsheetId = spreadsheet_id,
            body = { # The request for updating more than one range of values in a spreadsheet.
                "valueInputOption": "USER_ENTERED", # How the input data should be interpreted.
                "data": [ # The new values to apply to the spreadsheet.
                  { # Data within a range of the spreadsheet.
                    "range": f'{sheetname}!{shRange}', 
                    "values": data,
                    "majorDimension": "ROWS",
                  },
                ],
              }
        ).execute()
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
                logging.critical("Passed noop to batch handler")
                return 'Noop'
            body = {"requests": requests}
            #print(body)
            response = (
                    service.spreadsheets()
                    .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                    .execute()
            )
            self.r = response
        except HttpError as error:
            #print(f"An error occurred: {error}")
            self.r = error