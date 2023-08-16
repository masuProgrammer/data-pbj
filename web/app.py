from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash  # Import the function
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import requests
from datetime import datetime,timedelta
from pytz import timezone
from openpyxl import Workbook

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
    role = db.Column(db.String(20), nullable=False, default='user')
    daerah_id = db.Column(db.Integer, db.ForeignKey('daerah.id'))  # Add the foreign key

    daerah = db.relationship('Daerah', backref='users')  # Establish the relationship

class Daerah(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

class Api(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    url = db.Column(db.String(200), nullable=False)
    daerah_id = db.Column(db.Integer, db.ForeignKey('daerah.id'))  # Add the foreign key
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    daerah = db.relationship('Daerah', backref='apis')  # Establish the relationship



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

@app.route('/tarik', methods=['GET'])
def tarik():
    tarik_data()
    return 'fungsi tarik data tereksekusi'

# Define the login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()

        if user is not None and check_password_hash(user.password, password):
            print("berhasil")
            session['user_id'] = user.id
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        else:
            print("gagal")
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

# Define the dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])

        if user.role != 'admin':
            api_list = user.daerah.apis
            
            # Convert updated_at to Asia/Jakarta timezone
            for api in api_list:
                api.updated_at = api.updated_at.astimezone(timezone('Asia/Jakarta'))

            return render_template('dashboard.html', user=user, api_list=api_list, timedelta=timedelta)
        
        return render_template('dashboard.html', user=user)
    else:
        return redirect(url_for('login'))

@app.route('/manage-api')
def manage_api():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'admin':
            api_objects = Api.query.all()
            api_list = [{'id': api.id, 'name': api.name, 'url': api.url, 'daerah_id': api.daerah_id} for api in api_objects]
            daerah_objects = Daerah.query.all()  # Get all daerah as objects
            daerah_list = [{'id': daerah.id, 'name': daerah.name} for daerah in daerah_objects]  # Serialize daerah objects
            def get_daerah_name(daerah_id):
                daerah = next((item for item in daerah_list if item["id"] == daerah_id), None)
                return daerah["name"] if daerah else 'Unknown Daerah'
            return render_template('manage_api.html', user=user, api_list=api_list, daerah_list=daerah_list,get_daerah_name=get_daerah_name)
        else:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))   
    
# Define a route to delete an account
@app.route('/delete-api/<int:id>')
def delete_api(id):
    api = Api.query.get(id)
    db.session.delete(api)
    db.session.commit()
    flash('API deleted successfully.', 'success')
    return redirect(url_for('manage_api'))
    
@app.route('/create-api', methods=['POST'])
def create_api():
    if request.method == 'POST':
        new_api_name = request.form.get('name')
        new_api_url = request.form.get('url')
        new_daerah_id = request.form.get('daerah_id')  # Get the selected daerah_id

        print(new_daerah_id)
        # Perform necessary actions to create a new API
        new_api = Api(name=new_api_name, url=new_api_url, daerah_id=new_daerah_id)
        db.session.add(new_api)
        db.session.commit()

        flash('API created successfully.', 'success')
        return redirect(url_for('manage_api'))
    

@app.route('/edit-api/<int:id>', methods=['GET', 'POST'])
def edit_api(id):
    api = Api.query.get(id)
    if request.method == 'POST':
        api.name = request.form.get('name')
        api.url = request.form.get('url')
        api.daerah_id = request.form.get('daerah_id')  # Update the associated Daerah
        
        db.session.commit()
        flash('API edited successfully.', 'success')
        return redirect(url_for('manage_api'))
    return render_template('edit_api.html', api=api, daerah_list=Daerah.query.all())  # Pass daerah_list to the template


# Define a route for account management (only accessible to admin users)
@app.route('/manage-accounts')
def manage_accounts():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'admin':
            users = User.query.all()  # Get all users
            users_json = [{'id': user.id, 'username': user.username, 'role': user.role, 'daerah_id': user.daerah_id} for user in users]
            daerah_objects = Daerah.query.all()  # Get all daerah as objects
            daerah_list = [{'id': daerah.id, 'name': daerah.name} for daerah in daerah_objects]  # Serialize daerah objects
            def get_daerah_name(daerah_id):
                daerah = next((item for item in daerah_list if item["id"] == daerah_id), None)
                return daerah["name"] if daerah else 'Unknown Daerah'
            return render_template('manage_accounts.html', user=user, users=users_json,daerah_list=daerah_list,get_daerah_name=get_daerah_name)  # Pass the user and users to the template
        else:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/create-account', methods=['POST'])
