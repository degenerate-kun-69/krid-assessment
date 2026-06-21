
from pymongo import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://kokonut:<db_password>@whatsapp-bot-krid.3htnx0d.mongodb.net/?appName=whatsapp-bot-krid"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)