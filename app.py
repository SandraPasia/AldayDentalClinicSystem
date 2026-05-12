from flask import Flask, render_template, request, jsonify, redirect, session, make_response
import json, os, urllib.request, urllib.parse, uuid, random
from datetime import datetime
from functools import wraps

from models import db, Booking, Message, Payment, Feedback, Setting

app = Flask(__name__)

import os

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT', '3306')}/"
    f"{os.getenv('DB_NAME')}"
)

db.init_app(app)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'alday2025'

SEMAPHORE_API_KEY  = 'YOUR_SEMAPHORE_API_KEY_HERE'
SEMAPHORE_SENDER   = 'AldayDental'
SEMAPHORE_API_URL  = 'https://api.semaphore.co/api/v4/messages'
CLINIC_WEBSITE     = 'https://yourwebsite.com'

SERVICES = [
    {'name': 'General Dentistry',    'price': 'Starting ₱5000'},
    {'name': 'Restoration/Fillings', 'price': 'Starting ₱2,000'},
    {'name': 'Orthodontics',         'price': 'Starting ₱60,000'},
    {'name': 'Prosthodontics',       'price': 'Starting ₱5,0000'},
    {'name': 'Oral Surgery',         'price': 'Starting ₱5000'},
    {'name': 'Pediatric Dentistry',  'price': 'Starting ₱1500'},
    {'name': 'Consultation',         'price': 'Starting ₱600'},
]


# ── Helpers ────────────────────────────────────────────────────────────────

def generate_patient_id():
    while True:
        pid = 'ADC-' + str(random.randint(10000, 99999))
        if not Booking.query.filter_by(patient_id=pid).first():
            return pid


def send_sms(phone, message):
    if not SEMAPHORE_API_KEY or SEMAPHORE_API_KEY == 'YOUR_SEMAPHORE_API_KEY_HERE':
        print(f'[SMS SKIPPED] No API key set. Message for {phone}: {message}')
        return False
    try:
        number = phone.strip()
        if number.startswith('09'):
            number = '63' + number[1:]
        elif number.startswith('+63'):
            number = number[1:]
        payload = urllib.parse.urlencode({
            'apikey':     SEMAPHORE_API_KEY,
            'number':     number,
            'message':    message,
            'sendername': SEMAPHORE_SENDER,
        }).encode('utf-8')
        req  = urllib.request.Request(SEMAPHORE_API_URL, data=payload, method='POST')
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
        print(f'[SMS SENT] {phone} → status: {result}')
        return True
    except Exception as e:
        print(f'[SMS ERROR] {e}')
        return False


def sms_booking_received(booking):
    b = booking.to_dict() if hasattr(booking, 'to_dict') else booking
    pid_line = f"Your Patient ID: {b.get('patient_id', '')}. " if b.get('patient_id') else ''
    msg = (
        f"Hi {b['first_name']}! We received your appointment request at "
        f"Alday Dental Clinic ({b.get('branch','')}) on "
        f"{b.get('date','')} at {b.get('time','')} for "
        f"{b.get('service','')}. {pid_line}"
        f"We will confirm your appointment shortly. "
        f"To check your status or cancel, visit: {CLINIC_WEBSITE}/status"
    )
    send_sms(b['phone'], msg)


def sms_booking_confirmed(booking):
    b = booking.to_dict() if hasattr(booking, 'to_dict') else booking
    cancel_token = b.get('cancel_token', '')
    cancel_url   = f"{CLINIC_WEBSITE}/cancel/{cancel_token}" if cancel_token else f"{CLINIC_WEBSITE}/status"
    msg = (
        f"Hi {b['first_name']}! Your appointment at Alday Dental Clinic "
        f"({b.get('branch','')}) is CONFIRMED for "
        f"{b.get('date','')} at {b.get('time','')}. "
        f"Service: {b.get('service','')}. "
        f"Need to cancel? Visit: {cancel_url}"
    )
    send_sms(b['phone'], msg)


