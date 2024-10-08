import requests
import json
import os
import csv
import pandas as pd
import re
import logging
from datetime import date, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

import google.auth
##globals
CONFIGREGEX = r"\./.+?\./"

## Utilities
# Set up logging object with local data
def start_logger(suffix,level):
    '''
    Shortcut to starting a logger with the given name at the given level
    '''
    logging.basicConfig(
        filename=f"..\\Jupyter\\Logs\\{suffix}_log.csv",
        encoding="utf-8",
        filemode="a",
        format="{asctime},{name},{levelname},{message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
        level=eval(f'logging.{level}')
    )
    return logging
def parse_gr_symbols(match):
    '''
    Regex replacement function for certain symbols
    '''
    #case each defined symbol
    if match.group() == "./env./":
        replace = CONF.CONF['LocalUser']['Environment']
    elif match.group() == "./ipynb./":
        try:
            replace = NOTEBOOK_NAME
        except:
            replace = "Unknown Notebook"
    else:
        raise ValueError(f"Unexpected token: {match.group()}")
    return replace
    
##Gr config and interfaces
# Create class for global config
class GrConf:
    '''
    A helper class for the module
    loads the config file
    serves as an injection point for any notebook context needed in module
    A number of helper functions
    '''
    def __init__(self,notebook_name="Unknown Notebook",file='localEnv.json',ddic='ddic.csv'):
        env=open(file,'r',encoding='utf-8')
        config=json.load(env)
        env.close()
        with open(ddic,'r') as infile:
            reader = csv.DictReader(infile)
            self.dataDic = list(reader)
        #Inject a notebook name manually into global module context
        global NOTEBOOK_NAME
        NOTEBOOK_NAME = notebook_name
        #shortcut JSON to readable class values
        self.apikey = config['LocalUser']['APIKey']
        self.entrypoint = config['LocalUser']['URL Root']
        self.interface = config['Interface']
        self.tz = config['LocalUser']['Timezone']
        self.styleguide=config['GoogleAPI']['styleguide']
        self.sheets=config['GoogleAPI']['Sheets']
        self.CONF=config
        global CONF
        CONF = self
        logging.info('Config (re)loaded')
    def explainfield(self,field):
        ''' 
        Gives the data dictionary result in list format if it exists 
        or None if it does not
        '''
        for x in self.dataDic:
            if field == x['field']:
                return x
        return None
    def build_bools(self,APIresult):
        '''
        Returns a list of hard type bool fields
        '''
        bools = []
        for column in APIresult[0]:
            entry = self.explainfield(column)
            if entry != "Not Found" and entry['PyTypes'] == 'boolean' and entry['Import Hard Type'] == 'True':
                bools.append(entry['field'])
        return bools        
    def build_alias(self,APIresult):
        '''
        Builds a dictionary of field aliases to apply
        Takes a Grocy Get result and builds a dictionary of ID to Name/Description results
        '''
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
            raise ValueError("No aliasing found - is this a useful APIresult?")

    def list_uneditable(self):
        '''
        Returns a list of uneditable fields
        '''
        notEditable = []
        for entry in self.dataDic:
                if entry['notEditable'] == 'True':
                    notEditable.append(entry['field'])
        return notEditable

    def read_config(self,area):
        '''
        Returns config as a dictionary including replacing symbols with program values
        Ends up doing a deep copy through json.dumps and loads while parsing symbols
        '''
        try:
            result = self.__dict__[area]
            text = json.dumps(result)
            regex = re.sub(CONFIGREGEX,parse_gr_symbols,text)
            result = json.loads(regex)
            return result
        except KeyError:
            logging.warning(f'no config found for{area}')
            return None
    def cache_header_values(self,target,ordering=True):
        '''
        With a target data dictionary, calculates a bunch of required dicts
        for making Google Sheets updates and parsing data to and from Sheets to df
        and preparing for making Put and Get Grocy API calls
        '''
        alias_dict = {}
        md_cache = {}
        headerdef = {}
        i=1
        for field in target.keys():
            #slice ordering data out if ordering is indicated
            if ordering:
                try:
                    order = int(field[:2])
                except ValueError:
                    order = 'tech'
                field = field[2:]
                headerdef[field] = order
            else:
                field = field
                order = i
                i += 1
                headerdef[field] = order
            fieldDefinition = CONF.explainfield(field)
            #handling for undefiend custom fields
            try:
                if fieldDefinition['aliasObj'] != "":
                    iterCaller = GrGetAPI('Objects',fieldDefinition['aliasObj'])
                    iterCaller.buildParam("active=1")
                    iterCaller.get()
                    if "200" not in str(iterCaller.r):
                        logging.error(iterCaller.r+' API failure')
                        raise RuntimeError(iterCaller.r)
                    #summarize human alias for IDs in a dict
                    alias = {}
                    for objects in iterCaller.r.json():
                        alias[objects['id']] = objects['name']
                    alias_dict[field]=alias
                    #master data cache just in case
                    mdresult = iterCaller.r.json()
                    idresult = {}
                    for result in mdresult:
                        index = result.pop('id')
                        idresult[index]=result
                    md_cache[field] = idresult
                if fieldDefinition['PyTypes'] == "boolean":
                    #google aliases are TRUE and FALSE
                    alias = {1: "TRUE",0: "FALSE"}
                    alias_dict[field]=alias
            except:
                pass
        return alias_dict,md_cache,headerdef

