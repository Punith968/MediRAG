import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index("medirag")
index.delete(delete_all=True)
print("Pinecone index cleared successfully!")
