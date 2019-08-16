""" Config manager class"""
import os
import sys
import copy
import json
import requests
import traceback

sys.path.append(str(os.getcwd()))
from qna.log.Logger import Logger

logger = Logger()

class Singleton(object):
    """
    Singleton interface:
    http://www.python.org/download/releases/2.2.3/descrintro/#__new__
    """
    def __new__(cls, *args, **kwds):
        it = cls.__dict__.get("__it__")
        if it is not None:
            return it
        cls.__it__ = it = object.__new__(cls)
        it.init(*args, **kwds)
        return it

    def init(self, *args, **kwds):
        pass
        
class ConfigManager(Singleton):
    """ Load a config from a json file """

    def __init__(self):
        self.asd = 'asd'
        self.default_conf_file = './share/config/default_config.json'
        self.conf_file = './share/config/config.json'

    def load_config(self, key="all"):
        """ Load the config file """
        try:
            if key == "all":
                logger.info('Read [%s] config from %s', key, self.default_conf_file)
                return json.load(open(self.default_conf_file))
            elif key == "db":
                # remote_config = json.load(open(self.default_conf_file)).get("remote_config")
                remote_config = self.load_config(key="remote_config")

                db_config = self.override_config(key)

                if not remote_config.get("USE_REMOTE_CONFIG"):
                    return db_config
                else:
                    return self.update_db_config(db_config, remote_config)
            else:
                return self.override_config(key)

        except IOError:
            print('An error occured trying to read the file ', self.default_conf_file)

    def override_config(self, key):
        default_conf = json.load(open(self.default_conf_file)).get(key, {})
        conf = json.load(open(self.conf_file)).get(key, {})
        for key in list(conf.keys()):
            default_conf[key] = conf[key]
        return default_conf

    def update_db_config(self, db_config, remote_config):
        """ fetch db config with remote mongo creds """

        try:
            host_url = remote_config.get("CONFIG_HOST") + remote_config.get("CONFIG_END_POINT")
            # print host_url
            file_path = remote_config.get("API_KEY_PATH")
            api_key = self.read_key_from_file(file_path)

            if not api_key:
                return db_config

            headers = {
                'apikey': api_key.strip(),
                'cache-control': 'no-cache'}

            response = requests.get(host_url, headers=headers)
            db_object = response.json().get("db", {})
            if "MONGO_URL" in db_object:
                mongo_uri = db_object.get("MONGO_URL")
            else:
                mongo_uri = "mongodb://" + db_object.get("userName") + ":" \
                            + db_object.get("password") + "@" + db_object.get("host") + ":" + str(db_object.get("port"))
            # print "##", mongo_uri
            local_db_config = copy.deepcopy(db_config)
            local_db_config["MONGO_URI"] = mongo_uri
            return local_db_config

        except Exception:
            logger.critical('Failed to to fetch mongo_uri from remote host, using local mongo_uri')
            logger.error(traceback.format_exc())
            return db_config

    @staticmethod
    def read_key_from_file(file_path):
        """ read file content """
        try:
            with open(file_path, 'r') as myfile:
                api_key = myfile.read()
            return api_key
        except:
            logger.critical('Failed to read api key from file %s', file_path)
            return None


if __name__ == "__main__":
    conf = ConfigManager()
    log_conf = conf.load_config(key='log')
    print(json.dumps(conf.load_config(key='squid_proxy'), indent=2))
