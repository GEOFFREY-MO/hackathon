# SmartRetail AI

SmartRetail AI is a retail operations and analytics platform that combines POS workflows, inventory management, services, expenses, and an embedded AI assistant with OCR chart understanding. It is mobile-friendly, supports barcode scanning, and degrades gracefully to on-database insights when cloud AI is unavailable.

Founders: Geofrey Mokami (Founder), Francis Muthengi (Co‑founder), Kefa Mwita (Co‑founder)

## Features

- POS and inventory with barcode scanning
- Services and provider assignments, expense tracking, financial accounts
- AI assistant (OpenAI/Gemini) embedded on every page via floating chat
- OCR (Tesseract + OpenCV): capture/select charts and auto-explain in plain English
- Responsive UI with off‑canvas navigation and dark mode

## Tech Stack

- Backend: Flask, SQLAlchemy, Flask‑Login, Flask‑Migrate
- Frontend: Bootstrap 5, React (optional future UI), TypeScript ready
- AI/OCR: OpenAI/Gemini, Tesseract OCR, OpenCV, Pillow
- DB: SQLite by default; Postgres recommended for production

## Quick Start (Local)

### Prerequisites
- Python 3.8 or higher
- PostgreSQL (for production)
- Virtual environment (recommended)

### Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/SmartRetailAI.git
cd SmartRetailAI
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
copy NUL .env  # Windows
echo SECRET_KEY=dev > .env
echo FLASK_ENV=development >> .env
echo DATABASE_URL=sqlite:///smartretail.db >> .env
# Add OPENAI_API_KEY or GEMINI_API_KEY if available
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the development server:
```bash
flask run
```

### Production Deployment

1. Set up a production environment:
```bash
export FLASK_ENV=production
export SECRET_KEY=your-secure-secret-key
export DATABASE_URL=postgresql://user:password@localhost/smartretail
```

2. Install production dependencies:
```bash
pip install gunicorn psycopg2-binary
```

3. Run with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
```

### Deployment Options

#### Option 1: Traditional VPS (e.g., DigitalOcean, Linode)
1. Set up a VPS with Ubuntu 20.04
2. Install required packages:
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx postgresql
```
3. Configure Nginx as reverse proxy
4. Set up SSL with Let's Encrypt
5. Use systemd for process management

#### Option 2: Containerized Deployment (Docker)
1. Build the Docker image:
```bash
docker build -t smartretail .
```
2. Run the container:
```bash
docker run -d -p 8000:8000 --env-file .env smartretail
```

#### Option 3: Platform as a Service (e.g., Heroku)
1. Install Heroku CLI
2. Create a new Heroku app
3. Set up environment variables
4. Deploy:
```bash
git push heroku main
```

### Security Considerations

1. Always use HTTPS in production
2. Keep dependencies updated
3. Use strong secret keys
4. Implement rate limiting
5. Regular security audits
6. Database backups

### Monitoring

1. Set up logging:
```python
import logging
logging.basicConfig(filename='app.log', level=logging.INFO)
```

2. Monitor application metrics
3. Set up error tracking
4. Regular performance monitoring

### Backup Strategy

1. Database backups:
```bash
pg_dump -U username database_name > backup.sql
```

2. File system backups
3. Regular backup testing
4. Off-site backup storage

## Support

For support, please open an issue in this repository or contact the maintainers.