def create_account():
    if request.method == 'POST':
        data = request.json  # Get JSON data from the request
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')
        daerah_id = data.get('daerah_id')  # Get daerah_id from the JSON data

        hashed_password = generate_password_hash(password)  # Hash the password

        new_user = User(username=username, password=hashed_password, role=role, daerah_id=daerah_id)  # Include daerah_id
        db.session.add(new_user)
        db.session.commit()

        response_data = {'message': 'User account created successfully.'}
        return jsonify(response_data)

# Define a route to edit an account
@app.route('/edit-account/<int:id>', methods=['GET', 'POST'])
def edit_account(id):
    user = User.query.get(id)
    if request.method == 'POST':
        # Update user data here based on the form data
        # Include updating daerah_id if needed
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

@app.route('/manage-daerah')
def manage_daerah():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'admin':
            daerah_objects = Daerah.query.all()  # Get all daerah as objects
            daerah_list = [{'id': daerah.id, 'name': daerah.name} for daerah in daerah_objects]  # Serialize daerah objects
            return render_template('manage_daerah.html', user=user, daerah_list=daerah_list)
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

@app.route('/create_daerah', methods=['POST'])
def create_daerah():
    if request.method == 'POST':
        new_daerah_name = request.form.get('name')

        # Perform necessary actions to create a new daerah
        # For example, adding to a database or updating the data list
        new_daerah = Daerah(name=new_daerah_name)
        db.session.add(new_daerah)

        return redirect(url_for('index'))
    
@app.route('/download/<string:daerah>/<string:api_name>/<string:format>')
def download_api(daerah, api_name,format):
    folder_path = os.path.join('download', daerah, api_name)
    file_path_json = os.path.join(folder_path, 'data.json')
    file_path_excel = os.path.join(folder_path, 'data.xlsx')

    # Check if the JSON file exists
    if format == 'json':
        return send_file(file_path_json, as_attachment=True)
    
    # Check if the Excel file exists
    elif format == 'excel':
        return send_file(file_path_excel, as_attachment=True)
    
    else:
        return "File not found"
    
# Definisi rute logout
@app.route('/logout')
def logout():
    session.clear()  # Menghapus data sesi
    return redirect(url_for('login'))  # Mengarahkan kembali ke halaman login
    

# Inisialisasi scheduler
scheduler = BackgroundScheduler()
def tarik_data():
    # Query API dengan updated_at terlama
    api = Api.query.order_by(Api.updated_at).first()

    if api is not None:
        daerah_name = Daerah.query.get(api.daerah_id).name
        api_name = api.name
        api_url = api.url
        
        # Lakukan permintaan HTTP untuk mengambil data dari URL API
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            
            # Buat struktur folder jika belum ada
            folder_path = os.path.join('download', daerah_name, api_name)
            os.makedirs(folder_path, exist_ok=True)
            
            # Simpan data ke dalam file JSON
            file_path = os.path.join(folder_path, 'data.json')
            with open(file_path, 'w') as file:
                json.dump(data, file)
            
            # Update updated_at
            api.updated_at = datetime.utcnow()
            db.session.commit()
            
            print(f"Data from {api_name} in {daerah_name} saved to {file_path}")
            
            # Buat file Excel
            excel_file_path = os.path.join(folder_path, 'data.xlsx')
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = 'Data'
            
            # Tulis data ke file Excel
            for row_index, item in enumerate(data, start=1):
                col_index = 1
                for value in item.values():
                    sheet.cell(row=row_index, column=col_index, value=value)
                    col_index += 1
            
            workbook.save(excel_file_path)
            print(f"Data from {api_name} in {daerah_name} saved to {excel_file_path}")
            
        else:
            print(f"Failed to fetch data from {api_name} in {daerah_name}")
    else:
        print("No APIs found")

scheduler.add_job(tarik_data, 'interval', minutes=1)

# Jalankan scheduler
scheduler.start()

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)