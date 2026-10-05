import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from config import Config
from models import db, User, Restaurant, NGO, Volunteer, FoodDonation, Allocation, Delivery, DistributionRecord
from decision_engine import DecisionEngine, MLDecisionEngineWrapper

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

decision_engine = DecisionEngine()
ml_wrapper = MLDecisionEngineWrapper(decision_engine)

# Context processor for current user role and profile in templates
@app.context_processor
def inject_user():
    user = None
    role = session.get('role')
    user_id = session.get('user_id')
    profile = None
    if user_id:
        user = User.query.get(user_id)
        if user:
            if user.role == 'restaurant':
                profile = user.restaurant
            elif user.role == 'ngo':
                profile = user.ngo
            elif user.role == 'volunteer':
                profile = user.volunteer
    return dict(current_user=user, current_role=role, current_profile=profile)

# Helper decorator for role checking
def role_required(*allowed_roles):
    def decorator(f):
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') not in allowed_roles:
                flash('Unauthorized access for your user role.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        wrapped.__name__ = f.__name__
        return wrapped
    return decorator

# Data Normalization Helper for External Interoperability (Section 12)
def normalize_external_donation_payload(data):
    """
    Normalizes external system payload schema to internal standard format.
    Example external schema:
    { "meal_count": 50, "expire_in_hours": 1.5, "address": "Gandhipuram", "dish": "Veg Meals" }
    Internal format:
    { "food_name": "Veg Meals", "quantity": 50, "expiry_time": ..., "pickup_location": "Gandhipuram" }
    """
    food_name = data.get('food_name') or data.get('dish') or data.get('item_name') or 'Surplus Food Batch'
    quantity = int(data.get('quantity') or data.get('meal_count') or data.get('count') or 10)
    food_category = data.get('food_category') or data.get('category') or 'Cooked'
    unit = data.get('unit') or 'meals'
    pickup_location = data.get('pickup_location') or data.get('address') or data.get('location') or 'Restaurant Location'
    is_veg = data.get('is_veg', True)
    if 'veg' in str(data.get('type', '')).lower():
        is_veg = True
    elif 'non-veg' in str(data.get('type', '')).lower():
        is_veg = False

    # Expiry parsing
    now = datetime.utcnow()
    if 'expire_in_minutes' in data:
        expiry_time = now + timedelta(minutes=int(data['expire_in_minutes']))
    elif 'expire_in_hours' in data:
        expiry_time = now + timedelta(hours=float(data['expire_in_hours']))
    elif 'expiry_time' in data:
        try:
            expiry_time = datetime.strptime(data['expiry_time'], '%Y-%m-%d %H:%M:%S')
        except Exception:
            expiry_time = now + timedelta(hours=2)
    else:
        expiry_time = now + timedelta(hours=2)

    return {
        'food_name': food_name,
        'food_category': food_category,
        'quantity': quantity,
        'unit': unit,
        'prepared_time': now,
        'expiry_time': expiry_time,
        'pickup_location': pickup_location,
        'is_veg': is_veg,
        'notes': data.get('notes') or data.get('description') or 'Received via External REST API Interoperability Endpoint',
        'latitude': float(data.get('latitude') or 11.0168),
        'longitude': float(data.get('longitude') or 76.9558)
    }


# ==========================================
# WEB ROUTES
# ==========================================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.status != 'active':
                flash('Your account is currently inactive. Please contact system admin.', 'danger')
                return redirect(url_for('login'))
            
            session['user_id'] = user.id
            session['email'] = user.email
            session['role'] = user.role
            flash(f'Logged in as {user.email} ({user.role.upper()})!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/quick-login/<role>')
def quick_login(role):
    email_map = {
        'admin': 'admin@surplus.org',
        'restaurant': 'gandhipuram@restaurant.com',
        'ngo': 'carefoundation@ngo.org',
        'volunteer': 'ravi@volunteer.org'
    }
    target_email = email_map.get(role.lower())
    if not target_email:
        flash('Invalid role for quick login.', 'danger')
        return redirect(url_for('login'))
    
    user = User.query.filter_by(email=target_email).first()
    if user:
        session['user_id'] = user.id
        session['email'] = user.email
        session['role'] = user.role
        flash(f'Active Session Switched: Logged in as {user.email} ({user.role.upper()})', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash(f'Account for {role} not found. Please register or seed database.', 'warning')
        return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '')

        if User.query.filter_by(email=email).first():
            flash('Email address already registered.', 'danger')
            return redirect(url_for('register'))

        if role not in ['restaurant', 'ngo', 'volunteer']:
            flash('Invalid user role selected.', 'danger')
            return redirect(url_for('register'))

        user = User(email=email, role=role, status='active')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Create Profile depending on role
        if role == 'restaurant':
            rest = Restaurant(
                user_id=user.id,
                name=request.form.get('name', 'Restaurant Partner'),
                email=email,
                phone=request.form.get('phone', ''),
                location=request.form.get('location', 'Gandhipuram, Coimbatore'),
                latitude=float(request.form.get('latitude', 11.0168)),
                longitude=float(request.form.get('longitude', 76.9558))
            )
            db.session.add(rest)
        elif role == 'ngo':
            ngo = NGO(
                user_id=user.id,
                name=request.form.get('name', 'NGO Partner'),
                email=email,
                phone=request.form.get('phone', ''),
                address=request.form.get('location', 'Central District, Coimbatore'),
                accepted_food_types=request.form.get('accepted_food_types', 'Cooked, Bakery, Packaged'),
                current_demand=int(request.form.get('current_demand', 50)),
                max_capacity=int(request.form.get('max_capacity', 100)),
                receiving_hours=request.form.get('receiving_hours', '08:00 - 22:00'),
                latitude=float(request.form.get('latitude', 11.0168)),
                longitude=float(request.form.get('longitude', 76.9558))
            )
            db.session.add(ngo)
        elif role == 'volunteer':
            vol = Volunteer(
                user_id=user.id,
                name=request.form.get('name', 'Volunteer Hero'),
                email=email,
                phone=request.form.get('phone', ''),
                current_location=request.form.get('location', 'Gandhipuram Junction'),
                vehicle_type=request.form.get('vehicle_type', 'Motorbike'),
                vehicle_capacity=int(request.form.get('vehicle_capacity', 50)),
                availability_status='AVAILABLE',
                max_delivery_distance=float(request.form.get('max_delivery_distance', 15.0)),
                latitude=float(request.form.get('latitude', 11.0168)),
                longitude=float(request.form.get('longitude', 76.9558))
            )
            db.session.add(vol)

        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    role = session.get('role')
    user_id = session.get('user_id')

    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'restaurant':
        return redirect(url_for('restaurant_dashboard'))
    elif role == 'ngo':
        return redirect(url_for('ngo_dashboard'))
    elif role == 'volunteer':
        return redirect(url_for('volunteer_dashboard'))
    
    return redirect(url_for('index'))


# ------------------------------------------
# ADMIN MODULE
# ------------------------------------------
@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    total_restaurants = Restaurant.query.count()
    total_ngos = NGO.query.count()
    total_volunteers = Volunteer.query.count()
    active_donations = FoodDonation.query.filter(FoodDonation.status.in_(['PENDING', 'NGO SELECTED', 'VOLUNTEER ASSIGNED', 'PICKED UP', 'IN TRANSIT'])).count()
    pending_allocations = FoodDonation.query.filter_by(status='PENDING').count()
    active_deliveries = Delivery.query.filter(Delivery.status.in_(['ASSIGNED', 'PICKUP_STARTED', 'PICKED_UP', 'IN_TRANSIT'])).count()
    completed_deliveries = Delivery.query.filter_by(status='COMPLETED').count()

    # Approaching expiry (remaining life < 60 minutes)
    now = datetime.utcnow()
    approaching_expiry = FoodDonation.query.filter(
        FoodDonation.status != 'DISTRIBUTED',
        FoodDonation.expiry_time > now,
        FoodDonation.expiry_time <= now + timedelta(minutes=60)
    ).all()

    restaurants = Restaurant.query.all()
    ngos = NGO.query.all()
    volunteers = Volunteer.query.all()
    donations = FoodDonation.query.order_by(FoodDonation.id.desc()).all()
    allocations = Allocation.query.order_by(Allocation.id.desc()).all()
    deliveries = Delivery.query.order_by(Delivery.id.desc()).all()
    users = User.query.all()

    return render_template(
        'admin_dashboard.html',
        total_restaurants=total_restaurants,
        total_ngos=total_ngos,
        total_volunteers=total_volunteers,
        active_donations=active_donations,
        pending_allocations=pending_allocations,
        active_deliveries=active_deliveries,
        completed_deliveries=completed_deliveries,
        approaching_expiry=approaching_expiry,
        restaurants=restaurants,
        ngos=ngos,
        volunteers=volunteers,
        donations=donations,
        allocations=allocations,
        deliveries=deliveries,
        users=users
    )


@app.route('/admin/user/<int:user_id>/toggle-status', methods=['POST'])
@role_required('admin')
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot deactivate Admin account.', 'warning')
        return redirect(url_for('admin_dashboard'))
    
    user.status = 'inactive' if user.status == 'active' else 'active'
    db.session.commit()
    flash(f'User {user.email} status updated to {user.status.upper()}.', 'success')
    return redirect(url_for('admin_dashboard'))


# ------------------------------------------
# RESTAURANT MODULE
# ------------------------------------------
@app.route('/restaurant/dashboard')
@role_required('restaurant')
def restaurant_dashboard():
    user = User.query.get(session['user_id'])
    restaurant = user.restaurant
    if not restaurant:
        flash('Restaurant profile not found.', 'danger')
        return redirect(url_for('logout'))

    donations = FoodDonation.query.filter_by(restaurant_id=restaurant.id).order_by(FoodDonation.id.desc()).all()
    return render_template('restaurant_dashboard.html', restaurant=restaurant, donations=donations)


@app.route('/restaurant/donate', methods=['POST'])
@role_required('restaurant')
def create_donation():
    user = User.query.get(session['user_id'])
    restaurant = user.restaurant
    
    food_name = request.form.get('food_name', '').strip()
    food_category = request.form.get('food_category', 'Cooked')
    quantity = int(request.form.get('quantity', 0))
    unit = request.form.get('unit', 'meals')
    pickup_location = request.form.get('pickup_location', restaurant.location)
    is_veg = request.form.get('is_veg') == '1'
    notes = request.form.get('notes', '')
    expiry_hours = float(request.form.get('expiry_hours', 2.0))

    now = datetime.utcnow()
    expiry_time = now + timedelta(hours=expiry_hours)

    donation = FoodDonation(
        restaurant_id=restaurant.id,
        food_name=food_name,
        food_category=food_category,
        quantity=quantity,
        unit=unit,
        prepared_time=now,
        expiry_time=expiry_time,
        pickup_location=pickup_location,
        latitude=restaurant.latitude,
        longitude=restaurant.longitude,
        is_veg=is_veg,
        notes=notes,
        status='PENDING'
    )
    db.session.add(donation)
    db.session.commit()

    # Trigger Food Allocation Decision Engine automatically
    ngos = NGO.query.filter_by(status='active').all()
    volunteers = Volunteer.query.all()

    selected_ngo, selected_vol, status_code, candidates = decision_engine.evaluate_allocation(
        donation, ngos, volunteers
    )

    if selected_ngo and selected_vol:
        donation.status = 'VOLUNTEER ASSIGNED'
        top_cand = [c for c in candidates if c['ngo'].id == selected_ngo.id and c['feasible']][0]

        allocation = Allocation(
            donation_id=donation.id,
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

        delivery = Delivery(
            allocation_id=allocation.id,
            donation_id=donation.id,
            volunteer_id=selected_vol.id,
            status='ASSIGNED'
        )
        db.session.add(delivery)
        db.session.commit()

        flash(f'Donation #{donation.id} submitted! Decision Engine matched {selected_ngo.name} (Score: {top_cand["priority_score"]}) with Volunteer {selected_vol.name}. Estimated delivery in {top_cand["est_delivery_min"]} mins.', 'success')
    else:
        flash(f'Donation #{donation.id} recorded. Decision Engine status: {status_code}. Pending feasible volunteer/NGO match.', 'warning')

    return redirect(url_for('restaurant_dashboard'))


# ------------------------------------------
# NGO MODULE
# ------------------------------------------
@app.route('/ngo/dashboard')
@role_required('ngo')
def ngo_dashboard():
    user = User.query.get(session['user_id'])
    ngo = user.ngo
    if not ngo:
        flash('NGO profile not found.', 'danger')
        return redirect(url_for('logout'))

    # Active incoming allocations for this NGO
    incoming_allocations = Allocation.query.filter_by(ngo_id=ngo.id).order_by(Allocation.id.desc()).all()
    received_history = DistributionRecord.query.filter_by(ngo_id=ngo.id).order_by(DistributionRecord.id.desc()).all()

    return render_template('ngo_dashboard.html', ngo=ngo, allocations=incoming_allocations, history=received_history)


@app.route('/ngo/update-capacity', methods=['POST'])
@role_required('ngo')
def ngo_update_capacity():
    user = User.query.get(session['user_id'])
    ngo = user.ngo
    
    demand = int(request.form.get('current_demand', ngo.current_demand))
    capacity = int(request.form.get('max_capacity', ngo.max_capacity))
    
    ngo.current_demand = demand
    ngo.max_capacity = capacity
    db.session.commit()

    flash('Current demand and capacity updated successfully.', 'success')
    return redirect(url_for('ngo_dashboard'))


@app.route('/ngo/distribute/<int:delivery_id>', methods=['POST'])
@role_required('ngo')
def ngo_record_distribution(delivery_id):
    user = User.query.get(session['user_id'])
    ngo = user.ngo

    delivery = Delivery.query.get_or_404(delivery_id)
    donation = delivery.donation

    qty_received = int(request.form.get('quantity_received', donation.quantity))
    qty_distributed = int(request.form.get('quantity_distributed', qty_received))
    beneficiaries = int(request.form.get('beneficiaries_served', qty_distributed))
    notes = request.form.get('notes', 'Distribution completed at NGO premises.')

    # Update delivery & donation status
    delivery.status = 'COMPLETED'
    donation.status = 'DISTRIBUTED'

    # Deduct demand from NGO
    ngo.current_demand = max(0, ngo.current_demand - qty_distributed)

    record = DistributionRecord(
        delivery_id=delivery.id,
        ngo_id=ngo.id,
        donation_id=donation.id,
        quantity_received=qty_received,
        quantity_distributed=qty_distributed,
        beneficiaries_served=beneficiaries,
        notes=notes
    )
    db.session.add(record)
    db.session.commit()

    flash(f'Distribution recorded! Served {beneficiaries} beneficiaries with {qty_distributed} meals.', 'success')
    return redirect(url_for('ngo_dashboard'))


# ------------------------------------------
# VOLUNTEER MODULE
# ------------------------------------------
@app.route('/volunteer/dashboard')
@role_required('volunteer')
def volunteer_dashboard():
    user = User.query.get(session['user_id'])
    volunteer = user.volunteer
    if not volunteer:
        flash('Volunteer profile not found.', 'danger')
        return redirect(url_for('logout'))

    assigned_deliveries = Delivery.query.filter_by(volunteer_id=volunteer.id).order_by(Delivery.id.desc()).all()
    return render_template('volunteer_dashboard.html', volunteer=volunteer, deliveries=assigned_deliveries)


@app.route('/volunteer/toggle-availability', methods=['POST'])
@role_required('volunteer')
def toggle_volunteer_availability():
    user = User.query.get(session['user_id'])
    volunteer = user.volunteer
    
    volunteer.availability_status = 'UNAVAILABLE' if volunteer.availability_status == 'AVAILABLE' else 'AVAILABLE'
    db.session.commit()

    flash(f'Your status is now {volunteer.availability_status}.', 'info')
    return redirect(url_for('volunteer_dashboard'))


# ------------------------------------------
# DELIVERY TRACKING & STATUS UPDATES
# ------------------------------------------
@app.route('/delivery/<int:delivery_id>')
def delivery_tracking(delivery_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    delivery = Delivery.query.get_or_404(delivery_id)
    return render_template('delivery_tracking.html', delivery=delivery)


@app.route('/delivery/<int:delivery_id>/update-status', methods=['POST'])
def update_delivery_status(delivery_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    delivery = Delivery.query.get_or_404(delivery_id)
    donation = delivery.donation
    new_status = request.form.get('status')

    valid_statuses = ['PICKUP_STARTED', 'PICKED_UP', 'IN_TRANSIT', 'NGO_RECEIVED', 'COMPLETED']
    if new_status in valid_statuses:
        delivery.status = new_status
        now = datetime.utcnow()

        if new_status == 'PICKUP_STARTED':
            delivery.pickup_started_at = now
            donation.status = 'VOLUNTEER ASSIGNED'
        elif new_status == 'PICKED_UP':
            delivery.picked_up_at = now
            donation.status = 'PICKED UP'
        elif new_status == 'IN_TRANSIT':
            donation.status = 'IN TRANSIT'
        elif new_status == 'NGO_RECEIVED':
            delivery.ngo_received_at = now
            donation.status = 'DELIVERED'

        db.session.commit()
        flash(f'Delivery status updated to {new_status.replace("_", " ")}.', 'success')

    return redirect(url_for('delivery_tracking', delivery_id=delivery.id))


@app.route('/api-docs')
def api_docs():
    return render_template('api_docs.html')


# ==========================================
# REST API ENDPOINTS (Section 12 Requirements)
# ==========================================

@app.route('/api/restaurants', methods=['GET'])
def api_get_restaurants():
    restaurants = Restaurant.query.all()
    return jsonify({'status': 'success', 'data': [r.to_dict() for r in restaurants]})


@app.route('/api/restaurants/<int:restaurant_id>/surplus', methods=['GET'])
def api_get_restaurant_surplus(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    donations = FoodDonation.query.filter_by(restaurant_id=restaurant.id).all()
    return jsonify({
        'status': 'success',
        'restaurant': restaurant.to_dict(),
        'surplus_donations': [d.to_dict() for d in donations]
    })


@app.route('/api/ngos', methods=['GET'])
def api_get_ngos():
    ngos = NGO.query.all()
    return jsonify({'status': 'success', 'data': [n.to_dict() for n in ngos]})


@app.route('/api/ngos/<int:ngo_id>/demand', methods=['GET'])
def api_get_ngo_demand(ngo_id):
    ngo = NGO.query.get_or_404(ngo_id)
    return jsonify({
        'status': 'success',
        'id': ngo.id,
        'name': ngo.name,
        'current_demand': ngo.current_demand,
        'max_capacity': ngo.max_capacity,
        'accepted_food_types': ngo.accepted_food_types
    })


@app.route('/api/volunteers/available', methods=['GET'])
def api_get_available_volunteers():
    volunteers = Volunteer.query.filter_by(availability_status='AVAILABLE').all()
    return jsonify({'status': 'success', 'count': len(volunteers), 'data': [v.to_dict() for v in volunteers]})


@app.route('/api/donations', methods=['POST'])
def api_create_donation():
    """
    Accepts standardized JSON or normalized payload from external systems (Section 12).
    """
    data = request.get_json() or {}
    restaurant_id = data.get('restaurant_id')
    
    if not restaurant_id:
        # Fallback to default demo restaurant if external system doesn't specify ID
        rest = Restaurant.query.first()
        restaurant_id = rest.id if rest else 1

    # Normalize payload
    normalized = normalize_external_donation_payload(data)

    donation = FoodDonation(
        restaurant_id=restaurant_id,
        food_name=normalized['food_name'],
        food_category=normalized['food_category'],
        quantity=normalized['quantity'],
        unit=normalized['unit'],
        prepared_time=normalized['prepared_time'],
        expiry_time=normalized['expiry_time'],
        pickup_location=normalized['pickup_location'],
        latitude=normalized['latitude'],
        longitude=normalized['longitude'],
        is_veg=normalized['is_veg'],
        notes=normalized['notes'],
        status='PENDING'
    )
    db.session.add(donation)
    db.session.commit()

    # Trigger Decision Engine
    ngos = NGO.query.filter_by(status='active').all()
    volunteers = Volunteer.query.all()

    selected_ngo, selected_vol, status_code, candidates = decision_engine.evaluate_allocation(
        donation, ngos, volunteers
    )

    result_data = {'donation': donation.to_dict(), 'allocation': None}

    if selected_ngo and selected_vol:
        donation.status = 'VOLUNTEER ASSIGNED'
        top_cand = [c for c in candidates if c['ngo'].id == selected_ngo.id and c['feasible']][0]

        allocation = Allocation(
            donation_id=donation.id,
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

        delivery = Delivery(
            allocation_id=allocation.id,
            donation_id=donation.id,
            volunteer_id=selected_vol.id,
            status='ASSIGNED'
        )
        db.session.add(delivery)
        db.session.commit()

        result_data['allocation'] = allocation.to_dict()
        result_data['delivery_id'] = delivery.id

    return jsonify({'status': 'success', 'message': 'Donation received and evaluated', 'data': result_data}), 201


@app.route('/api/allocations', methods=['POST'])
def api_trigger_allocation():
    data = request.get_json() or {}
    donation_id = data.get('donation_id')
    donation = FoodDonation.query.get_or_404(donation_id)

    ngos = NGO.query.filter_by(status='active').all()
    volunteers = Volunteer.query.all()

    selected_ngo, selected_vol, status_code, candidates = decision_engine.evaluate_allocation(
        donation, ngos, volunteers
    )

    if selected_ngo and selected_vol:
        donation.status = 'VOLUNTEER ASSIGNED'
        top_cand = [c for c in candidates if c['ngo'].id == selected_ngo.id and c['feasible']][0]

        allocation = Allocation(
            donation_id=donation.id,
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

        return jsonify({'status': 'success', 'allocation': allocation.to_dict()})
    
    return jsonify({'status': 'error', 'reason': status_code, 'candidates_evaluated': len(candidates)}), 400


@app.route('/api/deliveries/<int:delivery_id>/status', methods=['PUT'])
def api_update_delivery_status(delivery_id):
    delivery = Delivery.query.get_or_404(delivery_id)
    data = request.get_json() or {}
    new_status = data.get('status')

    valid_statuses = ['ASSIGNED', 'PICKUP_STARTED', 'PICKED_UP', 'IN_TRANSIT', 'NGO_RECEIVED', 'COMPLETED']
    if new_status not in valid_statuses:
        return jsonify({'status': 'error', 'message': f'Invalid status. Allowed: {valid_statuses}'}), 400

    delivery.status = new_status
    now = datetime.utcnow()
    if new_status == 'PICKUP_STARTED':
        delivery.pickup_started_at = now
    elif new_status == 'PICKED_UP':
        delivery.picked_up_at = now
        delivery.donation.status = 'PICKED UP'
    elif new_status == 'IN_TRANSIT':
        delivery.donation.status = 'IN TRANSIT'
    elif new_status == 'NGO_RECEIVED':
        delivery.ngo_received_at = now
        delivery.donation.status = 'DELIVERED'

    db.session.commit()
    return jsonify({'status': 'success', 'delivery': delivery.to_dict()})


@app.route('/api/stats', methods=['GET'])
def api_get_system_stats():
    donations_by_status = {
        'PENDING': FoodDonation.query.filter_by(status='PENDING').count(),
        'VOLUNTEER_ASSIGNED': FoodDonation.query.filter_by(status='VOLUNTEER ASSIGNED').count(),
        'PICKED_UP': FoodDonation.query.filter_by(status='PICKED UP').count(),
        'IN_TRANSIT': FoodDonation.query.filter_by(status='IN TRANSIT').count(),
        'DELIVERED': FoodDonation.query.filter_by(status='DELIVERED').count(),
        'DISTRIBUTED': FoodDonation.query.filter_by(status='DISTRIBUTED').count()
    }
    
    total_meals_redistributed = db.session.query(db.func.sum(DistributionRecord.quantity_distributed)).scalar() or 0
    total_beneficiaries = db.session.query(db.func.sum(DistributionRecord.beneficiaries_served)).scalar() or 0

    return jsonify({
        'status': 'success',
        'donations_by_status': donations_by_status,
        'total_meals_redistributed': total_meals_redistributed,
        'total_beneficiaries_served': total_beneficiaries,
        'active_deliveries': Delivery.query.filter(Delivery.status.in_(['ASSIGNED', 'PICKUP_STARTED', 'PICKED_UP', 'IN_TRANSIT'])).count(),
        'completed_deliveries': Delivery.query.filter_by(status='COMPLETED').count()
    })


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
