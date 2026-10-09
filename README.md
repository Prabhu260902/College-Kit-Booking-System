# College Event Kit Booking System

This is a local application to book an equipment kit. 

## Tech Stack
- **Backend**: Django 4.2
- **Frontend**: Django templates, HTML, CSS (Glassmorphism aesthetics), basic JavaScript
- **Database**: MongoDB (PyMongo)
- **Authentication**: Custom JWT

## Prerequisites
- Python 3.9+
- MongoDB instance running locally on `mongodb://localhost:27017/`

## Setup Instructions

1. **Start MongoDB**: Ensure your local MongoDB server is running.
2. **Install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install django pymongo pyjwt pytz
   ```
3. **Run the server**:
   ```bash
   python manage.py runserver
   ```
4. **Access the application**: Open `http://127.0.0.1:8000` in your web browser.

## Predefined Accounts
The system automatically initializes accounts and a dummy kit on the first run.
- **Admin**: `username: Admin`, `password: 1234`
- **User1**: `username: User1`, `password: 1234`
- **User2**: `username: User2`, `password: 1234`

## Automated Tasks
To run the background cron job that maintains bookings (e.g. automatically rejecting expired pending bookings and handling equipment issues), execute the following management command on a schedule (e.g., using `cron` on macOS/Linux):
```bash
python manage.py maintain_bookings
```