def prep_df_to_upload(df,strNAreplace=True,boolreplace=True):
    '''
    Clean up function that gets a df into a list that works with Google Sheets API
    '''
    if strNAreplace: df = df.replace("<NA>","")
    if boolreplace:
        df = df.replace(True,"True")
        df = df.replace(False,"False")
    return df.values.tolist()

def refresh_activate_sheet(creds,spreadsheetId,sheetId,alias_dict,headerdef,logger=None):
    '''
    Google API batch updates for:
    Refresh validation with latest Grocy data
    Move sheet to front of Google Spreadsheet
    Add a super header based on config
    '''
    updater = GoBatchUpdate(creds,spreadsheetId)
    #add input help to columns with alias
    for field in alias_dict:
        #extract the possible values out of the thing
        validater = list(alias_dict[field].values())
        validater.sort()
        #initialize a request dict
        request = gr_style_template('request_styles','one_of_list_validation')
        #set the range
        chRange = request['setDataValidation']['range']
        chRange['startColumnIndex'] = int(headerdef[field])-1
        chRange['endColumnIndex'] = int(headerdef[field])
        chRange['startRowIndex'] = 2
        chRange['endRowIndex'] = CONF.CONF['LocalUser']['Max Rows to Format']
        chRange['sheetId'] = sheetId
        #set the values
        allowvalues = []
        for option in validater:
            valueObj = {"userEnteredValue":str(option)}
            allowvalues.append(valueObj)
        request['setDataValidation']['rule']['condition']['values'] = allowvalues
        #set the message
        request['setDataValidation']['rule']['inputMessage'] = 'Master Data Based Entry'
        #Prepare an API update
        updater.addReq(request)
        
    #add request to bring the sheet forward
    request = {"updateSheetProperties": {
            "properties": {
                "sheetId": sheetId,
                "index":0
            },
            "fields": "index"
    }
              }
    updater.addReq(request)
    updater.call()
    if logger:
        logger.info(updater.r)
    #Update the header with any utility values in config
    try:
        data = [gr_style_template("value_styles","default_header",file='localEnv.json')]
        for spreadsheet in CONF.sheets:
            if CONF.sheets[spreadsheet]['spreadsheetId'] == spreadsheetId:
                for sheet in CONF.sheets[spreadsheet]['sheets']:
                    if CONF.sheets[spreadsheet]['sheets'][sheet] == sheetId:
                        sheetname = sheet
        origin = 'A1'
        end = a1_from_table(origin,data)
        shRange = f'{origin}:{end}'
        sheets_update(creds,spreadsheetId,sheetname,shRange,data)
    except KeyError:
        if logger:
            logger.info("No header values configured")

class GrStyleGuide:
    '''
    deprecated, left for compatibility for now
    Create dict class for style guide data objects
    '''
    def __init__(self,stylebook,style,file='localEnv.json'):
        env=open(file,'r',encoding='utf-8')
        config=json.load(env)
        env.close()
        self.guide=config['GoogleAPI']['styleguide'][stylebook][style]
