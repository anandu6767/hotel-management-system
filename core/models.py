from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

# ---------------------
# Custom User Model
# ---------------------
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('receptionist', 'Receptionist'),
        ('housekeeping', 'Housekeeping'),
        ('guest', 'Guest'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='guest')

    def __str__(self):
        return f"{self.username} ({self.role})"


class Amenity(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)  # ✅ Add this line

    def __str__(self):
        return f"{self.name} (₹{self.price})"
    
class SpaService(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    
    def __str__(self):
        return f"{self.name} (₹{self.price})"


# ---------------------
# Room Model
# ---------------------
class Room(models.Model):
    ROOM_TYPES = [
        ('Single', 'Single'),
        ('Double', 'Double'),
        ('Suite', 'Suite'),
    ]

    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='Single')
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)
    amenities = models.ManyToManyField(Amenity, blank=True)
    spa_services = models.ManyToManyField(SpaService, blank=True)  # ✅ NEW
    image = models.ImageField(upload_to='room_images/', blank=True, null=True)

    def __str__(self):
        return f"{self.room_number} - {self.room_type} ({'Available' if self.is_available else 'Occupied'})"


# ---------------------
# Booking Model
# ---------------------
class Booking(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Checked In', 'Checked In'),
        ('Checked Out', 'Checked Out'),
        ('Canceled', 'Canceled'),
        ('No-Show', 'No-Show'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('Cash', 'Cash'),
        ('UPI', 'UPI'),
        ('Card', 'Card'),
        ('Wallet', 'Wallet'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'guest'}
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    amenities = models.ManyToManyField(Amenity, blank=True)
    spa_services = models.ManyToManyField(SpaService, blank=True)
    needs_cleaning = models.BooleanField(default=False)
    id_proof = models.ImageField(upload_to='booking_id_proofs/', blank=True, null=True)
    cleaned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'housekeeping'},
        related_name='cleaned_bookings'
    )
    cleaned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Billing & Payment Fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True
    )
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    payment_time = models.DateTimeField(blank=True, null=True)# For gateway like Razorpay

    def __str__(self):
        return f"{self.user.username} - Room {self.room.room_number} ({self.status})"

    @property
    def total_nights(self):
        return (self.check_out - self.check_in).days


# ---------------------
# Maintenance Model
# ---------------------
class Maintenance(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    issue = models.TextField()
    scheduled_date = models.DateField()
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Room {self.room.room_number} - Issue on {self.scheduled_date} ({'Done' if self.is_completed else 'Pending'})"


#Inventory

class InventoryItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=0)
    threshold = models.PositiveIntegerField(default=10)
    last_updated = models.DateTimeField(auto_now=True)

    def is_below_threshold(self):
        return self.quantity < self.threshold

    def __str__(self):
        return self.name

class InventoryUsageLog(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL)
    used_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    quantity_used = models.PositiveIntegerField()
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name} used by {self.used_by.username} for Room {self.room.room_number if self.room else '-'}"


class Service(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    
class Feedback(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]  # 1 to 5 stars

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'guest'})
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    cleanliness_rating = models.IntegerField(choices=RATING_CHOICES)
    service_rating = models.IntegerField(choices=RATING_CHOICES)
    facilities_rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback from {self.user.username} ({self.rating}★)"



class RoomImage(models.Model):
    room = models.ForeignKey('Room', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='room_images/')

    def __str__(self):
        return f"Image for Room {self.room.room_number}"
    
class GuestProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    id_proof = models.ImageField(upload_to='id_proofs/')
    address = models.TextField()

    def __str__(self):
        return f"{self.user.username} - Guest Profile"
    
# ---------------------
# Salary and Attendance
# ---------------------

class StaffSalary(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['receptionist', 'housekeeping']}
    )
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_salaries'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - ₹{self.salary_per_day}/day"



class StaffAttendance(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role__in': ['receptionist', 'housekeeping']}
    )
    date = models.DateField()
    present = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
       return f"{self.user.username} - {'Present' if self.present else 'Absent'} on {self.date}"

    

class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # ✅ Use dynamic reference
        on_delete=models.CASCADE
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"To {self.user.username}: {self.message[:50]}"
    

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.subject} from {self.name}"