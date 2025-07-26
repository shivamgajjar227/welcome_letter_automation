"""
Description: File contains all the constant values that will be used in entire code
"""
import base64
import os
from dotenv import load_dotenv

#  TODO change this to 0
USE_DOT_ENV = int(os.environ.get("USE_ENV", "0"))

if USE_DOT_ENV:
    cwd = os.getcwd()
    env_file = "/".join(cwd.split("/")[:-1]) + "/dpauth.env"
    load_dotenv(dotenv_path=env_file)



REMOTE_CONNECTION = 0
'''
DB Credencials
'''
id = 'root'
password = '12345678'
port = 3306
db_name = 'welcome_letter'

AUTH_SERVER_HOST = os.getenv("HOST", "0.0.0.0")
AUTH_SERVER_PORT = int(os.getenv("PORT", 10022))

# TODO: make OAUTHLIB_INSECURE_TRANSPORT = 0 when using SSL
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# TODO Default auth url - user agent will be redirected here
#   once client starts authorization flow

DEFAULT_APP_URI = f"{os.environ.get('APP_URI', 'https://test.dosepack.com')}"
DEFAULT_SERVER = f"{os.environ.get('AUTH_URI', 'https://mockurl.com')}"
DEFAULT_SERVER_HEADER = DEFAULT_SERVER.split('//')[1]
DEFAULT_AUTH_URI = f'{os.environ.get("AUTH_URI", "https://mockurl.com")}/api'
DEFAULT_POST_AUTH_URI = f"{DEFAULT_AUTH_URI}/postauth"
DEFAULT_TOKEN_URI = f"{DEFAULT_AUTH_URI}/api/token"
DEFAULT_SCOPE = ["dp-full-scope"]
DEFAULT_TOKEN_EXPIRE_TIME = int(os.environ.get("ACCESS_TOKEN_EXPIRE_TIME", 300))
DEFAULT_USER_LOGIN_TOKEN_EXPIRATION_TIME = 43200

APP_URL = f"{os.environ.get('APP_URI', 'https://mockurl.com')}"
RESET_PASS_URL = f"{APP_URL}/resetpassword"
SIGNUP_URL = f"{APP_URL}/signup"
TWO_FACTOR_AUTHENTICATION = True

DEFAULT_ADMIN_NAME = "Admin"

# TODO put these in ip const dictionary
IP_UNLOCKING_TIME = 86400
MAX_UNSUCCESSFUL_LOGIN_BY_IP = 50
MAX_UNSUCCESSFUL_LOGIN = 5

RESET_TOKEN_LIMIT = os.environ.get("RESET_TOKEN_LIMIT", 5)

SYSTEM_SETUP_ADDR_KEY = "system_setup"

ADDRESS_TYPES = ["system_setup", "billing", "company"]

SV_NAME = os.environ.get("SV_NAME", "dp-auth")

FROM_EMAIL_NAME = "Dosepacker"

FRONT_END_DOMAIN = DEFAULT_APP_URI

FRONT_END_RESET_PWD_PATH = f"{FRONT_END_DOMAIN}/resetpassword"
FRONT_END_RESET_PWD_ROUTE = '/resetpassword'
# api which requires no-auth
# make sure name starts with / and there are no params other
# than the path component of the endpoint url
NO_AUTH_ENDPOINTS = [
    "/api/ip/is_locked",
    "/api/user/password/forgot",
    "/api/validate_pwd_by_token",
    "/api/company/code/validate",
    "/api/user/email/validate",
    "/api/user/username/validate",
    "/api/company/admin",
    "/api/user/password/token_validate",
    "/api/user/password/reset",
    "/sv/geocode",
    "/api/user/pin/validate",
    "/api/user/last_login",
    "/api/sv/domain"
]

AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CLIENT_ID = "1004706828558-labfen4pprlme8nji56j6i7k9gab809l.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:3000/auth/oauth-callback"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

OLD_CRED_LIMIT = int(os.environ.get("OLD_CRED_LIMIT", 3))

