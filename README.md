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

## Roadmap