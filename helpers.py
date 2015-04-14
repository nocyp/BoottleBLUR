import os
import logging
import json
import configparser
import appdirs
import decimal
import apsw
from darkpoold.lib import config, util, bitcoin


def D(num):
    try:
        return decimal.Decimal(num)
    except:
        return decimal.Decimal(0) 

def set_options (data_dir=None, bitcoind_rpc_connect=None, bitcoind_rpc_port=None,
                 bitcoind_rpc_user=None, bitcoind_rpc_password=None, rpc_host=None, rpc_port=None,
                 rpc_user=None, rpc_password=None, log_file=None, database_file=None, testnet=False, testcoin=False, unittest=False, headless=False):

    # Unittests always run on testnet.
    if unittest and not testnet:
        raise Exception # TODO

    if not data_dir:
        config.DATA_DIR = appdirs.user_data_dir(appauthor='Darkpoold', appname='darkpoold', roaming=True)
    else:
        config.DATA_DIR = data_dir
    if not os.path.isdir(config.DATA_DIR): os.mkdir(config.DATA_DIR)

    # Configuration file
    configfile = configparser.ConfigParser()
    config_path = os.path.join(config.DATA_DIR, 'darkpoold.conf')
    configfile.read(config_path)
    has_config = 'Default' in configfile
    #logging.debug("Config file: %s; Exists: %s" % (config_path, "Yes" if has_config else "No"))


    # Bitcoind RPC host
    if bitcoind_rpc_connect:
        config.BITCOIND_RPC_CONNECT = bitcoind_rpc_connect
    elif has_config and 'bitcoind-rpc-connect' in configfile['Default'] and configfile['Default']['bitcoind-rpc-connect']:
        config.BITCOIND_RPC_CONNECT = configfile['Default']['bitcoind-rpc-connect']
    else:
        config.BITCOIND_RPC_CONNECT = 'localhost'

    # Bitcoind RPC port
    if bitcoind_rpc_port:
        config.BITCOIND_RPC_PORT = bitcoind_rpc_port
    elif has_config and 'bitcoind-rpc-port' in configfile['Default'] and configfile['Default']['bitcoind-rpc-port']:
        config.BITCOIND_RPC_PORT = configfile['Default']['bitcoind-rpc-port']
    else:
        config.BITCOIND_RPC_PORT = '8332'
    try:
        int(config.BITCOIND_RPC_PORT)
        assert int(config.BITCOIND_RPC_PORT) > 1 and int(config.BITCOIND_RPC_PORT) < 65535
    except:
        config.BITCOIND_RPC_PORT = '8332'

    # Bitcoind RPC user
    if bitcoind_rpc_user:
        config.BITCOIND_RPC_USER = bitcoind_rpc_user
    elif has_config and 'bitcoind-rpc-user' in configfile['Default'] and configfile['Default']['bitcoind-rpc-user']:
        config.BITCOIND_RPC_USER = configfile['Default']['bitcoind-rpc-user']
    else:
        config.BITCOIND_RPC_USER = 'bitcoinrpc'

    # Bitcoind RPC password
    if bitcoind_rpc_password:
        config.BITCOIND_RPC_PASSWORD = bitcoind_rpc_password
    elif has_config and 'bitcoind-rpc-password' in configfile['Default'] and configfile['Default']['bitcoind-rpc-password']:
        config.BITCOIND_RPC_PASSWORD = configfile['Default']['bitcoind-rpc-password']
    else:
        config.BITCOIND_RPC_PASSWORD = ''

    config.BITCOIND_RPC = 'http://' + config.BITCOIND_RPC_USER + ':' + config.BITCOIND_RPC_PASSWORD + '@' + config.BITCOIND_RPC_CONNECT + ':' + str(config.BITCOIND_RPC_PORT)

    #GUI host:
    if has_config and 'gui-host' in configfile['Default'] and configfile['Default']['gui-host']:
        config.GUI_HOST = configfile['Default']['gui-host']
    else:
        config.GUI_HOST = 'localhost'

    # GUI port
    if has_config and 'gui-port' in configfile['Default'] and configfile['Default']['gui-port']:
        config.GUI_PORT = configfile['Default']['gui-port']
    else:
        config.GUI_PORT = '8080'
    try:
        int(config.GUI_PORT)
        assert int(config.GUI_PORT) > 1 and int(config.GUI_PORT) < 65535
    except:
        config.GUI_PORT = '8080'

    # GUI user
    if has_config and 'gui-user' in configfile['Default'] and configfile['Default']['gui-user']:
        config.GUI_USER = configfile['Default']['gui-user']
    else:
        config.GUI_USER = 'xcpgui'

    # GUI password
    if has_config and 'gui-password' in configfile['Default'] and configfile['Default']['gui-password']:
        config.GUI_PASSWORD = configfile['Default']['gui-password']
    else:
        config.GUI_PASSWORD = ''

    config.GUI_HOME = 'http://' + config.GUI_USER + ':' + config.GUI_PASSWORD + '@' + config.GUI_HOST + ':' + str(config.GUI_PORT)

    config.GUI_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'counterpartygui')

    # Log
    if log_file:
        config.LOG = log_file
    elif has_config and 'logfile' in configfile['Default']:
        config.LOG = configfile['Default']['logfile']
    else:
        config.LOG = os.path.join(config.DATA_DIR, 'counterpartyd.log')

    config.PREFIX = b'CNTRPRTY'

    # Database
    if database_file:
        config.DATABASE = database_file
    else:
        config.VERSION_MAJOR
        config.DATABASE = os.path.join(config.DATA_DIR, 'darkpoold.' + str(config.VERSION_MAJOR) + '.db')

    config.ADDRESSVERSION = b'\x1b'
    config.BLOCK_FIRST = 17000
    config.BURN_START = 17000
    config.BURN_END = config.BURN_START + 30*24*60
    config.UNSPENDABLE = '1CounterpartyXXXXXXXXXXXXXXXUWLpVr'
            

    # Headless operation
    config.HEADLESS = headless
    config.TESTNET = False

    
    return configfile

