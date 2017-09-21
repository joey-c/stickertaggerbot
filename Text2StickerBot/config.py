import os

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

MAX_WORKERS = int(os.environ["MAX_WORKERS"])

db_name = os.environ["DATABASE_NAME"]
db_endpoint = os.environ["DATABASE_ENDPOINT"]
db_port = os.environ["DATABASE_PORT"]
db_username = os.environ["DATABASE_USERNAME"]
db_password = os.environ["DATABASE_PASSWORD"]

DATABASE_URI = "postgresql://" + \
               db_username + ":" + db_password + "@" + \
               db_endpoint + ":" + db_port + "/" + \
               db_name
