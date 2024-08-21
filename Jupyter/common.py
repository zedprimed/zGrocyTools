import requests
import json

# Create class for global config
class GrConf:
    def __init__(self,file='localEnv.json'):
        env=open(file,'r')
        config=json.load(env)
        env.close()
        #class decs
        self.apikey = config['LocalUser']['APIKey']
        self.entrypoint = config['LocalUser']['URL Root']
        self.objects = config['Readpoints']['Objects']
        self.tz = config['LocalUser']['Timezone']

# Create class for API calls
class GrGetAPI:
    def __init__(self,config,obj):
        self.endpoint = config.entrypoint+config.objects[obj]
        self.key = config.apikey
        self.headers = {
            "accept": "application/json",
            "GROCY-API-KEY": self.key}
        self.params = {}
        self.r = 0
    def buildParam(self,*query):

        self.params = {"query[]":query}
        
    def call(self):
        self.r = requests.get(self.endpoint,headers=self.headers,params=self.params)