from decimal import Decimal, ROUND_HALF_UP
from .models import Notification, Booking
from django.contrib.auth import get_user_model

User = get_user_model()
def is_room_available(room, check_in, check_out):
    
    return not Booking.objects.filter(
        room=room,
        check_in__lt=check_out,
        check_out__gt=check_in
    ).exists()




round2 = lambda x: x.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calculate_bill(booking):
    nights = (booking.check_out - booking.check_in).days or 1

    room_total = Decimal(booking.room.price_per_night) * nights
    amenity_total = sum((a.price for a in booking.amenities.all()), Decimal('0.00'))
    spa_total = sum((s.price for s in booking.spa_services.all()), Decimal('0.00'))

    subtotal = room_total + amenity_total + spa_total
    tax = subtotal * Decimal('0.18')  
    discount = Decimal('0.00')        
    total = subtotal + tax - discount

    
    room_total = round2(room_total)
    amenity_total = round2(amenity_total)
    spa_total = round2(spa_total)
    subtotal = round2(subtotal)
    tax = round2(tax)
    discount = round2(discount)
    total = round2(total)

   
    booking.subtotal = subtotal
    booking.tax = tax
    booking.discount = discount
    booking.total = total
    booking.save()

    return {
        'room_price': room_total,
        'amenity_price': amenity_total,
        'spa_price': spa_total,
        'subtotal': subtotal,
        'tax': tax,
        'discount': discount,
        'total': total
    }


def notify_if_inventory_low(item):
    if item.quantity < item.threshold:
        # Check if a similar unread notification already exists
        existing = Notification.objects.filter(
            user__role='manager',
            message__icontains=item.name,
            is_read=False
        )
        if existing.exists():
            return  # Skip duplicate

        for manager in User.objects.filter(role='manager'):
            Notification.objects.create(
                user=manager,
                message=f"⚠️ Inventory low: '{item.name}' has only {item.quantity} left."
            )