def sms_booking_cancelled(booking):
    b = booking.to_dict() if hasattr(booking, 'to_dict') else booking
    msg = (
        f"Hi {b['first_name']}, your appointment at Alday Dental Clinic "
        f"on {b.get('date','')} at {b.get('time','')} has been "
        f"CANCELLED. To rebook, visit: {CLINIC_WEBSITE}/book or call us at 0916-787-0278."
    )
    send_sms(b['phone'], msg)


def sms_booking_done(booking):
    b = booking.to_dict() if hasattr(booking, 'to_dict') else booking
    msg = (
        f"Hi {b['first_name']}! Thank you for visiting Alday Dental Clinic. "
        f"We hope your visit went well. Book your next appointment at: {CLINIC_WEBSITE}/book"
    )
    send_sms(b['phone'], msg)


# ── Admin Security ─────────────────────────────────────────────────────────

def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma']        = 'no-cache'
    response.headers['Expires']       = '0'
    return response


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            session.clear()
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated


# ── DB init + optional JSON migration ─────────────────────────────────────

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
BOOKINGS_FILE = os.path.join(BASE_DIR, 'bookings.json')
MESSAGES_FILE = os.path.join(BASE_DIR, 'messages.json')
PAYMENTS_FILE = os.path.join(BASE_DIR, 'payments.json')
FEEDBACK_FILE = os.path.join(BASE_DIR, 'feedback.json')


def load_json(filepath):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return []


def migrate_json_to_db():
    if Booking.query.count() == 0:
        raw_bookings = load_json(BOOKINGS_FILE)
        if raw_bookings:
            existing_pids = set()
            for b in raw_bookings:
                pid = b.get('patient_id') or generate_patient_id()
                while pid in existing_pids:
                    pid = generate_patient_id()
                existing_pids.add(pid)
                row = Booking(
                    patient_id   = pid,
                    cancel_token = b.get('cancel_token') or str(uuid.uuid4()),
                    first_name   = b.get('first_name', ''),
                    last_name    = b.get('last_name', ''),
                    phone        = b.get('phone', ''),
                    email        = b.get('email', ''),
                    branch       = b.get('branch', ''),
                    service      = b.get('service') or b.get('services', ''),
                    date         = b.get('date', ''),
                    time         = b.get('time', ''),
                    notes        = b.get('notes', ''),
                    status       = b.get('status', 'pending'),
                )
                db.session.add(row)
            db.session.commit()
            print(f'[MIGRATE] Imported {len(raw_bookings)} bookings from JSON.')
            os.rename(BOOKINGS_FILE, BOOKINGS_FILE + '.migrated')

    if Message.query.count() == 0:
        raw_messages = load_json(MESSAGES_FILE)
        if raw_messages:
            for m in raw_messages:
                row = Message(
                    first_name  = m.get('first_name', ''),
                    last_name   = m.get('last_name', ''),
                    email       = m.get('email', ''),
                    phone       = m.get('phone', ''),
                    subject     = m.get('subject', ''),
                    message     = m.get('message', ''),
                    status      = m.get('status', 'new'),
                    admin_note  = m.get('admin_note', ''),
                    received_at = m.get('received_at', ''),
                )
                db.session.add(row)
            db.session.commit()
            print(f'[MIGRATE] Imported {len(raw_messages)} messages from JSON.')
            os.rename(MESSAGES_FILE, MESSAGES_FILE + '.migrated')

    if Payment.query.count() == 0:
        raw_payments = load_json(PAYMENTS_FILE)
        if raw_payments:
            for p in raw_payments:
                row = Payment(
                    patient_name   = p.get('patient_name', ''),
                    service        = p.get('service', ''),
                    amount         = float(p.get('amount', 0) or 0),
                    total_amount   = float(p.get('total_amount', 0) or 0),
                    balance        = float(p.get('balance', 0) or 0),
                    method         = p.get('method', 'Cash'),
                    date           = p.get('date', ''),
                    reference      = p.get('reference', ''),
                    notes          = p.get('notes', ''),
                    payment_status = p.get('payment_status', 'paid'),
                )
                db.session.add(row)
            db.session.commit()
            print(f'[MIGRATE] Imported {len(raw_payments)} payments from JSON.')
            os.rename(PAYMENTS_FILE, PAYMENTS_FILE + '.migrated')

    if Feedback.query.count() == 0:
        raw_feedback = load_json(FEEDBACK_FILE)
        if raw_feedback:
            for f in raw_feedback:
                row = Feedback(
                    cancel_token       = f.get('cancel_token', ''),
                    patient_name       = f.get('patient_name', ''),
                    phone              = f.get('phone', ''),
                    branch             = f.get('branch', ''),
                    service            = f.get('service', ''),
                    appointment_date   = f.get('appointment_date', ''),
                    appointment_time   = f.get('appointment_time', ''),
                    overall_rating     = f.get('overall_rating'),
                    staff_rating       = f.get('staff_rating'),
                    cleanliness_rating = f.get('cleanliness_rating'),
                    waiting_rating     = f.get('waiting_rating'),
                    treatment_rating   = f.get('treatment_rating'),
                    recommend          = f.get('recommend', ''),
                    comment            = f.get('comment', ''),
                    submitted_at       = f.get('submitted_at', ''),
                )
                db.session.add(row)
            db.session.commit()
            print(f'[MIGRATE] Imported {len(raw_feedback)} feedback records from JSON.')
            os.rename(FEEDBACK_FILE, FEEDBACK_FILE + '.migrated')


