"""Views for public-facing pages."""
import os
from pathlib import Path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from .forms import BecomeEditorForm, FeedbackForm


def _load_email_config():
    """Load email configuration from .env for production email sending."""
    # Load .env if it exists (production path)
    env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
        except ImportError:
            pass
    
    # Return email configuration from environment
    return {
        'host': 'smtp.gmail.com',
        'port': 587,
        'use_tls': True,
        'username': os.environ.get('EMAIL_HOST_USER', ''),
        'password': os.environ.get('EMAIL_HOST_PASSWORD', ''),
        'from_email': os.environ.get('EMAIL_HOST_USER', settings.DEFAULT_FROM_EMAIL),
    }


def _send_email_with_smtp(subject, message, recipient_list):
    """Send email using SMTP with credentials from .env."""
    from django.core.mail import EmailMessage
    
    config = _load_email_config()
    
    if not config['username'] or not config['password']:
        # Fallback to Django settings (will use console backend if not configured)
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        return
    
    # Create email with explicit SMTP configuration
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=config['from_email'],
        to=recipient_list,
        connection=None,
    )
    
    # Configure SMTP connection
    from django.core.mail import get_connection
    connection = get_connection(
        backend='django.core.mail.backends.smtp.EmailBackend',
        host=config['host'],
        port=config['port'],
        username=config['username'],
        password=config['password'],
        use_tls=config['use_tls'],
    )
    
    email.connection = connection
    email.send(fail_silently=False)


def become_editor_view(request):
    """Handle the 'Become an Editor' application form."""
    if request.method == 'POST':
        form = BecomeEditorForm(request.POST)
        if form.is_valid():
            # Extract form data
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            
            # Prepare email
            subject = f'New Editor Application from {name}'
            email_body = f"""
New editor application received:

Name: {name}
Email: {email}

Message:
{message}

---
This is an automated message from TrackAdapt Wiki
            """
            
            try:
                # Send email to admin
                _send_email_with_smtp(
                    subject,
                    email_body,
                    [os.environ.get('EMAIL_HOST_USER', settings.DEFAULT_FROM_EMAIL)],
                )
                
                # Send confirmation to applicant
                _send_email_with_smtp(
                    'Your Editor Application - TrackAdapt Wiki',
                    f"""
Hello {name},

Thank you for your interest in becoming an editor for the TrackAdapt Wiki!

We have received your application and will review it shortly. We'll get back to you within 5 business days.

Best regards,
The TrackAdapt Wiki Team
                    """,
                    [email],
                )
                
                messages.success(request, 'Your application has been submitted successfully! Check your email for confirmation.')
                return redirect('become_editor')
                
            except Exception as e:
                messages.error(request, 'There was an error sending your application. Please try again later.')
                print(f"Error sending email: {e}")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BecomeEditorForm()
    
    return render(request, 'become_editor.html', {'form': form})


def feedback_view(request):
    """Handle the feedback and corrections form."""
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            # Extract form data
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            
            # Prepare email
            subject = f'New Feedback from {name}'
            email_body = f"""
New feedback received:

Name: {name}
Email: {email}

Message:
{message}

---
This is an automated message from TrackAdapt Wiki
            """
            
            try:
                # Send email to admin
                _send_email_with_smtp(
                    subject,
                    email_body,
                    [os.environ.get('EMAIL_HOST_USER', settings.DEFAULT_FROM_EMAIL)],
                )
                
                # Send confirmation to user
                _send_email_with_smtp(
                    'Your Feedback - TrackAdapt Wiki',
                    f"""
Hello {name},

Thank you for your feedback!

We have received your message and appreciate you taking the time to help us improve the TrackAdapt Wiki. 
Our team will review your feedback and take appropriate action.

Best regards,
The TrackAdapt Wiki Team
                    """,
                    [email],
                )
                
                messages.success(request, 'Your feedback has been submitted successfully! Thank you for helping us improve.')
                return redirect('feedback')
                
            except Exception as e:
                messages.error(request, 'There was an error sending your feedback. Please try again later.')
                print(f"Error sending email: {e}")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeedbackForm()
    
    return render(request, 'feedback.html', {'form': form})
