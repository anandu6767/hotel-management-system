from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from django.contrib.auth import get_user_model
from .models import Booking, Notification

User = get_user_model()


@receiver(post_save, sender=apps.get_model('core', 'InventoryItem'))
def check_inventory_threshold(sender, instance, **kwargs):
    Notification = apps.get_model('core', 'Notification')  # ✅ lazy import
    if instance.quantity < instance.threshold:
        existing = Notification.objects.filter(
            user__role='manager',
            message__icontains=instance.name,
            is_read=False
        )
        if existing.exists():
            return

        for manager in User.objects.filter(role='manager'):
            Notification.objects.create(
                user=manager,
                message=f"⚠️ Inventory low: '{instance.name}' has only {instance.quantity} left."
            )


@receiver(post_save, sender=apps.get_model('core', 'Booking'))
def notify_staff_on_booking_created(sender, instance, created, **kwargs):
    Notification = apps.get_model('core', 'Notification')  # ✅ lazy import
    if created:
        target_roles = ['receptionist', 'housekeeping']
        message = f"🛎️ New booking: Room {instance.room.room_number} booked by {instance.user.username}."

        existing = Notification.objects.filter(
            message=message,
            is_read=False
        )
        if existing.exists():
            return

        for staff in User.objects.filter(role__in=target_roles):
            Notification.objects.create(
                user=staff,
                message=message
            )

@receiver(post_save, sender=Booking)
def notify_housekeeping_on_checkout(sender, instance, **kwargs):
    if instance.status == 'Checked Out' and instance.needs_cleaning:
        message = f"🧹 Room {instance.room.room_number} needs cleaning after checkout."

        # Avoid duplicate unread messages
        if Notification.objects.filter(message=message, is_read=False).exists():
            return

        for housekeeper in User.objects.filter(role='housekeeping'):
            Notification.objects.create(
                user=housekeeper,
                message=message
            )