def auto_migrate_columns():
    migrations = [
        ("bookings", "notes",   "ALTER TABLE bookings ADD COLUMN notes TEXT"),
        ("messages", "subject", "ALTER TABLE messages ADD COLUMN subject VARCHAR(255)"),
    ]
    with db.engine.connect() as conn:
        for table, column, sql in migrations:
            try:
                conn.execute(db.text(f"SELECT `{column}` FROM `{table}` LIMIT 1"))
            except Exception:
                try:
                    conn.execute(db.text(sql))
                    conn.commit()
                    print(f'[MIGRATE] Added column `{column}` to `{table}`.')
                except Exception as e:
                    print(f'[MIGRATE] Could not add `{column}` to `{table}`: {e}')


SETTING_DEFAULTS = {
    'clinic_name':        'Alday Dental Clinic',
    'clinic_tagline':     'Your Smile, Our Priority',
    'clinic_phone':       '0916-787-0278',
    'clinic_email':       'info@aldaydental.com',
    'clinic_branches':    'Nasugbu, Batangas\nTagaytay, Cavite',
    'clinic_description': 'Providing quality dental care with a gentle touch since 2010. We offer comprehensive dental services for the whole family.',
    'clinic_maps':        '',
    'admin_display_name': 'Admin',
    'admin_email':        'admin@aldaydental.com',
    'admin_role':         'Clinic Administrator',
    'admin_timezone':     'Asia/Manila (UTC+8)',
    'schedule_open_days':      'Mon,Tue,Wed,Thu,Fri,Sat',
    'schedule_open_time':      '09:00',
    'schedule_close_time':     '17:00',
    'schedule_slot_states':    '9:00 AM,10:00 AM,11:00 AM,1:00 PM,2:00 PM,3:00 PM,4:00 PM,5:00 PM',
    'schedule_appt_duration':  '60 mins',
    'schedule_holidays':       '',
    'booking_online_enabled':  'true',
    'booking_auto_confirm':    'false',
    'booking_require_phone':   'true',
    'booking_multi_service':   'true',
    'booking_advance_days':    '30 days',
    'booking_cutoff_time':     '15:00',
    'booking_max_slots':       '10',
    'booking_confirm_message': 'Thank you for booking with Alday Dental Clinic! We will confirm your appointment shortly. Please call us if you need to reschedule.',
    'notif_new_booking':    'true',
    'notif_new_message':    'true',
    'notif_patient_confirm':'true',
    'notif_sms_reminder':   'false',
    'notif_daily_summary':  'false',
    'notif_admin_email':    'admin@aldaydental.com',
    'notif_reminder_tpl':   'Hi {name}, this is a reminder for your appointment at Alday Dental Clinic on {date} at {time} for {service}. See you soon!',
    'pay_accept_cash':      'true',
    'pay_accept_gcash':     'true',
    'pay_accept_card':      'true',
    'pay_gcash_number':     '0916-787-0278',
    'pay_currency':         '₱ (PHP)',
    'pay_require_ref':      'false',
    'pay_allow_partial':    'true',
    'pay_receipt_footer':   'Thank you for trusting Alday Dental Clinic! 📞 0916-787-0278 · Keep this receipt for your records.',
    'appear_accent_color':  '#c9a84c',
    'appear_theme':         'Light (Default)',
    'appear_sidebar_style': 'Full (Icons + Text)',
    'appear_table_density': 'Comfortable',
    'appear_animations':    'true',
    'appear_date_format':   'YYYY-MM-DD',
    'security_session_timeout': '1 hour',
    'security_login_limit':     '5 attempts',
    'security_login_log':       'true',
}


