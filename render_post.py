# Content Calendar Viewer - Version 6.22
# Updated: December 31, 2025
# Changes: Removed accidental CSS paste (syntax error fix)

import pandas as pd
from flask import Flask, render_template, request, redirect, flash
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import secure_filename
import os
from datetime import timedelta, date
from calendar import monthrange

# Optional local .env support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__, template_folder='templates')
app.static_folder = 'downloaded_images'
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-change-me')

# === PASSWORD FROM ENVIRONMENT VARIABLES ===
auth = HTTPBasicAuth()

USERNAME = os.getenv('APP_USERNAME', 'admin')
PASSWORD = os.getenv('APP_PASSWORD', 'change-me')

users = {USERNAME: PASSWORD}

@auth.get_password
def get_pw(username):
    return users.get(username)

# === FILE UPLOAD CONFIG ===
ALLOWED_EXCEL = {'xlsx'}
ALLOWED_IMAGES = {'jpg', 'jpeg'}

def allowed_excel(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXCEL

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGES

# Load data function
def load_data():
    df = pd.read_excel('Content_Calendar.xlsx', sheet_name='Feed List')
    df['Publish Date (DD/MM/YYYY)'] = pd.to_datetime(df['Publish Date (DD/MM/YYYY)'], format='%d/%m/%Y', errors='coerce')
    df = df.dropna(subset=['Publish Date (DD/MM/YYYY)'])
    df = df.fillna('')
    return df

# Initial load
df = load_data()

unique_dates = sorted(df['Publish Date (DD/MM/YYYY)'].dt.date.unique())
unique_month_first_days = sorted(set(date(d.year, d.month, 1) for d in unique_dates))

FH_LOGO = 'https://scontent.ftll3-1.fna.fbcdn.net/v/t39.30808-1/457303426_911180744386777_3888699262340289275_n.jpg?stp=dst-jpg_s200x200_tt6&_nc_cat=102&ccb=1-7&_nc_sid=2d3e12&_nc_ohc=Nd6kmFjAJQEQ7kNvwFJ0lkG&_nc_oc=AdnOJfcQCICar3GKfMiQ8Fbyf6cCvhpDht7GswwCBDJqBNl9p2Ngo3LgTxef1oEIM7kBPMJxOpfeILHZNneZy03z&_nc_zt=24&_nc_ht=scontent.ftll3-1.fna&_nc_gid=-IS6c9rLDrHQIP3ejnsIoA&oh=00_Afk6sAZDlfx82GcdXX2vSpBJWlk9JjorQW5Ql0KMPSbuWA&oe=6959C0AA'

CATEGORY_COLORS = {
    'About FH': '#AEBB43',
    'Programs': '#47BBBC',
    '': '#AEBB43',
}

def get_month_days(year, month):
    _, days = monthrange(year, month)
    first = date(year, month, 1)
    return [first + timedelta(days=i) for i in range(days)]

def get_weekday_headers():
    return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

@app.route('/')
@auth.login_required
def index():
    # Reload data on every request
    df = load_data()

    unique_dates = sorted(df['Publish Date (DD/MM/YYYY)'].dt.date.unique())
    unique_month_first_days = sorted(set(date(d.year, d.month, 1) for d in unique_dates))

    view_mode = request.args.get('mode', 'day')
    date_str = request.args.get('date')

    if date_str:
        selected_date = pd.to_datetime(date_str).date()
    else:
        selected_date = unique_dates[-1] if unique_dates else date.today()

    posts = []
    month_days = []
    calendar_data = {}

    if view_mode == 'day':
        posts = df[df['Publish Date (DD/MM/YYYY)'].dt.date == selected_date].to_dict('records')

    elif view_mode == 'month':
        year, month = selected_date.year, selected_date.month
        month_days = get_month_days(year, month)
        for d in month_days:
            day_posts = df[df['Publish Date (DD/MM/YYYY)'].dt.date == d].to_dict('records')
            calendar_data[d] = day_posts

    elif view_mode == 'all':
        filtered_df = df[df['Publish Date (DD/MM/YYYY)'].dt.date <= selected_date]
        posts = filtered_df.sort_values('Publish Date (DD/MM/YYYY)', ascending=False).to_dict('records')

    # Process posts
    for post in posts:
        item_name = post['Item Name'].strip()
        image_filename = f"{item_name}.jpg"
        image_full_path = os.path.join('downloaded_images', image_filename)
        if os.path.exists(image_full_path):
            post['image'] = image_filename
        else:
            post['image'] = None

        sub_cat = post.get('Sub-Category', 'About FH').strip()
        post['category_color'] = CATEGORY_COLORS.get(sub_cat, '#AEBB43')

    weekday_headers = get_weekday_headers()

    show_nav = view_mode != 'month'
    if show_nav:
        try:
            current_idx = unique_dates.index(selected_date)
            prev_date = unique_dates[current_idx - 1] if current_idx > 0 else None
            next_date = unique_dates[current_idx + 1] if current_idx < len(unique_dates) - 1 else None
        except ValueError:
            prev_date = next_date = None
    else:
        prev_date = next_date = None

    return render_template('index.html',
                           posts=posts,
                           selected_date=selected_date,
                           view_mode=view_mode,
                           show_nav=show_nav,
                           prev_date=prev_date,
                           next_date=next_date,
                           dates=unique_dates,
                           unique_month_first_days=unique_month_first_days,
                           month_days=month_days,
                           calendar_data=calendar_data,
                           weekday_headers=weekday_headers,
                           logo=FH_LOGO,
                           py_version="6.22")

# === UPLOAD ROUTES ===
@app.route('/upload-calendar', methods=['GET', 'POST'])
@auth.login_required
def upload_calendar():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_excel(file.filename):
            file.save('Content_Calendar.xlsx')
            flash('Calendar updated successfully! Refresh to see changes.')
            return redirect('/')
        else:
            flash('Invalid file — .xlsx only')
    return '''
    <h1>Upload New Calendar (.xlsx)</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file accept=".xlsx">
      <input type=submit value=Upload>
    </form>
    <p><a href="/">Back</a></p>
    '''

@app.route('/upload-image', methods=['GET', 'POST'])
@auth.login_required
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_image(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join('downloaded_images', filename))
            flash(f'Image "{filename}" uploaded!')
            return redirect('/')
        else:
            flash('Invalid image — .jpg or .jpeg only')
    return '''
    <h1>Upload Image (.jpg or .jpeg)</h1>
    <p>Name the file exactly like the "Item Name" in Excel (e.g., Org_Spiritual_Jan1.jpg)</p>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file accept=".jpg,.jpeg">
      <input type=submit value=Upload>
    </form>
    <p><a href="/">Back</a></p>
    '''

if __name__ == '__main__':
    app.run(debug=True)