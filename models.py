from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Booking(db.Model):
    __tablename__ = 'bookings'

    id           = db.Column(db.Integer, primary_key=True)
    patient_id   = db.Column(db.String(20), unique=True)
    cancel_token = db.Column(db.String(100), unique=True)
    first_name   = db.Column(db.String(100))
    last_name    = db.Column(db.String(100))
    phone        = db.Column(db.String(20))
    email        = db.Column(db.String(100))
    branch       = db.Column(db.String(100))
    service      = db.Column(db.String(100))
    date         = db.Column(db.String(20))
    time         = db.Column(db.String(20))
    notes        = db.Column(db.Text)           # added — used in /book route
    status       = db.Column(db.String(20), default='pending')
    created_at   = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id':           self.id,
            'patient_id':   self.patient_id   or '',
            'cancel_token': self.cancel_token or '',
            'first_name':   self.first_name   or '',
            'last_name':    self.last_name    or '',
            'phone':        self.phone        or '',
            'email':        self.email        or '',
            'branch':       self.branch       or '',
            'service':      self.service      or '',
            'date':         self.date         or '',
            'time':         self.time         or '',
            'notes':        self.notes        or '',
            'status':       self.status       or 'pending',
        }


class Message(db.Model):
    __tablename__ = 'messages'

    id          = db.Column(db.Integer, primary_key=True)
    first_name  = db.Column(db.String(100))
    last_name   = db.Column(db.String(100))
    phone       = db.Column(db.String(20))
    email       = db.Column(db.String(100))
    subject     = db.Column(db.String(255))     # added — used in /contact route
    message     = db.Column(db.Text)
    status      = db.Column(db.String(20), default='new')
    admin_note  = db.Column(db.Text)
    received_at = db.Column(db.String(20))

    def to_dict(self):
        return {
            'id':          self.id,
            'first_name':  self.first_name  or '',
            'last_name':   self.last_name   or '',
            'phone':       self.phone       or '',
            'email':       self.email       or '',
            'subject':     self.subject     or '',
            'message':     self.message     or '',
            'status':      self.status      or 'new',
            'admin_note':  self.admin_note  or '',
            'received_at': self.received_at or '',
        }


class Payment(db.Model):
    __tablename__ = 'payments'

    id             = db.Column(db.Integer, primary_key=True)
    patient_name   = db.Column(db.String(200))
    service        = db.Column(db.String(100))
    amount         = db.Column(db.Float, default=0)
    total_amount   = db.Column(db.Float, default=0)
    balance        = db.Column(db.Float, default=0)
    method         = db.Column(db.String(50), default='Cash')
    date           = db.Column(db.String(20))
    reference      = db.Column(db.String(100))
    notes          = db.Column(db.Text)
    payment_status = db.Column(db.String(20), default='paid')

    def to_dict(self):
        return {
            'id':             self.id,
            'patient_name':   self.patient_name   or '',
            'service':        self.service         or '',
            'amount':         str(self.amount      or 0),
            'total_amount':   str(self.total_amount or 0),
            'balance':        str(self.balance      or 0),
            'method':         self.method          or 'Cash',
            'date':           self.date            or '',
            'reference':      self.reference       or '',
            'notes':          self.notes           or '',
            'payment_status': self.payment_status  or 'paid',
        }


class Setting(db.Model):
    __tablename__ = 'settings'

    id         = db.Column(db.Integer, primary_key=True)
    key        = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value      = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    @staticmethod
    def get(key, default=''):
        row = Setting.query.filter_by(key=key).first()
        return row.value if row and row.value is not None else default

    @staticmethod
    def set(key, value):
        row = Setting.query.filter_by(key=key).first()
        if row:
            row.value = value
            row.updated_at = datetime.now()
        else:
            row = Setting(key=key, value=value)
            db.session.add(row)
        # caller must commit

    @staticmethod
    def all_as_dict():
        return {r.key: r.value for r in Setting.query.all()}


class Feedback(db.Model):
    __tablename__ = 'feedback'

    id                  = db.Column(db.Integer, primary_key=True)
    cancel_token        = db.Column(db.String(100))
    patient_name        = db.Column(db.String(200))
    phone               = db.Column(db.String(20))
    branch              = db.Column(db.String(100))
    service             = db.Column(db.String(100))
    appointment_date    = db.Column(db.String(20))
    appointment_time    = db.Column(db.String(20))
    overall_rating      = db.Column(db.Integer)
    staff_rating        = db.Column(db.Integer)
    cleanliness_rating  = db.Column(db.Integer)
    waiting_rating      = db.Column(db.Integer)
    treatment_rating    = db.Column(db.Integer)
    recommend           = db.Column(db.String(10))
    comment             = db.Column(db.Text)
    submitted_at        = db.Column(db.String(30))

    def to_dict(self):
        return {
            'id':                 self.id,
            'cancel_token':       self.cancel_token       or '',
            'patient_name':       self.patient_name       or '',
            'phone':              self.phone              or '',
            'branch':             self.branch             or '',
            'service':            self.service            or '',
            'appointment_date':   self.appointment_date   or '',
            'appointment_time':   self.appointment_time   or '',
            'overall_rating':     self.overall_rating     or 0,
            'staff_rating':       self.staff_rating,
            'cleanliness_rating': self.cleanliness_rating,
            'waiting_rating':     self.waiting_rating,
            'treatment_rating':   self.treatment_rating,
            'recommend':          self.recommend          or '',
            'comment':            self.comment            or '',
            'submitted_at':       self.submitted_at       or '',
        }