def seed_default_settings():
    changed = False
    for key, default_val in SETTING_DEFAULTS.items():
        if not Setting.query.filter_by(key=key).first():
            db.session.add(Setting(key=key, value=default_val))
            changed = True
    if changed:
        db.session.commit()
        print('[SETTINGS] Default settings seeded.')


with app.app_context():
    db.create_all()
    auto_migrate_columns()
    migrate_json_to_db()
    seed_default_settings()


# ── Public Routes ──────────────────────────────────────────────────────────

@app.route('/')
def home():
    feedback_list = [f.to_dict() for f in Feedback.query.all()]
    featured = [f for f in feedback_list if f.get('overall_rating', 0) >= 4]
    return render_template('index.html', featured_reviews=featured)


@app.route('/branches')
def branches():
    return render_template('branches.html')


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if data:
                row = Message(
                    first_name  = data.get('first_name', ''),
                    last_name   = data.get('last_name', ''),
                    email       = data.get('email', ''),
                    phone       = data.get('phone', ''),
                    subject     = data.get('subject', ''),
                    message     = data.get('message', ''),
                    status      = 'new',
                    received_at = datetime.now().strftime('%Y-%m-%d'),
                )
                db.session.add(row)
                db.session.commit()
            return jsonify({'status': 'success'})
        except Exception as e:
            db.session.rollback()
            print(f'Contact error: {e}')
            return jsonify({'status': 'error'}), 500
    return render_template('contact.html')


@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if data:
                phone = data.get('phone', '').strip()
                date  = data.get('date', '').strip()
                time  = data.get('time', '').strip()

                existing = Booking.query.filter(
                    Booking.phone  == phone,
                    Booking.date   == date,
                    Booking.time   == time,
                    Booking.status != 'cancelled',
                ).first()

                if existing:
                    print(f'[BOOK] Duplicate prevented for {phone} on {date} at {time}')
                    return jsonify({
                        'status':     'success',
                        'message':    'Booking already exists!',
                        'patient_id': existing.patient_id,
                    })

                pid = generate_patient_id()
                row = Booking(
                    patient_id   = pid,
                    cancel_token = str(uuid.uuid4()),
                    first_name   = data.get('first_name', ''),
                    last_name    = data.get('last_name', ''),
                    phone        = phone,
                    email        = data.get('email', ''),
                    branch       = data.get('branch', ''),
                    service      = data.get('service') or data.get('services', ''),
                    date         = date,
                    time         = time,
                    notes        = data.get('notes', ''),
                    status       = 'pending',
                )
                db.session.add(row)
                db.session.commit()
                sms_booking_received(row)

            return jsonify({
                'status':     'success',
                'message':    'Booking received!',
                'patient_id': row.patient_id,
            })
        except Exception as e:
            db.session.rollback()
            print(f'Booking error: {e}')
            return jsonify({'status': 'error'}), 500
    return render_template('book.html')


@app.route('/status')
def status():
    return render_template('status.html')


# ── Cancel Routes ──────────────────────────────────────────────────────────

