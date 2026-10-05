import unittest
from datetime import datetime, timedelta
from app import app, db
from models import User, Restaurant, NGO, Volunteer, FoodDonation, Allocation, Delivery, DistributionRecord

class SurplusFoodSystemTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.drop_all()
        db.create_all()
        self._seed_test_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _seed_test_data(self):
        # Create Test Users
        r_user = User(email='rest_unique@test.com', role='restaurant', status='active')
        r_user.set_password('pass123')
        
        n_user_a = User(email='ngo_a_unique@test.com', role='ngo', status='active')
        n_user_a.set_password('pass123')

        n_user_b = User(email='ngo_b_unique@test.com', role='ngo', status='active')
        n_user_b.set_password('pass123')

        v_user = User(email='vol_unique@test.com', role='volunteer', status='active')
        v_user.set_password('pass123')

        db.session.add_all([r_user, n_user_a, n_user_b, v_user])
        db.session.commit()

        # Profiles
        self.restaurant = Restaurant(
            user_id=r_user.id, name="Gandhipuram Test Kitchen", email="rest_unique@test.com",
            phone="1234567890", location="Gandhipuram", latitude=11.0168, longitude=76.9558
        )
        # NGO A: Close (2km), NO VOLUNTEER NEARBY
        self.ngo_a = NGO(
            user_id=n_user_a.id, name="Hope Shelter NGO A", email="ngo_a_unique@test.com",
            phone="1234567891", address="Gandhipuram 2km", latitude=11.0348, longitude=76.9558,
            current_demand=20, max_capacity=30
        )
        # NGO B: Further (4km), VOLUNTEER AVAILABLE
        self.ngo_b = NGO(
            user_id=n_user_b.id, name="Care Foundation NGO B", email="ngo_b_unique@test.com",
            phone="1234567892", address="Peelamedu 4km", latitude=11.0528, longitude=76.9558,
            current_demand=50, max_capacity=60
        )
        # Volunteer for NGO B
        self.vol = Volunteer(
            user_id=v_user.id, name="Ravi Test Volunteer", email="vol_unique@test.com",
            phone="9988776655", current_location="Gandhipuram Junction",
            latitude=11.0180, longitude=76.9560, vehicle_type="Motorbike",
            vehicle_capacity=60, availability_status="AVAILABLE", max_delivery_distance=15.0
        )
        db.session.add_all([self.restaurant, self.ngo_a, self.ngo_b, self.vol])
        db.session.commit()

    def test_demo_scenario_allocation(self):
        """
        Verify Demo Scenario: 50 meals expiring in 90 minutes.
        NGO A is 2km away but has no available volunteer -> NOT FEASIBLE.
        NGO B is 4km away with volunteer available -> FEASIBLE & SELECTED.
        """
        response = self.client.post('/api/donations', json={
            "dish": "Test Veg Feast",
            "category": "Cooked",
            "meal_count": 50,
            "expire_in_minutes": 90,
            "address": "Gandhipuram Test Kitchen",
            "restaurant_id": self.restaurant.id
        })
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIsNotNone(data['data']['allocation'])
        
        allocation = data['data']['allocation']
        self.assertEqual(allocation['ngo_id'], self.ngo_b.id)
        self.assertEqual(allocation['volunteer_id'], self.vol.id)
        self.assertTrue(allocation['priority_score'] > 0)

    def test_api_endpoints(self):
        res_r = self.client.get('/api/restaurants')
        self.assertEqual(res_r.status_code, 200)

        res_n = self.client.get('/api/ngos')
        self.assertEqual(res_n.status_code, 200)

        res_v = self.client.get('/api/volunteers/available')
        self.assertEqual(res_v.status_code, 200)

        res_s = self.client.get('/api/stats')
        self.assertEqual(res_s.status_code, 200)

if __name__ == '__main__':
    unittest.main()