# umm that being a class is currently ridiculous. Method here instead makes more sense
def gr_style_template(stylebook,style,file='localEnv.json'):
    '''
    Loads a specific style direct from config file
    A shortcut compared to using CONF as we definitely need a deep copy
    but only need a very specific piece of config.
    '''
    fh=open(file,"r")
    strconfig = fh.read()
    result = re.sub(CONFIGREGEX,parse_gr_symbols,strconfig)
    config = json.loads(result)
    guide = config['GoogleAPI']['styleguide'][stylebook][style]
    fh.close()
    return guide

class GrGetAPI:
    '''
    Object to manage Get API calls to Grocy
    '''
    def __init__(self,category,obj):
        self.origEndpoint = CONF.entrypoint+CONF.interface[category][obj]['path']
        self.endpoint = self.origEndpoint #assume generally object gets until told otherwise by buildTx
        self.key = CONF.apikey
        self.headers = {
            "accept": "application/json",
            "GROCY-API-KEY": self.key}
        self.params = {}
        self.r = None
        self.reference = CONF.interface[category][obj]
    def buildParam(self,query):
        '''
        Build the Grocy query[] based queries which is a little different than the rest of
        a REST query i.e. str based statements and not dict
        query is a list of Grocy query statements (str)
        '''
        #compatibility with an old way: if the value is not a list, listify it
        if not isinstance(query, list):
            query = [query]
        self.params['query[]']=query
    def buildFreeParam(self,param):
        '''
        Build the normal REST queries which are in standard dict format
        param is in request Dict
        '''
        self.params.update(param)

    def buildTx(self,target,tx):
        '''
        simpler Tx builder for the Tx type gets
        '''
        if 'txType' in self.reference and (tx=="" or target==""):
            print("Not enough info for this type of post")
        elif 'txType' in self.reference:
            self.endpoint = self.origEndpoint+str(target)+'/'+tx
        else:
            self.endpoint = self.origEndpoint #rebuild lost endpoints for simple objects
        self.body = body
        
    def get(self):
        '''
        Executes the HTML request as a GET call using the URL, headers, and parameters
        built through other methods
        '''
        if bool(self.reference['get']):
            self.r = requests.get(self.endpoint,headers=self.headers,params=self.params)
        else:
            self.r = "Failure: get not enabled for this API"

# Create class for Post API calls
class GrPostAPI:
    '''
    Object to manage POST API calls to Grocy
    '''
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
        '''
        Build a transaction using a dict body, the target ID, and the Grocy transaction code
        '''
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
        '''
        Excecute the call as an HTML POST request
        '''
        self.r = requests.post(self.endpoint,headers=self.headers,json=self.body)
## Dataframe operations to apply rowwise
def gr_sales_unit_convert(row,product_def):
    '''
    Convert the entered quantity assuming it is a sales unit into the stocktaking unit
    '''
    #if a bad product ID, leave
    if pd.isna(row['product_id']): return row
    #check if sales unit is different than base unit and make a conversion if so
    if product_def['product_id'][row['product_id']]['qu_id_purchase'] == product_def['product_id'][row['product_id']]['qu_id_stock']:
        return row
    uom_check = GrGetAPI('Objects','quantity_unit_conversions')
    query = [
        f'from_qu_id={product_def['product_id'][row['product_id']]['qu_id_purchase']}',
        f'to_qu_id={product_def['product_id'][row['product_id']]['qu_id_stock']}',
        f'product_id={row['product_id']}'
        ]
    uom_check.buildParam(query)
    uom_check.get()
    conversion = uom_check.r.json()
    if len(conversion) != 1: raise ValueError(f'Inconsistent conversion returned for product:{row['product_id']}; id_purchase: {row['qu_id_purchase']}; id_stock: {row['qu_id_stock']}')
    row['amount'] = float(row['amount']) * float(conversion[0]['factor'])
    #log that a quantity was converted
    row['log'] = row['log'] + f'Conversion: quantity was converted by a factor of {conversion[0]['factor']} from {product_def['quantity_units'][product_def['product_id'][row['product_id']]['qu_id_purchase']]['name']} to {product_def['quantity_units'][product_def['product_id'][row['product_id']]['qu_id_stock']]['name']}'
    return row