@app.route('/cancel/<token>')
def cancel_via_link(token):
    booking = Booking.query.filter_by(cancel_token=token).first()
    if not booking:
        return render_template('cancel_result.html',
                               success=False,
                               message="We couldn't find that appointment. It may have already been cancelled.")
    if booking.status in ('cancelled', 'done'):
        return render_template('cancel_result.html',
                               success=False,
                               message=f"This appointment is already marked as '{booking.status}'.")
    return render_template('cancel_confirm.html', booking=booking.to_dict(), token=token)


@app.route('/cancel/<token>/confirm', methods=['POST'])
def cancel_confirm(token):
    booking = Booking.query.filter_by(cancel_token=token).first()
    if not booking:
        return render_template('cancel_result.html', success=False, message="Appointment not found.")
    if booking.status in ('cancelled', 'done'):
        return render_template('cancel_result.html',
                               success=False,
                               message=f"This appointment is already '{booking.status}'.")
    booking.status = 'cancelled'
    db.session.commit()
    sms_booking_cancelled(booking)
    return render_template('cancel_result.html',
                           success=True,
                           message=f"Your appointment on {booking.date} at {booking.time} has been cancelled.")


@app.route('/api/cancel-appointment', methods=['POST'])
def api_cancel_appointment():
    try:
        data  = request.get_json()
        name  = f"{data.get('first_name','')} {data.get('last_name','')}".strip().lower()
        phone = data.get('phone', '').strip()
        token = data.get('cancel_token', '')

        booking = Booking.query.filter_by(cancel_token=token).first()
        if not booking:
            return jsonify({'status': 'error', 'message': 'Appointment not found or details do not match.'}), 404

        full_name = f"{booking.first_name} {booking.last_name}".strip().lower()
        if full_name != name or booking.phone.strip() != phone:
            return jsonify({'status': 'error', 'message': 'Appointment not found or details do not match.'}), 404

        if booking.status in ('cancelled', 'done'):
            return jsonify({'status': 'error', 'message': f"Appointment is already '{booking.status}'."}), 400

        booking.status = 'cancelled'
        db.session.commit()
        sms_booking_cancelled(booking)
        return jsonify({'status': 'success', 'message': 'Appointment cancelled successfully.'})
    except Exception as e:
        db.session.rollback()
        print(f'Cancel error: {e}')
        return jsonify({'status': 'error', 'message': 'An error occurred.'}), 500


# ── Feedback Route ─────────────────────────────────────────────────────────

@app.route('/api/submit-feedback', methods=['POST'])
def submit_feedback():
    try:
        data           = request.get_json()
        token          = data.get('cancel_token', '').strip()
        overall_rating = data.get('overall_rating')
        category       = data.get('category_ratings', {})
        recommend      = data.get('recommend')
        comment        = data.get('comment', '').strip()

        if not token:
            return jsonify({'status': 'error', 'message': 'Missing appointment reference.'}), 400
        if not overall_rating or not (1 <= int(overall_rating) <= 5):
            return jsonify({'status': 'error', 'message': 'Please provide a valid rating (1–5).'}), 400

        booking = Booking.query.filter_by(cancel_token=token).first()
        if not booking:
            return jsonify({'status': 'error', 'message': 'Appointment not found.'}), 404
        if booking.status != 'done':
            return jsonify({'status': 'error', 'message': 'Feedback can only be submitted for completed appointments.'}), 403

        if Feedback.query.filter_by(cancel_token=token).first():
            return jsonify({'status': 'error', 'message': 'Feedback has already been submitted for this appointment.'}), 409

        row = Feedback(
            cancel_token       = token,
            patient_name       = f"{booking.first_name} {booking.last_name}".strip(),
            phone              = booking.phone,
            branch             = booking.branch,
            service            = booking.service,
            appointment_date   = booking.date,
            appointment_time   = booking.time,
            overall_rating     = int(overall_rating),
            staff_rating       = int(category.get('staff', 0)) or None,
            cleanliness_rating = int(category.get('cleanliness', 0)) or None,
            waiting_rating     = int(category.get('waiting', 0)) or None,
            treatment_rating   = int(category.get('treatment', 0)) or None,
            recommend          = recommend,
            comment            = comment,
            submitted_at       = datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        )
        db.session.add(row)
        db.session.commit()
        print(f'[FEEDBACK] Saved for {row.patient_name} — {overall_rating}★')
        return jsonify({'status': 'success'})

    except Exception as e:
        db.session.rollback()
        print(f'Feedback error: {e}')
        return jsonify({'status': 'error', 'message': 'An error occurred. Please try again.'}), 500


