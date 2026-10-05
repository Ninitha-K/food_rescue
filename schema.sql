-- MySQL Database Schema for AI-Driven Surplus Food Redistribution System
-- Database Name: surplus_food_db

CREATE DATABASE IF NOT EXISTS surplus_food_db;
USE surplus_food_db;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'restaurant', 'ngo', 'volunteer') NOT NULL,
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Restaurants Table
CREATE TABLE IF NOT EXISTS restaurants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(120) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    location VARCHAR(255) NOT NULL,
    latitude DOUBLE DEFAULT 11.0168,
    longitude DOUBLE DEFAULT 76.9558,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. NGOs Table
CREATE TABLE IF NOT EXISTS ngos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(120) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address VARCHAR(255) NOT NULL,
    latitude DOUBLE DEFAULT 11.0168,
    longitude DOUBLE DEFAULT 76.9558,
    accepted_food_types VARCHAR(255) DEFAULT 'Cooked, Bakery, Packaged, Raw Produce',
    current_demand INT DEFAULT 50,
    max_capacity INT DEFAULT 100,
    receiving_hours VARCHAR(50) DEFAULT '08:00 - 22:00',
    service_area VARCHAR(150) DEFAULT 'Central District',
    status ENUM('active', 'inactive') DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Volunteers Table
CREATE TABLE IF NOT EXISTS volunteers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(120) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    current_location VARCHAR(255) NOT NULL,
    latitude DOUBLE DEFAULT 11.0168,
    longitude DOUBLE DEFAULT 76.9558,
    vehicle_type VARCHAR(50) NOT NULL,
    vehicle_capacity INT NOT NULL, -- Capacity in meals/units
    availability_status ENUM('AVAILABLE', 'UNAVAILABLE') DEFAULT 'AVAILABLE',
    max_delivery_distance DOUBLE DEFAULT 15.0, -- Distance in km
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. Food Donations Table
CREATE TABLE IF NOT EXISTS food_donations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_id INT NOT NULL,
    food_name VARCHAR(150) NOT NULL,
    food_category VARCHAR(50) NOT NULL, -- Cooked, Bakery, Packaged, Raw Produce
    quantity INT NOT NULL,
    unit VARCHAR(20) DEFAULT 'meals',
    prepared_time DATETIME NOT NULL,
    expiry_time DATETIME NOT NULL,
    pickup_location VARCHAR(255) NOT NULL,
    latitude DOUBLE DEFAULT 11.0168,
    longitude DOUBLE DEFAULT 76.9558,
    is_veg BOOLEAN DEFAULT TRUE,
    notes TEXT,
    status ENUM('PENDING', 'NGO SELECTED', 'VOLUNTEER ASSIGNED', 'PICKED UP', 'IN TRANSIT', 'DELIVERED', 'DISTRIBUTED') DEFAULT 'PENDING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE
);

-- 6. Allocations Table
CREATE TABLE IF NOT EXISTS allocations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donation_id INT NOT NULL,
    ngo_id INT NOT NULL,
    volunteer_id INT DEFAULT NULL,
    priority_score DOUBLE NOT NULL,
    feasibility_status ENUM('FEASIBLE', 'NOT FEASIBLE') DEFAULT 'FEASIBLE',
    reason_for_selection TEXT,
    estimated_pickup_time_minutes INT,
    estimated_delivery_time_minutes INT,
    allocated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donation_id) REFERENCES food_donations(id) ON DELETE CASCADE,
    FOREIGN KEY (ngo_id) REFERENCES ngos(id) ON DELETE CASCADE,
    FOREIGN KEY (volunteer_id) REFERENCES volunteers(id) ON DELETE SET NULL
);

-- 7. Deliveries Table
CREATE TABLE IF NOT EXISTS deliveries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    allocation_id INT NOT NULL,
    donation_id INT NOT NULL,
    volunteer_id INT NOT NULL,
    status ENUM('ASSIGNED', 'PICKUP_STARTED', 'PICKED_UP', 'IN_TRANSIT', 'NGO_RECEIVED', 'COMPLETED') DEFAULT 'ASSIGNED',
    pickup_started_at DATETIME DEFAULT NULL,
    picked_up_at DATETIME DEFAULT NULL,
    ngo_received_at DATETIME DEFAULT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (allocation_id) REFERENCES allocations(id) ON DELETE CASCADE,
    FOREIGN KEY (donation_id) REFERENCES food_donations(id) ON DELETE CASCADE,
    FOREIGN KEY (volunteer_id) REFERENCES volunteers(id) ON DELETE CASCADE
);

-- 8. Distribution Records Table
CREATE TABLE IF NOT EXISTS distribution_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    delivery_id INT NOT NULL,
    ngo_id INT NOT NULL,
    donation_id INT NOT NULL,
    quantity_received INT NOT NULL,
    quantity_distributed INT NOT NULL,
    beneficiaries_served INT NOT NULL,
    distribution_completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (delivery_id) REFERENCES deliveries(id) ON DELETE CASCADE,
    FOREIGN KEY (ngo_id) REFERENCES ngos(id) ON DELETE CASCADE,
    FOREIGN KEY (donation_id) REFERENCES food_donations(id) ON DELETE CASCADE
);