def check_config():
    ok = config.GUI_HOST!=''
    ok = ok and config.GUI_PORT!=''
    ok = ok and config.GUI_USER!=''
    ok = ok and config.GUI_PASSWORD!=''
    ok = ok and config.BITCOIND_RPC_CONNECT!=''
    ok = ok and config.BITCOIND_RPC_PORT!=''
    ok = ok and config.BITCOIND_RPC_USER!=''
    #ok = ok and config.BITCOIND_RPC_PASSWORD!=''
    return ok


def connect_to_db(timeout=1000):
    """Connects to the SQLite database, returning a db Connection object"""
    db = apsw.Connection(config.DATABASE)
    cursor = db.cursor()
    cursor.execute('''PRAGMA count_changes = OFF''')
    cursor.close()
    db.setrowtrace(util.rowtracer)
    db.setexectrace(util.exectracer)
    db.setbusytimeout(timeout)
    return db

def init_logging():

    logger = logging.getLogger() #get root logger
    logger.setLevel(logging.INFO)
    #Console logging
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)


def S(value):
    return int(D(value)*config.UNIT)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o,  decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

def check_auth(user, passwd):
    if user==config.GUI_USER and passwd==config.GUI_PASSWORD:
        return True
    return False

def wallet_unlock(passphrase=None):
    success_response = {'success':True, 'message':'Wallet unlocked'}

    getinfo = bitcoin.rpc('getinfo', [])
    if 'unlocked_until' not in getinfo:
        return success_response
    elif getinfo['unlocked_until'] > 0:
        return success_response
    else:
        if passphrase is not None:
            headers = {'content-type': 'application/json'}
            payload = {
                "method": "walletpassphrase",
                "params": [passphrase, 60],
                "jsonrpc": "2.0",
                "id": 0,
            }
            passhprase_response = bitcoin.connect(config.BITCOIND_RPC, payload, headers)
            passhprase_response_json = passhprase_response.json()
            if 'error' not in passhprase_response_json.keys() or passhprase_response_json['error'] == None:
                return success_response
            else:
                return {'success':False, 'message':'Invalid passhrase'}
        else:
            return {'success':False, 'message':'Wallet locked. Type your passphrase'}