# ── Admin Routes ───────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session['admin_logged_in'] = True
            return redirect('/admin')
        error = 'Invalid username or password. Please try again.'
    else:
        # Only clear the session when the admin visits the login page directly
        session.clear()
    resp = make_response(render_template('admin_login.html', error=error))
    return no_cache(resp)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')


@app.route('/admin')
@admin_required
def admin_dashboard():
    bookings      = [b.to_dict() for b in Booking.query.order_by(Booking.id.desc()).all()]
    messages      = [m.to_dict() for m in Message.query.order_by(Message.id.desc()).all()]
    payments      = [p.to_dict() for p in Payment.query.order_by(Payment.id.desc()).all()]
    feedback_list = [f.to_dict() for f in Feedback.query.order_by(Feedback.id.desc()).all()]

    total_revenue = sum(
        float(p.get('amount', 0)) for p in payments if p.get('payment_status') == 'paid'
    )
    total_balance = sum(float(p.get('balance', 0)) for p in payments)
    settings      = Setting.all_as_dict()

    resp = make_response(render_template(
        'admin_dashboard.html',
        bookings=bookings,
        messages=messages,
        payments=payments,
        feedback_list=feedback_list,
        services=SERVICES,
        total_revenue=total_revenue,
        total_balance=total_balance,
        settings=settings,
    ))
    return no_cache(resp)


# ── Admin POST Routes ──────────────────────────────────────────────────────

@app.route('/admin/update-booking/<int:index>', methods=['POST'])
@admin_required
def update_booking(index):
    booking = Booking.query.get(index)
    if booking:
        old_status = booking.status
        new_status = request.form.get('status', 'pending')
        booking.status = new_status
        db.session.commit()
        if new_status != old_status:
            if new_status == 'confirmed':
                sms_booking_confirmed(booking)
            elif new_status == 'cancelled':
                sms_booking_cancelled(booking)
            elif new_status == 'done':
                sms_booking_done(booking)
        print(f'Updated booking id={index} to status={new_status}')
    else:
        print(f'Booking id={index} not found.')
    return redirect('/admin')


@app.route('/admin/update-message/<int:index>', methods=['POST'])
@admin_required
def update_message(index):
    msg = Message.query.get(index)
    if msg:
        msg.status = request.form.get('status', 'new')
        db.session.commit()
    return redirect('/admin')


@app.route('/admin/delete-message/<int:index>', methods=['POST'])
@admin_required
def delete_message(index):
    try:
        msg = Message.query.get(index)
        if msg:
            db.session.delete(msg)
            db.session.commit()
            print(f'[MESSAGE] Deleted message from {msg.first_name} {msg.last_name}')
        else:
            print(f'[MESSAGE] Message id={index} not found.')
    except Exception as e:
        db.session.rollback()
        print(f'[MESSAGE] Delete error: {e}')
    return redirect('/admin')


@app.route('/admin/note-message/<int:index>', methods=['POST'])
@admin_required
def note_message(index):
    try:
        msg = Message.query.get(index)
        if msg:
            msg.admin_note = request.form.get('admin_note', '').strip()
            db.session.commit()
            print(f'[MESSAGE] Note saved for id={index}')
    except Exception as e:
        db.session.rollback()
        print(f'[MESSAGE] Note error: {e}')
    return redirect('/admin')


