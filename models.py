from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False) # admin, restaurant, ngo, volunteer
    status = db.Column(db.String(20), default='active') # active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    restaurant = db.relationship('Restaurant', backref='user', uselist=False, cascade="all, delete-orphan")
    ngo = db.relationship('NGO', backref='user', uselist=False, cascade="all, delete-orphan")
    volunteer = db.relationship('Volunteer', backref='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Restaurant(db.Model):
    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, default=11.0168)
    longitude = db.Column(db.Float, default=76.9558)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    donations = db.relationship('FoodDonation', backref='restaurant', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class NGO(db.Model):
    __tablename__ = 'ngos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, default=11.0168)
    longitude = db.Column(db.Float, default=76.9558)
    accepted_food_types = db.Column(db.String(255), default='Cooked, Bakery, Packaged, Raw Produce')
    current_demand = db.Column(db.Integer, default=50)
    max_capacity = db.Column(db.Integer, default=100)
    receiving_hours = db.Column(db.String(50), default='08:00 - 22:00')
    service_area = db.Column(db.String(150), default='Central District')
    status = db.Column(db.String(20), default='active') # active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    allocations = db.relationship('Allocation', backref='ngo', lazy=True)
    distribution_records = db.relationship('DistributionRecord', backref='ngo', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accepted_food_types': self.accepted_food_types,
            'current_demand': self.current_demand,
            'max_capacity': self.max_capacity,
            'receiving_hours': self.receiving_hours,
            'service_area': self.service_area,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Volunteer(db.Model):
    __tablename__ = 'volunteers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    current_location = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, default=11.0168)
    longitude = db.Column(db.Float, default=76.9558)
    vehicle_type = db.Column(db.String(50), nullable=False) # Bike, Scooter, Car, Van, Truck
    vehicle_capacity = db.Column(db.Integer, nullable=False) # Capacity in units/meals
    availability_status = db.Column(db.String(20), default='AVAILABLE') # AVAILABLE, UNAVAILABLE
    max_delivery_distance = db.Column(db.Float, default=15.0) # km
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    allocations = db.relationship('Allocation', backref='volunteer', lazy=True)
    deliveries = db.relationship('Delivery', backref='volunteer', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'current_location': self.current_location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'vehicle_type': self.vehicle_type,
            'vehicle_capacity': self.vehicle_capacity,
            'availability_status': self.availability_status,
            'max_delivery_distance': self.max_delivery_distance,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class FoodDonation(db.Model):
    __tablename__ = 'food_donations'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id', ondelete='CASCADE'), nullable=False)
    food_name = db.Column(db.String(150), nullable=False)
    food_category = db.Column(db.String(50), nullable=False) # Cooked, Bakery, Packaged, Raw Produce
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(20), default='meals')
    prepared_time = db.Column(db.DateTime, nullable=False)
    expiry_time = db.Column(db.DateTime, nullable=False)
    pickup_location = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, default=11.0168)
    longitude = db.Column(db.Float, default=76.9558)
    is_veg = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='PENDING') 
    # PENDING -> NGO SELECTED -> VOLUNTEER ASSIGNED -> PICKED UP -> IN TRANSIT -> DELIVERED -> DISTRIBUTED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    allocation = db.relationship('Allocation', backref='donation', uselist=False, cascade="all, delete-orphan")
    delivery = db.relationship('Delivery', backref='donation', uselist=False, cascade="all, delete-orphan")
    distribution_record = db.relationship('DistributionRecord', backref='donation', uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        now = datetime.utcnow()
        remaining_minutes = max(0, int((self.expiry_time - now).total_seconds() / 60))
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'restaurant_name': self.restaurant.name if self.restaurant else 'Unknown',
            'food_name': self.food_name,
            'food_category': self.food_category,
            'quantity': self.quantity,
            'unit': self.unit,
            'prepared_time': self.prepared_time.strftime('%Y-%m-%d %H:%M:%S') if self.prepared_time else None,
            'expiry_time': self.expiry_time.strftime('%Y-%m-%d %H:%M:%S') if self.expiry_time else None,
            'remaining_minutes': remaining_minutes,
            'pickup_location': self.pickup_location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'is_veg': self.is_veg,
            'notes': self.notes,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Allocation(db.Model):
    __tablename__ = 'allocations'

    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('food_donations.id', ondelete='CASCADE'), nullable=False)
    ngo_id = db.Column(db.Integer, db.ForeignKey('ngos.id', ondelete='CASCADE'), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id', ondelete='SET NULL'), nullable=True)
    priority_score = db.Column(db.Float, nullable=False)
    feasibility_status = db.Column(db.String(20), default='FEASIBLE') # FEASIBLE, NOT FEASIBLE
    reason_for_selection = db.Column(db.Text, nullable=True)
    estimated_pickup_time_minutes = db.Column(db.Integer, default=15)
    estimated_delivery_time_minutes = db.Column(db.Integer, default=35)
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow)

    delivery = db.relationship('Delivery', backref='allocation', uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'donation_id': self.donation_id,
            'ngo_id': self.ngo_id,
            'ngo_name': self.ngo.name if self.ngo else 'N/A',
            'volunteer_id': self.volunteer_id,
            'volunteer_name': self.volunteer.name if self.volunteer else 'Unassigned',
            'priority_score': round(self.priority_score, 2) if self.priority_score else 0.0,
            'feasibility_status': self.feasibility_status,
            'reason_for_selection': self.reason_for_selection,
            'estimated_pickup_time_minutes': self.estimated_pickup_time_minutes,
            'estimated_delivery_time_minutes': self.estimated_delivery_time_minutes,
            'allocated_at': self.allocated_at.strftime('%Y-%m-%d %H:%M:%S') if self.allocated_at else None
        }