if OLD_CRED_LIMIT <= 0:
    print(f'ensure {OLD_CRED_LIMIT=} is gt 0')
    raise Exception(f'{OLD_CRED_LIMIT=} should be > 0')

MAX_API_REQUEST_FOR_USER = int(os.environ.get("MAX_API_REQUEST_FOR_USER", 1000))

DEFAULT_IDLE_TIME = int(os.environ.get("DEFAULT_IDLE_TIME", 300))

SVC_SUFFIX_LEN = int(os.environ.get("SVC_SUFFIX_LEN", 10))
# variable denoting how many random chars to add during svc user creation.
# adding more len will give us flexibility to create more svc users

DRUG_DIMENSION_VERIFICATION_PENDING = 52
DRUG_DIMENSION_VERIFICATION_DONE = 53
DRUG_DIMENSION_VERIFICATION_REJECTED = 54

ODOO_CREATE_TASK_API_URL = "https://pms-qa.dosepack.com/create_task_canister"
ODOO_UPDATE_TASK_API_URL = "https://pms-qa.dosepack.com/update_task_canister"
ODOO_GET_TOKEN_URL = "https://pms-qa.dosepack.com/api/auth/get_tokens"

ODOO_TOKEN_PAYLOAD = {"username": "taskapi",
                      "password": "99$inDosePack",
                      "db": "pms_live_copy"}
ODOO_USERNAME = "taskapi"
ODOO_PASSWORD = "99$inDosePack"
ODOO_DB = "pms_live_copy"

TEMP_ATTACHMENT = "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"

MFT_MAPPING = {
    2: "odoo_canister",
    3: "canister_fixed_drum"
}

BUCKET_NAME_FOR_ODOO_DRUG_IMAGE = os.environ.get('BUCKET_NAME', 'dosepack-dev')
BLOB_NAME = os.environ.get("BLOB_NAME", "pill_dimension_images")


BASE_URL_PUB_SUB = os.environ.get("BASE_URL_PUB_SUB", "http://172.16.70.131:14016")
PUB_SUB_PUBLISH_API = "/publish"
TOPIC_SEND_NEW_DRUG = os.environ.get("TOPIC_SEND_NEW_DRUG", '/topic-qa_ph1-drugs_without_cdr_id')

# TOPIC_VERIFY_DD = os.environ.get("TOPIC_VERIFY_DD", "/topic-verify_drug_dimension")
# TOPIC_SEND_CDR_ID_LIST = os.environ.get("TOPIC_SEND_CDR_ID_LIST", '/topic-vibrant-cdr_id_list')
TOPIC_SENT_DRUG_DETAILS = os.environ.get("TOPIC_SENT_DRUG_DETAILS", '/topic-qa_ph1-send_cdr_drug_details')
TOPIC_ODOO_STAGE_UPDATE = os.environ.get("TOPIC_ODOO_STAGE_UPDATE", '/topic-qa_ph1-odoo_stage_update')
TOPIC_VERIFY_DD = os.environ.get("TOPIC_VERIFY_DD", '/topic-qa-verify_drug_dimension')
TOPIC_SEND_CDR_ID_LIST = os.environ.get("TOPIC_SEND_CDR_ID_LIST", '/topic-qa_ph1-cdr_id_list')
# TOPIC_SENT_DRUG_DETAILS = int(os.environ.get("TOPIC_SENT_DRUG_DETAILS", 2))
MAX_MSG_SIZE_FOR_PUB_SUB_IN_KB = int(os.environ.get("MAX_MSG_SIZE_FOR_PUB_SUB_IN_KB", 5000))


MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_API_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjUwNjExNTA0MCwiYWFpIjoxMSwidWlkIjo3MDU4OTMyNSwiaWFkIjoiMjAyNS0wNC0yOVQxNDoyMjozNS4wMDBaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MTgwNjU1MzMsInJnbiI6InVzZTEifQ.dFGw06lzcCtlPPAnR8nx2DPWZGvqxCeKIzln6Y26qZ4"  # replace with env variable in production