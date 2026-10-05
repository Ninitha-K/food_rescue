import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'surplus_food_redistribution_secret_key_2026')
    
    # Use SQLite by default for zero-setup execution, configurable to MySQL via environment variable or URI string.
    # MySQL URI format: mysql+pymysql://username:password@localhost:3306/surplus_food_db
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///surplus_food.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Decision Engine Weighting Factors (Configurable Backend Weights)
    DECISION_ENGINE_WEIGHTS = {
        'expiry_urgency': 0.25,
        'ngo_demand': 0.20,
        'ngo_capacity': 0.15,
        'distance': 0.15,
        'food_compatibility': 0.10,
        'volunteer_availability': 0.10,
        'receiving_hours': 0.05
    }

    # Average travel speed in km/h for delivery time estimation logic
    AVERAGE_SPEED_KMH = 30.0
