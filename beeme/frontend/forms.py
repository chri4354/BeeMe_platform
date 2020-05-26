# django imports
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import password_validation
from django.core.validators import validate_email
# third-party imports
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Invisible
# project imports
from beeme.core.models import BannedEmailDomain


# forms

class SignUpForm(forms.Form):

    email = forms.EmailField(
        label='Email Address',
        help_text='We\'ll never share your email with anyone else.'
    )

    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput
    )
    password_verify = forms.CharField(
        label='Verify Password',
        widget=forms.PasswordInput,
        strip=False
    )

    captcha = ReCaptchaField(widget=ReCaptchaV2Invisible)

    def _post_clean(self):
        super()._post_clean()
        # Validate the password after self.instance is updated with form data
        # by super().
        password = self.cleaned_data.get('password')

        if password:
            try:
                password_validation.validate_password(password)
            except forms.ValidationError as error:
                self.add_error('password_verify', error)
            pass

        return

    def clean_email(self):
        User = get_user_model()

        email = self.cleaned_data.get('email', '').lower()

        if email:
             validate_email(email)
             pass

        if email:
            email_domain = email.split('@')[-1]

            if BannedEmailDomain.objects.filter(domain=email_domain).exists():
                raise forms.ValidationError(
                    'Email address not allowed'
                )
            
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError(
                    'This email address is not available'
                )
            pass

        return email

    def clean_password_verify(self):
        password = self.cleaned_data.get('password')
        password_verify = self.cleaned_data.get('password_verify')

        if password and password_verify and password != password_verify:
            raise forms.ValidationError(
                'The two password fields didn\'t match.'
            )

        if password and len(password) < 5:
            raise forms.ValidationError(
                'Password is too short'
            )

        return password_verify

    pass
