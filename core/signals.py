from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import InventoryItem, Notification
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=InventoryItem)
def check_inventory_threshold(sender, instance, **kwargs):
    if instance.quantity < instance.threshold:
        # Avoid duplicate unread notifications
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
