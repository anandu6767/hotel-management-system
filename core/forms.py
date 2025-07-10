from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, Room
from .models import Booking, Amenity, SpaService, GuestProfile
from .models import Maintenance
from datetime import date
from .models import InventoryItem, InventoryUsageLog
from .models import Feedback
from django.contrib.auth import get_user_model
from .models import StaffSalary, StaffAttendance 
from .models import ContactMessage

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']
        
class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = '__all__'
        widgets = {
            'amenities': forms.CheckboxSelectMultiple(),  
            'spa_services': forms.CheckboxSelectMultiple(),
        }
        
class BookingForm(forms.ModelForm):
    
    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    spa_services = forms.ModelMultipleChoiceField(
        queryset=SpaService.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Booking
        fields = ['room', 'check_in', 'check_out', 'amenities', 'spa_services', 'id_proof']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_out': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'room': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                existing_class = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = f"{existing_class} form-control".strip()

        
        self.fields['id_proof'].required = True

        #  Pre-fill check-in/check-out from GET parameters if available
        if request:
            check_in = request.GET.get('check_in')
            check_out = request.GET.get('check_out')
            if check_in:
                self.fields['check_in'].initial = check_in
            if check_out:
                self.fields['check_out'].initial = check_out

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')

        if check_in and check_in < date.today():
            raise forms.ValidationError("Check-in date cannot be in the past.")

        if check_in and check_out and check_out <= check_in:
            raise forms.ValidationError("Check-out must be after check-in.")

        return cleaned_data

        
class ReceptionistBookingForm(forms.ModelForm):
    #  Amenities and Spa Services with Bootstrap styling
    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    spa_services = forms.ModelMultipleChoiceField(
        queryset=SpaService.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    class Meta:
        model = Booking
        fields = ['user', 'room', 'check_in', 'check_out', 'amenities', 'spa_services']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'check_in': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_out': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')

        if check_in and check_in < date.today():
            raise forms.ValidationError("Check-in date cannot be in the past.")
        if check_in and check_out and check_out <= check_in:
            raise forms.ValidationError("Check-out must be after check-in.")

        return cleaned_data

    
class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['room', 'issue', 'scheduled_date']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'issue': forms.Textarea(attrs={'rows': 3}),
        }

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'description', 'quantity', 'threshold']

class InventoryUsageForm(forms.ModelForm):
    class Meta:
        model = InventoryUsageLog
        fields = ['item', 'room', 'used_by', 'quantity_used']


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        # Exclude 'booking' from the visible form
        fields = ['rating', 'cleanliness_rating', 'service_rating', 'facilities_rating', 'comment']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
            

class BookingWithUserForm(BookingForm):
    user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='guest'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta(BookingForm.Meta):
        fields = ['user'] + BookingForm.Meta.fields
        
class GuestUserForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'first_name', 'last_name']

class GuestProfileForm(forms.ModelForm):
    class Meta:
        model = GuestProfile
        fields = ['phone', 'id_proof', 'address']

class WalkInBookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['room', 'check_in', 'check_out', 'status','id_proof']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'check_in': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_out': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class StaffSalaryForm(forms.ModelForm):
    class Meta:
        model = StaffSalary
        fields = ['user', 'daily_rate']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'daily_rate': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class StaffAttendanceForm(forms.ModelForm):
    class Meta:
        model = StaffAttendance
        fields = ['user', 'date', 'present']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'present': forms.CheckboxInput(),
        }

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }
