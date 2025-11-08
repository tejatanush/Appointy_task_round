from pymongo import MongoClient
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def load_environments():
    load_dotenv()
    mongodb_URI=os.getenv("mongodb_url")
    mongodb_name=os.getenv("mongodb")
    collection_name=os.getenv("collection")
    collection2_name=os.getenv("collection2")
    OPENAI_KEY=os.getenv("OPENAI_API_KEY")
    return mongodb_URI,mongodb_name,collection_name,collection2_name,OPENAI_KEY
def get_JWT_settings():
    algo=os.getenv("ALGORITHM")
    secrete_key2=os.getenv("SECRET_KEY")
    time_in_min=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
    return algo,secrete_key2,time_in_min

def get_scraper():
    load_dotenv()
    scraper_api_key=os.getenv("SCRAPER_API_KEY")
    return scraper_api_key