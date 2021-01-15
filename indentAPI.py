import requests
import json
from log.Logger import Logger

config_file_path="config.json"
oa=Logger()


class Indent:

    def __init__(self):
        data=self.read_json_file(config_file_path)
        self.bot_id=data["apiconfig"]["bot_id"]
        self.auth_token=data["apiconfig"]["auth_token"]


 
    def read_json_file(self,file_path):
        ogFile=file_path
        with open(ogFile, 'r') as infile: 
            #extracting all the data as is from our graph A 
            data = json.load(infile)
        return data

    
    def callintentAPI(self,input_string):

        oa.info("Calling the Intend API for: "+input_string)
        url = "https://bots.kore.ai/api/v1.1/rest/streams/"+self.bot_id+"/findIntent?fetchConfiguredTasks=true"
        payload = "{\n  \"input\": \""+input_string+" \",\n  \"streamName\": \"ABBevBot\"\n}"
        headers = {
        'auth': self.auth_token,
        'Content-Type': 'application/json'
        }
        try:
            response = requests.request("POST", url, headers=headers, data = payload)
            payload=response.json()
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            oa.debug(err)
            raise SystemExit(err)

        

        if "definitive" in payload["response"]["faq"]:
            oa.info("FAQ SCORE: "+str(payload["response"]["faq"]["definitive"][0]["faqScore"]))
            if payload["response"]["faq"]["definitive"][0]["faqScore"]>90:
                primaryQuestion=payload["response"]["faq"]["definitive"][0]["primaryQuestion"]
                return primaryQuestion
            
        else:
            oa.info("No match found/FAQ score is low")
            return 0
    
