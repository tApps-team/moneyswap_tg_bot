import os

from dotenv import load_dotenv

from sqlalchemy.engine import URL


load_dotenv()

TOKEN = os.environ.get('TOKEN')
WEBAPP_URL_ONE = os.environ.get('WEBAPP_URL_ONE')
WEBAPP_URL_TWO = os.environ.get('WEBAPP_URL_TWO')
WEBAPP_URL_THREE = os.environ.get('WEBAPP_URL_THREE')


PUBLIC_URL = os.environ.get('PUBLIC_URL')


#DATABASE
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASS')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_NAME = os.environ.get('DB_NAME')


db_url = URL.create(
    'postgresql+psycopg2',
    username=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
)

# Client Bot API
API_ID = os.environ.get('API_ID')
API_HASH = os.environ.get('API_HASH')


#Bearer authentication token
BEARER_TOKEN = os.environ.get('BEARER_TOKEN')