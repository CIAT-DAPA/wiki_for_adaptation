"""Views for public-facing pages."""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from .forms import BecomeEditorForm, FeedbackForm


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
                send_mail(
                    subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.DEFAULT_FROM_EMAIL],  # Send to ourselves
                    fail_silently=False,
                )
                
                # Send confirmation to applicant
                send_mail(
                    'Your Editor Application - TrackAdapt Wiki',
                    f"""
Hello {name},

Thank you for your interest in becoming an editor for the TrackAdapt Wiki!

We have received your application and will review it shortly. We'll get back to you within 5 business days.

Best regards,
The TrackAdapt Wiki Team
                    """,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
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
                send_mail(
                    subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.DEFAULT_FROM_EMAIL],  # Send to ourselves
                    fail_silently=False,
                )
                
                # Send confirmation to user
                send_mail(
                    'Your Feedback - TrackAdapt Wiki',
                    f"""
Hello {name},

Thank you for your feedback!

We have received your message and appreciate you taking the time to help us improve the TrackAdapt Wiki. 
Our team will review your feedback and take appropriate action.

Best regards,
The TrackAdapt Wiki Team
                    """,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
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
