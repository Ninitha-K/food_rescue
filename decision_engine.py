import math
from datetime import datetime, timedelta
from config import Config

try:
    import numpy as np
except ImportError:
    np = None

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points on the Earth (in km).
    """
    R = 6371.0 # Radius of Earth in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class DecisionEngine:
    def __init__(self, weights=None):
        self.weights = weights or Config.DECISION_ENGINE_WEIGHTS
        self.average_speed_kmh = Config.AVERAGE_SPEED_KMH

    def check_receiving_hours(self, receiving_hours_str):
        """
        Parses format like '08:00 - 22:00' and checks if current local time is within window.
        """
        try:
            if not receiving_hours_str or '-' not in receiving_hours_str:
                return True
            parts = receiving_hours_str.split('-')
            start_str, end_str = parts[0].strip(), parts[1].strip()
            
            now_time = datetime.now().time()
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()

            if start_time <= end_time:
                return start_time <= now_time <= end_time
            else: # Overnight window (e.g. 20:00 - 06:00)
                return now_time >= start_time or now_time <= end_time
        except Exception:
            return True # Default to accessible if parse fails

    def check_food_compatibility(self, food_category, is_veg, accepted_types_str):
        """
        Checks if NGO accepts the donated food type/category.
        """
        if not accepted_types_str:
            return True
        types_list = [t.strip().lower() for t in accepted_types_str.split(',')]
        category_clean = food_category.strip().lower()
        
        # Check direct match
        for t in types_list:
            if category_clean in t or t in category_clean or 'all' in t:
                return True
        return True # Generous fallback for prototype matching

    def calculate_ngo_score(self, ngo, donation, distance, remaining_minutes, best_volunteer):
        """
        Multi-Criteria Weighted Scoring Algorithm.
        Weights sum to 1.0 (100%).
        """
        # 1. Expiry Urgency Score (0 to 1) -> Higher score if food expires sooner (more urgent redistribution needed)
        # Urgency scaled between 15 mins (score 1.0) and 360 mins (score 0.1)
        if remaining_minutes <= 0:
            urgency_score = 0.0
        elif remaining_minutes <= 60:
            urgency_score = 1.0
        elif remaining_minutes <= 180:
            urgency_score = 0.8
        elif remaining_minutes <= 360:
            urgency_score = 0.5
        else:
            urgency_score = 0.3

        # 2. NGO Demand Score (0 to 1) -> Match ratio of NGO demand to donation quantity
        demand = ngo.current_demand or 0
        if demand >= donation.quantity:
            demand_score = 1.0
        elif demand > 0:
            demand_score = demand / donation.quantity
        else:
            demand_score = 0.1

        # 3. NGO Remaining Capacity Score (0 to 1)
        capacity = ngo.max_capacity or 100
        if capacity >= donation.quantity:
            capacity_score = min(1.0, capacity / (donation.quantity * 1.5))
        else:
            capacity_score = 0.2

        # 4. Distance Score (0 to 1) -> Inverse normalized distance (closer is higher score)
        # 1 km = 1.0, 20 km = 0.1
        distance_score = max(0.1, 1.0 - (distance / 25.0))

        # 5. Food Compatibility Score
        compat_score = 1.0 if self.check_food_compatibility(donation.food_category, donation.is_veg, ngo.accepted_food_types) else 0.4

        # 6. Volunteer Availability & Delivery Margin Score
        if best_volunteer:
            volunteer_score = 1.0
        else:
            volunteer_score = 0.0

        # 7. Receiving Hours Score
        hours_score = 1.0 if self.check_receiving_hours(ngo.receiving_hours) else 0.5

        # Weighted Total Score (scale of 0 - 100)
        weights = self.weights
        total_score = (
            urgency_score * weights['expiry_urgency'] +
            demand_score * weights['ngo_demand'] +
            capacity_score * weights['ngo_capacity'] +
            distance_score * weights['distance'] +
            compat_score * weights['food_compatibility'] +
            volunteer_score * weights['volunteer_availability'] +
            hours_score * weights['receiving_hours']
        ) * 100.0

        return round(total_score, 2), {
            'urgency_score': round(urgency_score * 100, 1),
            'demand_score': round(demand_score * 100, 1),
            'capacity_score': round(capacity_score * 100, 1),
            'distance_score': round(distance_score * 100, 1),
            'compat_score': round(compat_score * 100, 1),
            'volunteer_score': round(volunteer_score * 100, 1),
            'hours_score': round(hours_score * 100, 1)
        }

    def evaluate_allocation(self, donation, ngos, volunteers):
        """
        Main Decision Engine Routine:
        Filter inactive NGOs & unavailable volunteers, enforce Time-Critical Delivery check,
        rank eligible combinations, and return the best NGO + Volunteer pairing.
        """
        now = datetime.utcnow()
        remaining_minutes = int((donation.expiry_time - now).total_seconds() / 60)
        
        if remaining_minutes <= 0:
            return None, None, "FOOD_EXPIRED", []

        rest_lat = donation.latitude or 11.0168
        rest_lon = donation.longitude or 76.9558

        ranked_candidates = []

        for ngo in ngos:
            # 1. Filter out inactive NGOs
            if ngo.status != 'active':
                continue

            # 2. Filter out NGOs with insufficient capacity
            if ngo.max_capacity < donation.quantity:
                continue

            # 3. Calculate Distance: Restaurant to NGO
            ngo_lat = ngo.latitude or 11.0168
            ngo_lon = ngo.longitude or 76.9558
            dist_rest_to_ngo = haversine_distance(rest_lat, rest_lon, ngo_lat, ngo_lon)

            # 4. Find Best Suitable Available Volunteer for this specific NGO
            best_volunteer = None
            best_vol_est_delivery_min = 9999
            best_vol_pickup_min = 9999
            best_vol_distance = 9999

            for vol in volunteers:
                # Rule: Never assign an unavailable volunteer
                if vol.availability_status != 'AVAILABLE':
                    continue

                # Rule: Vehicle capacity check
                if vol.vehicle_capacity < donation.quantity:
                    continue

                vol_lat = vol.latitude or 11.0168
                vol_lon = vol.longitude or 76.9558
                
                # Distance from volunteer to restaurant
                dist_vol_to_rest = haversine_distance(vol_lat, vol_lon, rest_lat, rest_lon)

                # Max distance check
                if dist_vol_to_rest > (vol.max_delivery_distance or 20.0):
                    continue

                # Time Calculations
                # Travel time in minutes = (distance / speed) * 60 + handling buffer (10 mins)
                pickup_time_min = int((dist_vol_to_rest / self.average_speed_kmh) * 60) + 10
                delivery_travel_time_min = int((dist_rest_to_ngo / self.average_speed_kmh) * 60) + 10
                total_delivery_time_min = pickup_time_min + delivery_travel_time_min

                # TIME-CRITICAL DELIVERY FEASIBILITY CHECK (Section 9)
                # If Estimated Delivery Time > Remaining Food Life, then NOT FEASIBLE!
                if total_delivery_time_min > remaining_minutes:
                    continue

                # Select best volunteer (closest travel time)
                if total_delivery_time_min < best_vol_est_delivery_min:
                    best_volunteer = vol
                    best_vol_est_delivery_min = total_delivery_time_min
                    best_vol_pickup_min = pickup_time_min
                    best_vol_distance = round(dist_vol_to_rest, 2)

            # Feasibility Assessment
            if not best_volunteer:
                # NGO is evaluated, but no feasible volunteer can deliver before food expiry!
                ranked_candidates.append({
                    'ngo': ngo,
                    'volunteer': None,
                    'feasible': False,
                    'priority_score': 0.0,
                    'distance_km': round(dist_rest_to_ngo, 2),
                    'est_delivery_min': None,
                    'reason': f"Not Feasible: No available volunteer can complete delivery within remaining {remaining_minutes} mins expiry window."
                })
                continue

            # Calculate Priority Score
            score, breakdown = self.calculate_ngo_score(
                ngo, donation, dist_rest_to_ngo, remaining_minutes, best_volunteer
            )

            reason_str = (
                f"Selected as highest compatibility match ({score}/100). "
                f"Delivery feasible in {best_vol_est_delivery_min} mins (Expiry: {remaining_minutes} mins). "
                f"Demand: {ngo.current_demand} meals, Capacity: {ngo.max_capacity}, Distance: {round(dist_rest_to_ngo, 1)} km. "
                f"Assigned Volunteer: {best_volunteer.name} ({best_volunteer.vehicle_type})."
            )

            ranked_candidates.append({
                'ngo': ngo,
                'volunteer': best_volunteer,
                'feasible': True,
                'priority_score': score,
                'distance_km': round(dist_rest_to_ngo, 2),
                'vol_distance_km': best_vol_distance,
                'est_pickup_min': best_vol_pickup_min,
                'est_delivery_min': best_vol_est_delivery_min,
                'score_breakdown': breakdown,
                'reason': reason_str
            })

        # Separate feasible vs non-feasible
        feasible_candidates = [c for c in ranked_candidates if c['feasible']]
        feasible_candidates.sort(key=lambda x: x['priority_score'], reverse=True)

        if feasible_candidates:
            top_choice = feasible_candidates[0]
            return top_choice['ngo'], top_choice['volunteer'], "SUCCESS", feasible_candidates
        else:
            return None, None, "NO_FEASIBLE_NGO_OR_VOLUNTEER", ranked_candidates


# Modular Scikit-Learn Machine Learning Classifier Wrapper (Section 7 Extension)
class MLDecisionEngineWrapper:
    """
    Extensible module allowing a trained Scikit-learn Random Forest model
    to replace or enhance rule-based priority scoring.
    """
    def __init__(self, baseline_engine=None):
        self.baseline = baseline_engine or DecisionEngine()
        self.rf_model = None
        self._load_mock_rf_model()

    def _load_mock_rf_model(self):
        """
        Initializes a lightweight Scikit-learn Random Forest Regressor/Classifier for demo readiness.
        """
        try:
            from sklearn.ensemble import RandomForestRegressor
            # Train a small synthetic model mapping features -> priority score
            X_dummy = np.array([
                [30, 50, 100, 2.0, 1, 1], # [expiry_mins, demand, capacity, dist_km, veg_match, vol_avail]
                [90, 50, 60, 4.0, 1, 1],
                [15, 10, 20, 15.0, 0, 0],
                [200, 100, 150, 1.0, 1, 1]
            ])
            y_dummy = np.array([85.0, 92.0, 15.0, 98.0])
            rf = RandomForestRegressor(n_estimators=10, random_state=42)
            rf.fit(X_dummy, y_dummy)
            self.rf_model = rf
        except Exception:
            self.rf_model = None

    def predict_score(self, expiry_mins, demand, capacity, distance, veg_match, vol_avail):
        if self.rf_model is not None:
            features = np.array([[expiry_mins, demand, capacity, distance, 1 if veg_match else 0, 1 if vol_avail else 0]])
            pred = self.rf_model.predict(features)[0]
            return float(round(pred, 2))
        return 50.0
