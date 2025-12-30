# Content Calendar Viewer - Version 5.7
# Updated: December 30, 2025
# Changes: Month view Previous/Next now changes month correctly

import pandas as pd
from flask import Flask, render_template, request
import os
from datetime import timedelta, date
from calendar import monthrange

app = Flask(__name__, template_folder='templates')
app.static_folder = 'downloaded_images'

PY_VERSION = "5.7"

# Load Excel
df = pd.read_excel('Content_Calendar.xlsx', sheet_name='Feed List')

df['Publish Date (DD/MM/YYYY)'] = pd.to_datetime(df['Publish Date (DD/MM/YYYY)'], format='%d/%m/%Y', errors='coerce')
df = df.dropna(subset=['Publish Date (DD/MM/YYYY)'])
df = df.fillna('')

df_all = df.sort_values('Publish Date (DD/MM/YYYY)', ascending=False)

df = df.sort_values('Publish Date (DD/MM/YYYY)')

unique_dates = sorted(df['Publish Date (DD/MM/YYYY)'].dt.date.unique())

unique_month_first_days = sorted(set(date(d.year, d.month, 1) for d in unique_dates))

IMAGE_FOLDER = 'downloaded_images'

FH_LOGO = 'https://scontent.ftll3-1.fna.fbcdn.net/v/t39.30808-1/457303426_911180744386777_3888699262340289275_n.jpg?stp=dst-jpg_s200x200_tt6&_nc_cat=102&ccb=1-7&_nc_sid=2d3e12&_nc_ohc=Nd6kmFjAJQEQ7kNvwFJ0lkG&_nc_oc=AdnOJfcQCICar3GKfMiQ8Fbyf6cCvhpDht7GswwCBDJqBNl9p2Ngo3LgTxef1oEIM7kBPMJxOpfeILHZNneZy03z&_nc_zt=24&_nc_ht=scontent.ftll3-1.fna&_nc_gid=-IS6c9rLDrHQIP3ejnsIoA&oh=00_Afk6sAZDlfx82GcdXX2vSpBJWlk9JjorQW5Ql0KMPSbuWA&oe=6959C0AA'

CATEGORY_COLORS = {
    'About FH': '#AEBB43',
    'Programs': '#47BBBC',
    '': '#AEBB43',
}

def get_week_range(selected_date):
    days_to_sunday = selected_date.weekday()
    days_to_sunday = 6 - days_to_sunday
    start = selected_date - timedelta(days=days_to_sunday)
    end = start + timedelta(days=6)
    return start, end

def get_week_dates(selected_date):
    start, _ = get_week_range(selected_date)
    return [start + timedelta(days=i) for i in range(7)]

def get_month_days(year, month):
    _, days = monthrange(year, month)
    first = date(year, month, 1)
    return [first + timedelta(days=i) for i in range(days)]

def get_weekday_headers():
    return ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

@app.route('/')
def index():
    view_mode = request.args.get('mode', 'day')
    date_str = request.args.get('date')

    if date_str:
        selected_date = pd.to_datetime(date_str).date()
    else:
        selected_date = unique_dates[-1] if unique_dates else date.today()

    posts = []
    week_posts = []
    month_days = []
    calendar_data = {}

    if view_mode == 'day':
        posts = df[df['Publish Date (DD/MM/YYYY)'].dt.date == selected_date].to_dict('records')

    elif view_mode == 'week':
        week_dates = get_week_dates(selected_date)
        week_posts = df[df['Publish Date (DD/MM/YYYY)'].dt.date.isin(week_dates)].to_dict('records')

    elif view_mode == 'month':
        year, month = selected_date.year, selected_date.month
        month_days = get_month_days(year, month)
        for d in month_days:
            day_posts = df[df['Publish Date (DD/MM/YYYY)'].dt.date == d].to_dict('records')
            calendar_data[d] = day_posts

    elif view_mode == 'all':
        posts = df_all.to_dict('records')

    # Process posts
    for p_list in [posts, week_posts]:
        for post in p_list:
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

    # Week ranges for dropdown
    week_options = {}
    for d in unique_dates:
        start, end = get_week_range(d)
        week_options[d] = f"Week of {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"

    # Navigation - FIXED FOR MONTH VIEW
    if view_mode == 'month':
        # Previous month
        prev_month_date = selected_date - timedelta(days=32)
        prev_date = date(prev_month_date.year, prev_month_date.month, 1)
        # Next month
        next_month_date = selected_date + timedelta(days=32)
        next_date = date(next_month_date.year, next_month_date.month, 1)
    else:
        # Day/week/all navigation
        try:
            current_idx = unique_dates.index(selected_date)
            prev_date = unique_dates[current_idx - 1] if current_idx > 0 else None
            next_date = unique_dates[current_idx + 1] if current_idx < len(unique_dates) - 1 else None
        except ValueError:
            prev_date = next_date = None

    return render_template('index.html',
                           posts=posts,
                           week_posts=week_posts,
                           selected_date=selected_date,
                           view_mode=view_mode,
                           prev_date=prev_date,
                           next_date=next_date,
                           dates=unique_dates,
                           unique_month_first_days=unique_month_first_days,
                           month_days=month_days,
                           calendar_data=calendar_data,
                           weekday_headers=weekday_headers,
                           week_options=week_options,
                           logo=FH_LOGO,
                           py_version=PY_VERSION)

if __name__ == '__main__':
    app.run(debug=True)