class Delivery(db.Model):
    __tablename__ = 'deliveries'

    id = db.Column(db.Integer, primary_key=True)
    allocation_id = db.Column(db.Integer, db.ForeignKey('allocations.id', ondelete='CASCADE'), nullable=False)
    donation_id = db.Column(db.Integer, db.ForeignKey('food_donations.id', ondelete='CASCADE'), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteers.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(30), default='ASSIGNED')
    # ASSIGNED -> PICKUP_STARTED -> PICKED_UP -> IN_TRANSIT -> NGO_RECEIVED -> COMPLETED
    pickup_started_at = db.Column(db.DateTime, nullable=True)
    picked_up_at = db.Column(db.DateTime, nullable=True)
    ngo_received_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    distribution_record = db.relationship('DistributionRecord', backref='delivery', uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'allocation_id': self.allocation_id,
            'donation_id': self.donation_id,
            'food_name': self.donation.food_name if self.donation else 'N/A',
            'quantity': self.donation.quantity if self.donation else 0,
            'volunteer_id': self.volunteer_id,
            'volunteer_name': self.volunteer.name if self.volunteer else 'N/A',
            'volunteer_phone': self.volunteer.phone if self.volunteer else 'N/A',
            'restaurant_name': self.donation.restaurant.name if self.donation and self.donation.restaurant else 'N/A',
            'pickup_location': self.donation.pickup_location if self.donation else 'N/A',
            'ngo_id': self.allocation.ngo_id if self.allocation else None,
            'ngo_name': self.allocation.ngo.name if self.allocation and self.allocation.ngo else 'N/A',
            'ngo_address': self.allocation.ngo.address if self.allocation and self.allocation.ngo else 'N/A',
            'status': self.status,
            'pickup_started_at': self.pickup_started_at.strftime('%Y-%m-%d %H:%M:%S') if self.pickup_started_at else None,
            'picked_up_at': self.picked_up_at.strftime('%Y-%m-%d %H:%M:%S') if self.picked_up_at else None,
            'ngo_received_at': self.ngo_received_at.strftime('%Y-%m-%d %H:%M:%S') if self.ngo_received_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class DistributionRecord(db.Model):
    __tablename__ = 'distribution_records'

    id = db.Column(db.Integer, primary_key=True)
    delivery_id = db.Column(db.Integer, db.ForeignKey('deliveries.id', ondelete='CASCADE'), nullable=False)
    ngo_id = db.Column(db.Integer, db.ForeignKey('ngos.id', ondelete='CASCADE'), nullable=False)
    donation_id = db.Column(db.Integer, db.ForeignKey('food_donations.id', ondelete='CASCADE'), nullable=False)
    quantity_received = db.Column(db.Integer, nullable=False)
    quantity_distributed = db.Column(db.Integer, nullable=False)
    beneficiaries_served = db.Column(db.Integer, nullable=False)
    distribution_completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'delivery_id': self.delivery_id,
            'ngo_id': self.ngo_id,
            'ngo_name': self.ngo.name if self.ngo else 'N/A',
            'donation_id': self.donation_id,
            'food_name': self.donation.food_name if self.donation else 'N/A',
            'quantity_received': self.quantity_received,
            'quantity_distributed': self.quantity_distributed,
            'beneficiaries_served': self.beneficiaries_served,
            'distribution_completed_at': self.distribution_completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.distribution_completed_at else None,
            'notes': self.notes
        }
