# zGrocyTools
A Python learning project to use Grocy as a small data platform
## Quick Start
1. [Install Python 3](https://www.python.org/downloads/) (at time of documentation this project has been using Python 3.12.5)
2. PIP dependency modules:
	1. [pandas](https://pandas.pydata.org/docs/getting_started/install.html): pip install pandas
	2. [Google Client Library](https://developers.google.com/sheets/api/quickstart/python): pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
	3. [Interactive Tables](https://github.com/mwouts/itables): pip install itables
3. Install Jupyter Lab
	* Option 1: [As a PIP download]()
	* Option 2: [As a desktop client](https://github.com/jupyterlab/jupyterlab-desktop)
	* Option 3: [As a Docker stack](https://jupyter-docker-stacks.readthedocs.io/en/latest/index.html) or other self-hosted server
4. Download Jupyter folder from main repo to a place of your choosing. Be aware your choice of Jupyet Lab install will control what is in scope of your Lab
5. Copy exmplEnv.json to a new file: localEnv.json and fill in the local config options:
	1. GoogleAPI-Credentials: Copy and paste the contents of a Google Cloud project (with the Sheets API activated) OAuth Client ID secret JSON download.
	2. LocalUser-APIKey - a Grocy client generated API key for the user you wish to transact with the Grocy server with the permissions expected to be used (i.e. change mode if you are expecting to utilize mass change scripts, or only read modes if you just want mass download scripts)
	3. LocalUser-Timezone - a pytz timezone to use as local time assuming Grocy config of UTC server time.
	4. LocalUser-URL Root - The HTTP address to your Grocy server ending in the API point /api/