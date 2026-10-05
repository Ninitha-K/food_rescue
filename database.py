import os
from models import db, User, Restaurant, NGO, Volunteer, FoodDonation, Allocation, Delivery, DistributionRecord

def init_db(app):
    """
    Initializes the database schema and creates tables if they do not exist.
    """
    with app.app_context():
        db.create_all()
        print("[Database] Schema initialized successfully.")