def validate_purchase(row,md_cache):
    '''
    complete boolean evaluations on each row of a purchase DF to prepare for posting
    '''
    #line is not marked ready - log it and return
    if row['Ready'] == "":
        row['error'] = True
        row['log'] = row['log'] + "Not ready (no other evals run)"
        return row
    #product ID NaN
    if pd.isna(row['product_id']):
        row['error'] = True
        row['log'] = row['log'] + "Error: product ID not found (no other evals run)"
        return row
    #amount validation
    if row['amount'] == '':
        row['error'] = True
        row['log'] = row['log'] + "Error: no quantity,"
    if row['best_before_date'] == '':
        life = md_cache['product_id'][row['product_id']]['default_best_before_days']
        if life == 0:
            row['caution'] = True
        predBBD = days_from_now(life)
        row['log'] = row['log'] + f'Predicted BBD: {str(predBBD)},'
    if pd.isna(row['location_id']):
        pred_loc = md_cache['product_id'][row['product_id']]['location_id']
        pred_loc = md_cache['location_id'][pred_loc]['name']
        row['log'] = row['log'] + f'Predicted Location: {str(pred_loc)},'
    return row
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


def a1_from_table(startA1,data):
    '''
    use a1 utilities to find a corner bound from a start A1 and a data set
    '''
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


def tz(series):
    '''
    Deprecated - in case your Grocy is in UTC this can help
    Create a function for timezone handling of pandas series
    Localize a series into default timezone
    '''
    series = pd.to_datetime(series)
    if CONF.tz:
        series = series.dt.tz_localize(CONF.tz)
    return series


def days_from_now(n):
    '''
    Function for time deltas ex. BBD prediction
    '''
    return date.today() + timedelta(days=n)

def csv_extend(target,delimiter=','):
    '''
    Turn comma separated values in a list into more list
    '''
    new_list = []
    for entry in target:
        try:
            if delimiter in entry:
                new_list.extend(entry.split(delimiter))
            else: new_list.append(entry)
        except TypeError: new_list.append(entry)
    return new_list


def table_csv_extend(target,delimiter=','):
    '''
    apply csv_extend to list of list table data
    '''
    newTable = []
    for line in target:
        line = csv_extend(line,delimiter)
        newTable.append(line)
    return newTable

## Google reference functions
def GoogleOAuth():
    '''
    Runs Google OAuth to update tokens in config file
    '''
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
    """
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
    """
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





def sheets_append(creds,spreadsheet_id,sheetname,data,origin):
    '''
    simply appends a list of list data to the requested sheet
    if origin is in a table, Google will start from the bottom of it
    '''
    service = build("sheets", "v4", credentials=creds)
    response = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId = spreadsheet_id,
                    range=f'{sheetname}!{origin}',
                    valueInputOption="USER_ENTERED",
                    body = {
                            'values': data,
                            })
                .execute()
    )
    return response

def sheets_update(creds,spreadsheet_id,sheetname,shRange,data):
    '''
    Updates and overwrites the google sheet with a list of list data
    As in Google API, requires an explicit sheet range as a check against 
    what you are overwriting
    '''
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

def sheets_clear(creds,spreadsheet_id,sheetname,shRange):
    '''
    Clears the data in the sheet and range provided, leaving formatting
    '''
    service = build("sheets", "v4", credentials=creds)
    response = (
        service.spreadsheets()
        .values()
        .clear(
            spreadsheetId = spreadsheet_id,
            range = f'{sheetname}!{shRange}'
            )
        ).execute()
    return response

class GoBatchUpdate:
    '''
    An API object for building batch requests and providing them in mass to the Google API
    '''
    def __init__(self,creds,spreadsheet_id):
        self.creds = creds
        self.spreadsheet_id = spreadsheet_id
        self.requests = []

    def addReq(self,req):
        '''
        Adds a request
        A request is a dictionary as a JSON object for the API
        '''
        self.requests.append(req)
    
    def call(self):
        """
        Update the sheet details in batch, the user has access to.
        Load pre-authorized user credentials from the environment.
        TODO(developer) - See https://developers.google.com/identity
        for guides on implementing OAuth2 for the application.      
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