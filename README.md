# Alday Dental Clinic – Flask Website

## Setup Instructions

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your clinic photos** (optional)
   Place your images inside `static/images/`:
   - `clinic1.jpg` – Treatment room photo
   - `clinic2.jpg` – Reception / business cards photo
   - `clinic3.jpg` – Clinic entrance / signage photo

3. **Run the app**
   ```bash
   python admin_dashboard.html

   ```

4. **Open in browser**
   Visit: http://127.0.0.1:5000

## Pages
- `/`         – Home page
- `/branches` – Branches
- `/services` – Services
- `/contact`  – Contact form
- `/book`     – Booking form (POST returns JSON)

## Folder Structure
```
alday_dental/
├── app.py
├── requirements.txt
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── branches.html
│   ├── services.html
│   ├── contact.html
│   └── book.html
└── static/
    ├── css/style.css
    ├── js/main.js
    └── images/   ← put your clinic photos here
```
