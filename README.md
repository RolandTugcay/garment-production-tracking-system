# Garments Production Tracking System

## Run locally

1. Install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and set `FLASK_SECRET_KEY` to a long, random value.
   Keep `.env` private; it is excluded from version control.
3. Start the app:

   ```powershell
   python app.py
   ```