import os
import matplotlib
# **IMPORTANT:** Set the backend before importing pyplot or any other Matplotlib modules
matplotlib.use('Agg')  # Use the Anti-Grain Geometry backend for PNGs
import matplotlib.pyplot as plt

from flask import Flask, render_template, request, redirect, jsonify, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange
from datetime import datetime

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Ensure the 'static' directory exists
STATIC_DIR = os.path.join(app.root_path, 'static')
os.makedirs(STATIC_DIR, exist_ok=True)

# Models
class User(db.Model):
    # __tablename__= 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    transactions = db.relationship('Transaction', backref='owner', lazy=True)
    goals = db.relationship('Goal', backref='owner', lazy=True)

class Transaction(db.Model):
    # __tablename__= 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Goal(db.Model):
    # __tablename__= 'goals'
    id = db.Column(db.Integer, primary_key=True)
    goal_name = db.Column(db.String(50), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0.0)
    due_date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class TransactionForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    type = SelectField(
        'Type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()]
    )
    category = StringField('Category', validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=datetime.today)
    note = StringField('Note')
    submit = SubmitField('Add Transaction')

class GoalForm(FlaskForm):
    goal_name = StringField('Goal Name', validators=[DataRequired()])
    target_amount = FloatField('Target Amount', validators=[DataRequired(), NumberRange(min=0)])
    due_date = DateField('Due Date', validators=[DataRequired()], default=datetime.today)
    submit = SubmitField('Set Goal')

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        if existing_user:
            flash('Username or Email already exists. Please choose a different one.', 'danger')
            return render_template('register.html', form=form)
        
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            username=form.username.data, 
            email=form.email.data, 
            password=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id
            flash('You have been logged in!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/dashboard')
def dashboard():
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

    # Fetch the current user and their transactions
    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('login'))
    
    transactions = Transaction.query.filter_by(user_id=user.id).all()

    # Prepare data for the pie chart
    income_data = [transaction.amount for transaction in transactions if transaction.type == 'income']
    expense_data = [transaction.amount for transaction in transactions if transaction.type == 'expense']
    current_balance = sum(income_data) - sum(expense_data)

    # Check and create the `static` folder if it does not exist
    static_folder = os.path.join(os.getcwd(), 'static')
    if not os.path.exists(static_folder):
        os.makedirs(static_folder)

    # Generate and save the pie chart
    chart_path = os.path.join(static_folder, 'chart.png')
    if transactions:  # Only generate the chart if there are transactions
        labels = ['Income', 'Expense']
        sizes = [sum(income_data), sum(expense_data)]
        colors = ['#4caf50', '#f44336']  # Green for income, red for expense
        explode = (0.1, 0)  # Slightly "explode" the income slice

        plt.figure(figsize=(6, 4))
        plt.pie(sizes, labels=labels, colors=colors, explode=explode, autopct='%1.1f%%',
                shadow=True, startangle=140)
        plt.title('Transaction Overview')
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()

    # Render the dashboard template
    return render_template(
        'dashboard.html',
        transactions=transactions,
        income_data=income_data,  # For potential chart customization
        expense_data=expense_data,  # For potential chart customization
        current_balance=current_balance  # For display in the template
    )

@app.route('/add-transaction', methods=['GET', 'POST'])
def add_transaction():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    form = TransactionForm()
    if form.validate_on_submit():
        transaction = Transaction(
            amount=form.amount.data,
            type=form.type.data,
            category=form.category.data,
            date=form.date.data,
            note=form.note.data,
            user_id=session['user_id']
        )
        db.session.add(transaction)
        db.session.commit()
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_transaction.html', form=form)

@app.route('/set-goal', methods=['GET', 'POST'])
def set_goal():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    form = GoalForm()
    if form.validate_on_submit():
        goal = Goal(
            goal_name=form.goal_name.data,
            target_amount=form.target_amount.data,
            due_date=form.due_date.data,
            user_id=session['user_id']
        )
        db.session.add(goal)
        db.session.commit()
        flash('Goal set successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('set_goal.html', form=form)

@app.route('/goals_viewer')
def goals_viewer():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))

    try:
        # Query goals and join with the user table
        results = db.session.query(
            Goal.id.label('goal_id'),
            Goal.goal_name,
            Goal.target_amount,
            Goal.current_amount,
            Goal.due_date,
            User.username.label('owner_name')
        ).join(User, Goal.user_id == User.id).filter(
            User.id == session['user_id']
        ).order_by(Goal.due_date.asc()).all()

        # Transform query results into the desired structure
        goals_data = [
            {
                "goal_id": row.goal_id,
                "goal_name": row.goal_name,
                "target_amount": row.target_amount,
                "current_amount": row.current_amount,
                "due_date": row.due_date.strftime('%Y-%m-%d'),
                "owner_name": row.owner_name
            }
            for row in results
        ]

        return render_template('goals_viewer.html', goals=goals_data)
    
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# Initialize the database before the first request

def create_tables():
    db.create_all()

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
