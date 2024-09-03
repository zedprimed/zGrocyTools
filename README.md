# zGrocyTools
A Python learning project to use Grocy as a small data platform
## Quick Start
1. [Install Python 3](https://www.python.org/downloads/) (at time of documentation this project has been using Python 3.12.5)
2. PIP dependency modules:
	1. [pandas](https://pandas.pydata.org/docs/getting_started/install.html): pip install pandas
	2. [Google Client Library](https://developers.google.com/sheets/api/quickstart/python): pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
	3. [Interactive Tables](https://github.com/mwouts/itables): pip install itables
3. Install Jupyter Lab
	* Option 1: [As a PIP download](https://jupyter.org/install): pip install jupyterlab
	* Option 2: [As a desktop client](https://github.com/jupyterlab/jupyterlab-desktop)
	* Option 3: [As a Docker stack](https://jupyter-docker-stacks.readthedocs.io/en/latest/index.html) or other self-hosted server
4. Download Jupyter folder from main repo to a place of your choosing. This should be somewhere your Jupyter Lab has access to (influenced by how you installed it)
5. Copy exmplEnv.json to a new file: localEnv.json and fill in the local config options:
	1. GoogleAPI-Credentials: Copy and paste the contents of a Google Cloud project (with the Sheets API activated) OAuth Client ID secret JSON download.
	2. LocalUser-APIKey - a Grocy client generated API key for the user you wish to transact with the Grocy server with the permissions expected to be used (i.e. change mode if you are expecting to utilize mass change scripts, or only read modes if you just want mass download scripts)
	3. LocalUser-Timezone - a pytz timezone to use as local time assuming Grocy config of UTC server time. Run the command below in a Python environment (ex. the Jupyter Lab console) to get the current list supported by the module.
	
	```
	import pytz
	pytz.all_timezones
	```
	4. LocalUser-URL Root - The HTTP address to your Grocy server ending in the API point /api/
	
6. Import the Workspaces files from the Jupyter/Workspaces folder to populate your Lab with the default workspaces. You can then access lab directly by the workspace and get into a view that's ready to do what you want.
7. Follow the instructions in each workbook that catches your fancy. Further details in the Process Summaries below.

## Roadmap
### Epic 1: Mass Change, Mass Process, Basic Transaction Analysis
* Mass change of master data in place in Google Sheets
* Mass process purchasing in Google Sheets
* Enable basic transaction analysis with basic query capability feeding into Jupyter ITables or Google Sheets
### Epic 2: OCR Integration
* Prepopulate Google Sheets with receipt data into mass change of master data and mass process of purchases
### Epic 3: Advanced Transaction Analysis
* Forecasting and summarizing of data
* Update of master data based on certain forecast results

## Process Summaries
### Google Sheets Bootstrap
If you want to use Google Sheet integration for some of the mass change in place processes you should do this process first.
If you are not familiar with Google Cloud APIs check out Google's [Get Started](https://developers.google.com/workspace/guides/get-started) guide. To summarize, you will need to:
1. Create a Google Cloud project
2. Activate the Sheets API
3. Create a local user Oauth key
4. Download the Oauth secret in JSON format
5. Copy and paste the contents of the JSON into localConf.
6. The first time you use a Sheets API and any time you use them with expired log ins, a browser will open to allow you to log in to the Google account that you wish to use the Drive of.
You may continue with a test project or promote to production as desired.  
Now you are ready to run the BootstrapGoogleSheets notebook:
1. Run each cell in turn to create the basic Spreadsheets, sheets, headers, and data connections
2. Pull up each sheet in each Spreadsheet to check for data connection errors - you must authorize each in the web UI
3. (Optional) file these sheets into a folder of choice in Drive.