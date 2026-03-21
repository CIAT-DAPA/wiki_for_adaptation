# TrackAdapt Wiki

A structured, collaborative, and transparent digital environment built with Django and Wagtail CMS where researchers, practitioners, and institutions can access and manage standardized information on methods and indicators used to measure progress in climate change adaptation.

## 📋 Overview

TrackAdapt Wiki provides a comprehensive platform for documenting and sharing climate adaptation strategies, methodologies, and indicators. The system integrates with Keycloak for unified authentication and uses Google reCAPTCHA for form security.

## ⚙️ Requirements

- Python 3.10+
- Django 5.2.7
- Wagtail 7.2.1
- PostgreSQL 12+ (production)
- Keycloak 25.0+ (authentication)
- Node.js (for static assets compilation)

## 🛠️ Technology Stack

- **Backend Framework**: Django 5.2.7
- **CMS**: Wagtail 7.2.1
- **Database**: PostgreSQL (production), SQLite (development)
- **Authentication**: Mozilla Django OIDC + Keycloak
- **Web Server**: Gunicorn + Nginx (production)
- **Security**: Google reCAPTCHA v2
- **Email**: Gmail SMTP
- **Analytics**: Google Analytics 4

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/CIAT-DAPA/wiki_for_adaptation.git
cd wiki_for_adaptation
```

### 2. Create Virtual Environment

```bash
python -m venv env

# On Linux/macOS
source env/bin/activate

# On Windows
env\Scripts\activate
```

### 3. Install Dependencies

```bash
cd src/mysite
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the repository root with the following variables:

```bash
# Django Settings
DJANGO_SETTINGS_MODULE=mysite.settings.production
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=trackadapt.org,www.trackadapt.org

# Database (PostgreSQL for production)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Email Configuration (Gmail SMTP)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# Keycloak OIDC Configuration
PUBLIC_KEYCLOAK_URL=https://auth.trackadapt.org
PUBLIC_KEYCLOAK_REALM=trackadapt
PUBLIC_KEYCLOAK_CLIENT_ID=trackadapt_admin
KEYCLOAK_CLIENT_SECRET=your-keycloak-client-secret

# Google Services
GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX
RECAPTCHA_PUBLIC_KEY=your-recaptcha-site-key
RECAPTCHA_PRIVATE_KEY=your-recaptcha-secret-key
```

## 🚀 Running the Project

### Development Environment

If starting from scratch without migrations and database:

```bash
cd src/mysite

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --no-input

# Run development server
python manage.py runserver
```

The application will be available at: `http://localhost:8000`

**Note**: If you encounter circular dependency errors during `makemigrations`, you may need to migrate models individually by temporarily commenting out dependent models in `models.py` files.

### With Existing Database (Recommended)

If the project includes migrations and a database:

```bash
cd src/mysite
python manage.py runserver
```

### Production Environment

The production deployment uses Gunicorn as the WSGI server:

```bash
cd wiki_for_adaptation

# Restart Gunicorn service
bash restart_gunicorn.sh
```

For initial production setup, ensure:
1. PostgreSQL database is created
2. `.env` file is configured with production values
3. Static files are collected: `python manage.py collectstatic --no-input`
4. Migrations are applied: `python manage.py migrate`
5. Nginx is configured as reverse proxy

## 🔑 Initial Setup

### Create Superuser

```bash
python manage.py createsuperuser
```

### Access Admin Panel

- **Wagtail Admin**: `http://localhost:8000/admin/`
- **Django Admin**: `http://localhost:8000/django-admin/`

### Configure Keycloak

1. Create a realm named `trackadapt`
2. Create a client with ID `trackadapt_admin`
3. Configure redirect URIs: `https://trackadapt.org/oidc/callback/`
4. Enable reCAPTCHA in registration flow (optional)
5. Copy client secret to `.env` file

## 📁 Project Structure

```
wiki_for_adaptation/
├── src/mysite/                 # Django project root
│   ├── mysite/                 # Project settings
│   │   ├── settings/
│   │   │   ├── base.py         # Base settings
│   │   │   ├── dev.py          # Development settings
│   │   │   └── production.py   # Production settings
│   │   ├── templates/          # Global templates
│   │   ├── static/             # Global static files
│   │   ├── urls.py             # URL configuration
│   │   ├── views.py            # Custom views (forms, emails)
│   │   └── wsgi.py             # WSGI application
│   ├── home/                   # Home app (static pages)
│   │   ├── models.py           # Page models
│   │   └── templates/          # Page templates
│   ├── catalog/                # Catalog app (main content)
│   ├── search/                 # Search functionality
│   ├── manage.py               # Django management script
│   └── requirements.txt        # Python dependencies
├── wiki-login-theme/           # Keycloak custom theme
│   └── login/                  # Login pages customization
├── logs/                       # Application logs (production)
├── restart_gunicorn.sh         # Gunicorn restart script
├── Jenkinsfile                 # CI/CD pipeline configuration
├── .env                        # Environment variables (not in git)
└── README.md                   # This file
```

## ✨ Key Features

- 📝 **Content Management**: Wagtail CMS for structured content editing
- 🔐 **Single Sign-On**: Keycloak integration for unified authentication
- 🔍 **Advanced Search**: Full-text search across all content
- 📧 **Email Notifications**: Automated emails for feedback and editor applications
- 📊 **Analytics**: Google Analytics 4 integration
- 🌍 **SEO Optimized**: Meta tags and structured data for all pages
- 🎨 **Responsive Design**: Mobile-friendly interface
- 👥 **User Management**: Role-based access control


## 🚀 Deployment

The project uses Jenkins for CI/CD with the following pipeline stages:

1. **Build**: Install dependencies
2. **Test**: Run test suite
3. **Migrate**: Apply database migrations
4. **Collect Static**: Gather static files
5. **Deploy**: Restart Gunicorn service

### Manual Deployment

```bash
# On production server
cd /opt/goodall/wiki_for_adaptation

# Pull latest changes
git pull origin main

# Activate virtual environment
source env/bin/activate

# Install/update dependencies
pip install -r src/mysite/requirements.txt

# Apply migrations
cd src/mysite
python manage.py migrate

# Collect static files
python manage.py collectstatic --no-input

# Restart Gunicorn
cd ../..
bash restart_gunicorn.sh
```

## 📄 License

This project is part of the CGIAR initiative for climate change adaptation research.

## 📞 Support

For issues and questions:
- **Email**: trackadaptwiki@gmail.com
- **Website**: https://trackadapt.org

## 🔗 Related Resources

- [Wagtail Documentation](https://docs.wagtail.org/)
- [Django Documentation](https://docs.djangoproject.com/)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [CGIAR Platform for Big Data in Agriculture](https://bigdata.cgiar.org/)

