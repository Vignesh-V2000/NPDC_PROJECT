import re
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, SetPasswordForm
from captcha.fields import CaptchaField


class AdminSetPasswordForm(SetPasswordForm):
    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters")
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r'\d', password):
            raise forms.ValidationError("Password must contain at least one number")
        if not re.search(r'[@$!%*?&]', password):
            raise forms.ValidationError("Password must contain at least one special character (@$!%*?&)")
        return password



class NPDCRegisterForm(UserCreationForm):
    TITLE_CHOICES = [
        ('Mr', 'Mr'),
        ('Ms', 'Ms'),
        ('Dr', 'Dr'),
        ('Prof', 'Prof'),
    ]

    title = forms.ChoiceField(choices=TITLE_CHOICES, required=True)
    preferred_name = forms.CharField(required=False)

    email = forms.EmailField(required=True)
    confirm_email = forms.EmailField(required=True)

    organisation = forms.CharField(required=True)
    organisation_url = forms.URLField(required=True)
    profile_url = forms.URLField(required=False)
    designation = forms.CharField(required=False)

    phone = forms.CharField(required=False)
    whatsapp_number = forms.CharField(required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    alternate_email = forms.EmailField(required=False)

    captcha = CaptchaField()

    class Meta:
        model = User
        fields = [
            'email',
            'confirm_email',
            'first_name',
            'last_name',
            'password1',
            'password2',
        ]

    # ---------- FIELD VALIDATIONS ----------

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered")
        return email

    def clean_first_name(self):
        fn = self.cleaned_data.get('first_name')
        if not fn:
            raise forms.ValidationError("First name is required")
        if not re.match(r'^[A-Za-z\s]+$', fn):
            raise forms.ValidationError("First name must contain only letters")
        return fn

    def clean_last_name(self):
        ln = self.cleaned_data.get('last_name')
        if not ln:
            raise forms.ValidationError("Last name is required")
        if not re.match(r'^[A-Za-z\s]+$', ln):
            raise forms.ValidationError("Last name must contain only letters")
        return ln

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters")
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r'\d', password):
            raise forms.ValidationError("Password must contain at least one number")
        if not re.search(r'[@$!%*?&]', password):
            raise forms.ValidationError("Password must contain at least one special character (@$!%*?&)")
        return password

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            if not phone.isdigit():
                raise forms.ValidationError("Mobile number must contain only digits")
            if len(phone) != 10:
                raise forms.ValidationError("Mobile number must be exactly 10 digits")
        return phone

    def clean_whatsapp_number(self):
        whatsapp = self.cleaned_data.get("whatsapp_number")
        if whatsapp:
            if not whatsapp.isdigit():
                raise forms.ValidationError("WhatsApp number must contain only digits")
        return whatsapp

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        confirm_email = cleaned.get("confirm_email")

        if email and confirm_email and email != confirm_email:
            self.add_error("confirm_email", "Email addresses do not match")

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class CaptchaLoginForm(AuthenticationForm):
    captcha = CaptchaField()

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            return username.lower().strip()
        return username
from .models import Profile


class UserUpdateForm(forms.ModelForm):
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered")
        return email

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class ProfileUpdateForm(forms.ModelForm):
    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            if not phone.isdigit():
                raise forms.ValidationError("Mobile number must contain only digits")
            if len(phone) != 10:
                raise forms.ValidationError("Mobile number must be exactly 10 digits")
        return phone

    class Meta:
        model = Profile
        fields = [
            'title',
            'preferred_name',
            'organisation',
            'organisation_url',
            'profile_url',
            'designation',
            'phone',
            'whatsapp_number',
            'address',
            'alternate_email',
        ]


class AdminUserEditForm(forms.ModelForm):
    """Form for admin to edit user details without password/captcha"""
    TITLE_CHOICES = [
        ('Mr', 'Mr'),
        ('Ms', 'Ms'),
        ('Dr', 'Dr'),
        ('Prof', 'Prof'),
    ]

    # User fields
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.EmailField(required=True)

    # Profile fields
    title = forms.ChoiceField(choices=TITLE_CHOICES, required=True)
    preferred_name = forms.CharField(required=False)
    organisation = forms.CharField(required=True)
    organisation_url = forms.URLField(required=True)
    profile_url = forms.URLField(required=False)
    designation = forms.CharField(required=False)
    phone = forms.CharField(required=False)
    whatsapp_number = forms.CharField(required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    alternate_email = forms.EmailField(required=False)
    
    expedition_admin_type = forms.ChoiceField(
        choices=[('', '---------')] + Profile.EXPEDITION_TYPES,
        required=False,
        label="Expedition Admin Type (For Child Admins)"
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        self.profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        
        # Populate profile fields if profile exists
        if self.profile:
            self.fields['title'].initial = self.profile.title
            self.fields['preferred_name'].initial = self.profile.preferred_name
            self.fields['organisation'].initial = self.profile.organisation
            self.fields['organisation_url'].initial = self.profile.organisation_url
            self.fields['profile_url'].initial = self.profile.profile_url
            self.fields['designation'].initial = self.profile.designation
            self.fields['phone'].initial = self.profile.phone
            self.fields['whatsapp_number'].initial = self.profile.whatsapp_number
            self.fields['address'].initial = self.profile.address
            self.fields['alternate_email'].initial = self.profile.alternate_email
            self.fields['expedition_admin_type'].initial = self.profile.expedition_admin_type

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            if not phone.isdigit():
                raise forms.ValidationError("Mobile number must contain only digits")
            if len(phone) != 10:
                raise forms.ValidationError("Mobile number must be exactly 10 digits")
        return phone

    def clean_whatsapp_number(self):
        whatsapp = self.cleaned_data.get("whatsapp_number")
        if whatsapp:
            if not whatsapp.isdigit():
                raise forms.ValidationError("WhatsApp number must contain only digits")
        return whatsapp

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Update profile
            if self.profile:
                self.profile.title = self.cleaned_data['title']
                self.profile.preferred_name = self.cleaned_data.get('preferred_name', '')
                self.profile.organisation = self.cleaned_data['organisation']
                self.profile.organisation_url = self.cleaned_data['organisation_url']
                self.profile.profile_url = self.cleaned_data.get('profile_url', '')
                self.profile.designation = self.cleaned_data.get('designation', '')
                self.profile.phone = self.cleaned_data.get('phone', '')
                self.profile.whatsapp_number = self.cleaned_data.get('whatsapp_number', '')
                self.profile.address = self.cleaned_data.get('address', '')
                self.profile.alternate_email = self.cleaned_data.get('alternate_email', '')
                
                # Update expedition admin type
                exp_type = self.cleaned_data.get('expedition_admin_type')
                if exp_type:
                    self.profile.expedition_admin_type = exp_type
                    # If made an admin, ensure they are staff
                    user.is_staff = True
                    user.save()
                else:
                    self.profile.expedition_admin_type = None
                    # We don't automatically remove staff status as they might be staff for other reasons
                
                self.profile.save()
        
        return user
