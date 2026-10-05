from datetime import datetime, timedelta
from app import app
from models import db, User, Restaurant, NGO, Volunteer, FoodDonation, Allocation, Delivery, DistributionRecord
from decision_engine import DecisionEngine

def seed_database():
    with app.app_context():
        # Clean existing tables for fresh seed
        db.drop_all()
        db.create_all()
        print("[Seed] Creating initial database tables...")

        # 1. Admin User
        admin_user = User(email='admin@surplus.org', role='admin', status='active')
        admin_user.set_password('admin123')
        db.session.add(admin_user)

        # 2. Restaurants
        rest1_user = User(email='gandhipuram@restaurant.com', role='restaurant', status='active')
        rest1_user.set_password('rest123')
        db.session.add(rest1_user)

        rest2_user = User(email='royal@biryani.com', role='restaurant', status='active')
        rest2_user.set_password('rest123')
        db.session.add(rest2_user)

        # 3. NGOs
        # NGO A (Hope Shelter): Demand 20, Capacity 30, Distance 2 km from Gandhipuram, NO AVAILABLE VOLUNTEER NEARBY
        ngo_a_user = User(email='hopeshelter@ngo.org', role='ngo', status='active')
        ngo_a_user.set_password('ngo123')
        db.session.add(ngo_a_user)

        # NGO B (Care Foundation): Demand 50, Capacity 60, Distance 4 km from Gandhipuram, VOLUNTEER AVAILABLE
        ngo_b_user = User(email='carefoundation@ngo.org', role='ngo', status='active')
        ngo_b_user.set_password('ngo123')
        db.session.add(ngo_b_user)

        # 4. Volunteers
        # Volunteer 1: Ravi Kumar (AVAILABLE, Bike, capacity 60, 4 km radius)
        vol1_user = User(email='ravi@volunteer.org', role='volunteer', status='active')
        vol1_user.set_password('vol123')
        db.session.add(vol1_user)

        # Volunteer 2: Priya Sharma (UNAVAILABLE)
        vol2_user = User(email='priya@volunteer.org', role='volunteer', status='active')
        vol2_user.set_password('vol123')
        db.session.add(vol2_user)

        db.session.commit()

        # Create Profile Records
        # Gandhipuram Kitchen (Lat: 11.0168, Lon: 76.9558)
        rest1 = Restaurant(
            user_id=rest1_user.id,
            name="Gandhipuram Kitchen",
            email="gandhipuram@restaurant.com",
            phone="+91 9876543210",
            location="Gandhipuram Crosscut Road, Coimbatore",
            latitude=11.0168,
            longitude=76.9558
        )
        rest2 = Restaurant(
            user_id=rest2_user.id,
            name="Royal Biryani & Grill",
            email="royal@biryani.com",
            phone="+91 9876543211",
            location="RS Puram, Coimbatore",
            latitude=11.0084,
            longitude=76.9512
        )
        db.session.add_all([rest1, rest2])

        # NGO Profiles
        # NGO A: Hope Shelter (Lat: 11.0348, Lon: 76.9558 ~ 2 km)
        ngo_a = NGO(
            user_id=ngo_a_user.id,
            name="Hope Shelter (NGO A)",
            email="hopeshelter@ngo.org",
            phone="+91 9123456780",
            address="Near Bus Stand, Gandhipuram (2 km)",
            latitude=11.0348,
            longitude=76.9558,
            accepted_food_types="Cooked, Bakery, Packaged",
            current_demand=20,
            max_capacity=30,
            receiving_hours="08:00 - 22:00",
            service_area="Gandhipuram North"
        )
        # NGO B: Care Foundation (Lat: 11.0528, Lon: 76.9558 ~ 4 km)
        ngo_b = NGO(
            user_id=ngo_b_user.id,
            name="Care Foundation (NGO B)",
            email="carefoundation@ngo.org",
            phone="+91 9123456781",
            address="Peelamedu Main Road, Coimbatore (4 km)",
            latitude=11.0528,
            longitude=76.9558,
            accepted_food_types="Cooked, Bakery, Packaged, Raw Produce",
            current_demand=50,
            max_capacity=60,
            receiving_hours="08:00 - 23:00",
            service_area="Peelamedu & Central"
        )
        db.session.add_all([ngo_a, ngo_b])

        # Volunteer Profiles
        vol1 = Volunteer(
            user_id=vol1_user.id,
            name="Ravi Kumar",
            email="ravi@volunteer.org",
            phone="+91 9988776655",
            current_location="Gandhipuram Junction",
            latitude=11.0180,
            longitude=76.9560,
            vehicle_type="Motorbike with Delivery Box",
            vehicle_capacity=60,
            availability_status="AVAILABLE",
            max_delivery_distance=15.0
        )
        vol2 = Volunteer(
            user_id=vol2_user.id,
            name="Priya Sharma",
            email="priya@volunteer.org",
            phone="+91 9988776656",
            current_location="Singanallur",
            latitude=10.9980,
            longitude=77.0160,
            vehicle_type="Scooter",
            vehicle_capacity=30,
            availability_status="UNAVAILABLE", # Explicitly unavailable for NGO A zone
            max_delivery_distance=10.0
        )
        db.session.add_all([vol1, vol2])
        db.session.commit()

        # Seed Demo Scenario Food Donation (Section 17 Requirement)
        # 50 meals, preparing now, expiring in 90 minutes
        now = datetime.utcnow()
        expiry_90m = now + timedelta(minutes=90)

        demo_donation = FoodDonation(
            restaurant_id=rest1.id,
            food_name="Fresh Vegetable Rice & Curry Meals",
            food_category="Cooked",
            quantity=50,
            unit="meals",
            prepared_time=now - timedelta(minutes=15),
            expiry_time=expiry_90m,
            pickup_location="Gandhipuram Kitchen, Main Counter",
            latitude=11.0168,
            longitude=76.9558,
            is_veg=True,
            notes="Hot meals packed in insulated containers. Needs urgent redistribution within 90 mins.",
            status="PENDING"
        )
        db.session.add(demo_donation)
        db.session.commit()

        # Run Decision Engine on Demo Donation to demonstrate automatic allocation
        engine = DecisionEngine()
        ngos_list = [ngo_a, ngo_b]
        vols_list = [vol1, vol2]

        selected_ngo, selected_vol, status, candidates = engine.evaluate_allocation(
            demo_donation, ngos_list, vols_list
        )

        if selected_ngo and selected_vol:
            demo_donation.status = "VOLUNTEER ASSIGNED"
            
            # Find candidate info for top selection
            top_cand = [c for c in candidates if c['ngo'].id == selected_ngo.id and c['feasible']][0]

            allocation = Allocation(
                donation_id=demo_donation.id,
                ngo_id=selected_ngo.id,
                volunteer_id=selected_vol.id,
                priority_score=top_cand['priority_score'],
                feasibility_status='FEASIBLE',
                reason_for_selection=top_cand['reason'],
                estimated_pickup_time_minutes=top_cand['est_pickup_min'],
                estimated_delivery_time_minutes=top_cand['est_delivery_min']
            )
            db.session.add(allocation)
            db.session.commit()

            # Create Delivery record
            delivery = Delivery(
                allocation_id=allocation.id,
                donation_id=demo_donation.id,
                volunteer_id=selected_vol.id,
                status="ASSIGNED"
            )
            db.session.add(delivery)
            db.session.commit()

            print(f"[Seed Demo Scenario Success] Donation #{demo_donation.id} allocated to {selected_ngo.name} via Volunteer {selected_vol.name}. Feasibility: FEASIBLE in {top_cand['est_delivery_min']} mins.")

        # Seed an additional past completed donation record for rich visualization
        past_donation = FoodDonation(
            restaurant_id=rest2.id,
            food_name="Paneer Biryani & Salad",
            food_category="Cooked",
            quantity=35,
            unit="meals",
            prepared_time=now - timedelta(hours=5),
            expiry_time=now - timedelta(hours=1),
            pickup_location="Royal Biryani RS Puram",
            latitude=11.0084,
            longitude=76.9512,
            is_veg=True,
            notes="Completed afternoon redistribution batch.",
            status="DISTRIBUTED"
        )
        db.session.add(past_donation)
        db.session.commit()

        past_alloc = Allocation(
            donation_id=past_donation.id,
            ngo_id=ngo_b.id,
            volunteer_id=vol1.id,
            priority_score=94.5,
            feasibility_status='FEASIBLE',
            reason_for_selection="High compatibility match. Completed within 35 minutes.",
            estimated_pickup_time_minutes=12,
            estimated_delivery_time_minutes=35
        )
        db.session.add(past_alloc)
        db.session.commit()

        past_delivery = Delivery(
            allocation_id=past_alloc.id,
            donation_id=past_donation.id,
            volunteer_id=vol1.id,
            status="COMPLETED",
            pickup_started_at=now - timedelta(hours=4, minutes=30),
            picked_up_at=now - timedelta(hours=4, minutes=15),
            ngo_received_at=now - timedelta(hours=3, minutes=45)
        )
        db.session.add(past_delivery)
        db.session.commit()

        dist_record = DistributionRecord(
            delivery_id=past_delivery.id,
            ngo_id=ngo_b.id,
            donation_id=past_donation.id,
            quantity_received=35,
            quantity_distributed=35,
            beneficiaries_served=42,
            distribution_completed_at=now - timedelta(hours=3),
            notes="Distributed to evening shelter residents."
        )
        db.session.add(dist_record)
        db.session.commit()

        print("[Seed] Database seeded with Demo Scenario and initial accounts successfully!")

if __name__ == '__main__':
    seed_database()