@app.route('/admin/add-payment', methods=['POST'])
@admin_required
def add_payment():
    try:
        amount_paid  = float(request.form.get('amount', '0') or 0)
        total_amount = float(request.form.get('total_amount', '0') or 0)
        balance      = max(0, total_amount - amount_paid)
        row = Payment(
            patient_name   = request.form.get('patient_name', ''),
            service        = request.form.get('service', ''),
            amount         = amount_paid,
            total_amount   = total_amount,
            balance        = balance,
            method         = request.form.get('method', 'Cash'),
            date           = request.form.get('date', ''),
            reference      = request.form.get('reference', ''),
            notes          = request.form.get('notes', ''),
            payment_status = request.form.get('payment_status', 'paid'),
        )
        db.session.add(row)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'Payment error: {e}')
    return redirect('/admin')


@app.route('/admin/update-payment/<int:index>', methods=['POST'])
@admin_required
def update_payment(index):
    try:
        payment = Payment.query.get(index)
        if payment:
            total_amount = float(request.form.get('total_amount', '0') or 0)
            amount_paid  = float(request.form.get('amount', '0') or 0)
            balance      = max(0, total_amount - amount_paid)
            payment.patient_name   = request.form.get('patient_name', '').strip()
            payment.service        = request.form.get('service', '').strip()
            payment.total_amount   = total_amount
            payment.amount         = amount_paid
            payment.balance        = balance
            payment.method         = request.form.get('method', 'Cash').strip()
            payment.date           = request.form.get('date', '').strip()
            payment.reference      = request.form.get('reference', '').strip()
            payment.notes          = request.form.get('notes', '').strip()
            payment.payment_status = request.form.get('payment_status', 'paid').strip()
            db.session.commit()
            print(f'[PAYMENT] Updated id={index} ({payment.patient_name})')
        else:
            print(f'[PAYMENT] Payment id={index} not found.')
    except Exception as e:
        db.session.rollback()
        print(f'[PAYMENT] Update error: {e}')
    return redirect('/admin')


@app.route('/admin/save-settings', methods=['POST'])
@admin_required
def save_settings():
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({'status': 'error', 'message': 'Invalid payload.'}), 400
        for key, value in data.items():
            if key in SETTING_DEFAULTS:
                Setting.set(key, str(value))
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        print(f'[SETTINGS] Save error: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/admin/delete-payment/<int:index>', methods=['POST'])
@admin_required
def delete_payment(index):
    try:
        payment = Payment.query.get(index)
        if payment:
            db.session.delete(payment)
            db.session.commit()
            print(f'[PAYMENT] Deleted id={index}')
        else:
            print(f'[PAYMENT] Delete: id={index} not found.')
    except Exception as e:
        db.session.rollback()
        print(f'[PAYMENT] Delete error: {e}')
    return redirect('/admin')


# ── API Routes ─────────────────────────────────────────────────────────────

@app.route('/api/booked-slots')
def booked_slots():
    branch    = request.args.get('branch', '')
    ALL_TIMES = ['9:00 AM', '10:00 AM', '11:00 AM', '1:00 PM',
                 '2:00 PM', '3:00 PM',  '4:00 PM',  '5:00 PM']

    query = Booking.query.filter(Booking.status.in_(['confirmed', 'done']))
    if branch:
        query = query.filter_by(branch=branch)

    slots = {}
    for b in query.all():
        if b.date:
            slots.setdefault(b.date, set()).add(b.time)

    booked_times = {d: list(v) for d, v in slots.items()}
    fully_booked = [d for d, times in slots.items()
                    if all(t in times for t in ALL_TIMES)]

    return jsonify({'booked_times': booked_times, 'fully_booked': fully_booked})


@app.route('/api/check-status')
def check_status():
    name       = request.args.get('name', '').strip().lower()
    phone      = request.args.get('phone', '').strip()
    patient_id = request.args.get('patient_id', '').strip().upper()

    query = Booking.query.filter(
        db.func.lower(db.func.concat(Booking.first_name, ' ', Booking.last_name)) == name,
        Booking.phone == phone,
    )
    if patient_id:
        query = query.filter(db.func.upper(Booking.patient_id) == patient_id)

    matches = [b.to_dict() for b in query.all()]
    return jsonify({'appointments': matches})


# ── Debug ──────────────────────────────────────────────────────────────────

@app.route('/debug/bookings')
def debug_bookings():
    return jsonify([b.to_dict() for b in Booking.query.all()])


# ──────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)
