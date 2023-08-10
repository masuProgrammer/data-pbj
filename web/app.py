from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash  # Import the function
import os

# Create a Flask app
app = Flask(__name__)

# Set the secret key
app.config['SECRET_KEY'] = os.urandom(24)

# Set the database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

# Set the tracking modifications flag to False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create the SQLAlchemy database object
db = SQLAlchemy(app)

# Create the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # Add the role column

class Daerah(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)



# Define the index route
@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return f'Welcome, {user.username}!'
    else:
        return redirect(url_for('login'))
    
# Define a route to create the admin user
@app.route('/admin-create', methods=['GET', 'POST'])
def admin_create():
    admin_user = User.query.filter_by(username='admin').first()
    if admin_user is None:
        admin_password = 'admin_password'  # You should set a secure password here
        hashed_password = generate_password_hash(admin_password)  # Import this function
        admin_user = User(username='admin', password=hashed_password, role='admin')
        db.session.add(admin_user)
        db.session.commit()
        return 'Admin user created successfully!'
    return 'Admin user already exists.'

# Define the login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()

        if user is not None and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

# Define the dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('dashboard.html', user=user)  # Pass the user object to the template
    else:
        return redirect(url_for('login'))
    


# Define a route for account management (only accessible to admin users)
@app.route('/manage-accounts')
def manage_accounts():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'admin':
            users = User.query.all()  # Get all users
            users_json = [{'id': user.id, 'role': user.role} for user in users]
            return render_template('manage_accounts.html', user=user, users=users_json)  # Pass the user and users to the template
        else:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


# Define a route to edit an account
@app.route('/edit-account/<int:id>', methods=['GET', 'POST'])
def edit_account(id):
    user = User.query.get(id)
    if request.method == 'POST':
        # Update user data here based on the form data
        # Redirect back to the manage accounts page
        return redirect(url_for('manage_accounts'))
    return render_template('edit_account.html', user=user)

# Define a route to delete an account
@app.route('/delete-account/<int:id>')
def delete_account(id):
    user = User.query.get(id)
    db.session.delete(user)
    db.session.commit()
    flash('Account deleted successfully.', 'success')
    return redirect(url_for('manage_accounts'))

# Define a route for managing daerah (only accessible to admin users)
@app.route('/manage-daerah')
def manage_daerah():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'admin':
            daerah_list = Daerah.query.all()  # Get all daerah
            return render_template('manage_daerah.html', user=user, daerah_list=daerah_list)  # Pass the user and daerah_list to the template
        else:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))
    
    

# Define a route to edit a daerah
@app.route('/edit-daerah/<int:id>', methods=['GET', 'POST'])
def edit_daerah(id):
    daerah = Daerah.query.get(id)
    if request.method == 'POST':
        # Update daerah data here based on the form data
        # Redirect back to the manage daerah page
        return redirect(url_for('manage_daerah'))
    return render_template('edit_daerah.html', daerah=daerah)

# Define a route to delete a daerah
@app.route('/delete-daerah/<int:id>')
def delete_daerah(id):
    daerah = Daerah.query.get(id)
    db.session.delete(daerah)
    db.session.commit()
    flash('Daerah deleted successfully.', 'success')
    return redirect(url_for('manage_daerah'))

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)