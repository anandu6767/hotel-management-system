from .models import Notification

def unread_notification_count(request):
    if request.user.is_authenticated:
        return {
            'unread_notification_count': Notification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
        }
    return {}


from .models import ContactMessage

def unread_contact_messages(request):
    if request.user.is_authenticated and request.user.role in ['receptionist', 'manager']:
        count = ContactMessage.objects.filter(is_read=False).count()
        return {'unread_contact_count': count}
    return {'unread_contact_count': 0}