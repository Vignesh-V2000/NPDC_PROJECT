from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from .models import ActivityLog
from .middleware import get_current_request
from data_submission.models import DatasetSubmission
from users.models import Profile

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    ActivityLog.objects.create(
        actor=user,
        action_type='LOGIN',
        ip_address=ip,
        remarks='User logged in',
        status='SUCCESS',
        path=request.path
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    ActivityLog.objects.create(
        actor=user,
        action_type='LOGOUT',
        ip_address=ip,
        remarks='User logged out',
        status='SUCCESS',
        path=request.path
    )

@receiver(post_save, sender=DatasetSubmission)
def log_dataset_submission(sender, instance, created, **kwargs):
    request = get_current_request()
    user = request.user if request and request.user.is_authenticated else instance.submitter
    ip = get_client_ip(request) if request else None
    
    action_type = 'CREATE' if created else 'UPDATE'
    remarks = f"Dataset '{instance.title}' was {action_type.lower()}d."
    
    # Check for specific status changes if updated
    if not created:
         # Ideally we would check pre-save state, but for now we look at current status
         # This is a simplification; for detailed transitions we'd need a pre_save signal or dirty fields mixin
         if instance.status == 'approved':
             action_type = 'APPROVE'
             remarks = f"Dataset '{instance.title}' was approved."
         elif instance.status == 'rejected':
             action_type = 'REJECT'
             remarks = f"Dataset '{instance.title}' was rejected."
         elif instance.status == 'submitted':
             action_type = 'SUBMIT'
             remarks = f"Dataset '{instance.title}' was submitted."

    ActivityLog.objects.create(
        actor=user,
        action_type=action_type,
        ip_address=ip,
        remarks=remarks,
        entity_name='DatasetSubmission',
        path=request.path if request else ''
    )

@receiver(post_save, sender=Profile)
def log_profile_update(sender, instance, created, **kwargs):
    request = get_current_request()
    user = request.user if request and request.user.is_authenticated else instance.user
    ip = get_client_ip(request) if request else None

    action_type = 'CREATE' if created else 'UPDATE'
    remarks = f"Profile for '{instance.user.email}' was {action_type.lower()}d."
    
    if not created:
        if instance.is_approved:
             # Only log as approve if it might be a transition (hard to tell without prev state here, but acceptable)
             # Better logic: if the admin triggered this, it's an approval
             pass

    ActivityLog.objects.create(
        actor=user,
        action_type=action_type,
        ip_address=ip,
        remarks=remarks,
        entity_name='Profile',
        path=request.path if request else ''
    )

@receiver(post_delete, sender=DatasetSubmission)
def log_dataset_deletion(sender, instance, **kwargs):
    request = get_current_request()
    user = request.user if request and request.user.is_authenticated else None
    ip = get_client_ip(request) if request else None
    
    ActivityLog.objects.create(
        actor=user,
        action_type='DELETE',
        ip_address=ip,
        remarks=f"Dataset '{instance.title}' was deleted.",
        entity_name='DatasetSubmission',
        path=request.path if request else ''
    )
