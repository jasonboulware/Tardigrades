# Amara, universalsubtitles.org
#
# Copyright (C) 2013 Participatory Culture Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see
# http://www.gnu.org/licenses/agpl-3.0.html.

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import EMPTY_VALUES
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.html import format_html
from django.utils.http import urlsafe_base64_encode
from captcha.fields import CaptchaField
from django.template import loader
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings

from auth.models import CustomUser as User
from auth.validators import PasswordStrengthValidator

class UserField(forms.Field):
    default_error_messages = {
        'invalid': _(u'Invalid user'),
    }

    def prepare_value(self, value):
        if isinstance(value, User):
            return value.username
        return value

    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        if isinstance(value, User):
            return value
        try:
            return User.objects.get(username=value)
        except User.DoesNotExist:
            raise forms.ValidationError(self.error_messages['invalid'])

class CustomUserCreationForm(UserCreationForm):
    captcha = CaptchaField()
    class Meta:
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = 'create'
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True

    def validate_password(self, password):
        # remove this post-1.9 when setting is used
        user_inputs = [self.cleaned_data.get("email"), self.cleaned_data.get("username")]
        validator = PasswordStrengthValidator()
	validator.validate(password, user_inputs=user_inputs)

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def clean_password1(self):
	try:
            self.validate_password(self.cleaned_data.get("password1"))
            return self.cleaned_data.get("password1")
        except forms.ValidationError as e:
            raise e

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class ChooseUserForm(forms.Form):
    """
    Used in the login trap mechanism
    """

    username = forms.CharField(max_length=100)

    def clean_username(self):
        data = self.cleaned_data['username']

        try:
            data = User.objects.get(username=data)
        except User.DoesNotExist:
            raise forms.ValidationError("User doesn't exist.")

        return data

class SecureAuthenticationForm(AuthenticationForm):
    captcha = CaptchaField()

class EmailForm(forms.Form):
    email = forms.EmailField(label=_("E-mail"), max_length=100)
    url = forms.URLField(required=False, widget=forms.HiddenInput())
    first_name = forms.CharField(max_length=100, required=False, widget=forms.HiddenInput())
    last_name = forms.CharField(max_length=100, required=False, widget=forms.HiddenInput())
    avatar = forms.URLField(required=False, widget=forms.HiddenInput())

class CustomSetPasswordForm(forms.Form):
    """
    A form that lets a user change set their password without entering the old
    password
    """
    error_messages = {
        'invalid_email': _("The email address given doesn't match the user."),
        'password_mismatch': _("The two password fields didn't match."),
    }
    email_address = forms.EmailField(label=_("Verify email address"))
    new_password1 = forms.CharField(label=_("New password"),
                                    widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"),
                                    widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(CustomSetPasswordForm, self).__init__(*args, **kwargs)

    def validate_password(self, password):
        # remove this post-1.9 when setting is used
        user_inputs = [self.user.email, self.user.username]
        validator = PasswordStrengthValidator()
	validator.validate(password, user_inputs)

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
	try:
            self.validate_password(password)
        except forms.ValidationError as e:
            raise e
        return password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        return password2

    def clean_email_address(self):
        email = self.cleaned_data.get('email_address')
        if email != self.user.email:
            raise forms.ValidationError(
                self.error_messages['invalid_email'],
                code='invalid_email',
            )

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data['new_password1'])
        if commit:
            self.user.save()
        return self.user

class CustomPasswordResetForm(forms.Form):
    """
    This custom version of the password reset form has two differences with
    the default one:
    * It sends an email to every user matching the address, even to the ones
    where has_usable_password is false so that oauth users can set a
    password and become a regular amara user
    * It adds data to context for the templates so that emails and views
    can describe better what will happen to the account if password is
    reset
    """
    email = forms.EmailField(label=_("E-mail"), max_length=75)

    def clean_email(self):
        """
        Validates that an active user exists with the given email address.
        """
        email = self.cleaned_data["email"]
        self.users_cache = User.objects.filter(email__iexact=email,
                                               is_active=True)
        return email

    def save(self,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             html_email_template_name=None,
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None,
             **opts):
        """
        Generates a one-use only link for resetting password and sends to the
        user.
        """
        from django.core.mail import send_mail
        for user in self.users_cache:
            c = {
                'email': user.email,
                'domain': settings.HOSTNAME,
                'site_name': 'Amara',
                'uid': urlsafe_base64_encode(force_bytes(user.id)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': use_https and 'https' or 'http',
                'amara_user': user.has_valid_password(),
            }
            subject = loader.render_to_string(subject_template_name, c)
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            # FIXME: should use html_email_template_name if present
            email = loader.render_to_string(email_template_name, c)
            send_mail(subject, email, from_email, [user.email])

class SecureCustomPasswordResetForm(CustomPasswordResetForm):
    captcha = CaptchaField()

class DeleteUserForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(DeleteUserForm, self).__init__(*args, **kwargs)
        # Can't find a lazy format_html
        self.fields['password'].help_text = format_html(
            _('<a href="{link}">Forgot your password?</a>'),
            link=reverse('password_reset')
            )
        self.fields['delete_videos_and_subtitles'].help_text = format_html(
            _('This will delete videos that you have added to Amara that no other user has added subtitles to. It will also delete the related subtitles. For more details on deactivating or deleting your profile or removing subtitles and videos you\'ve collaborated on with other Amara members please read <a href="{link}">Deactivating your Amara Account</a>'),
            link="https://support.amara.org/support/solutions/articles/216336-deactivating-your-user-account"
            )

    password = forms.CharField(widget=forms.PasswordInput(), 
        label="Please enter your password to confirm.")
    delete_account_data = forms.BooleanField(required=False,
        help_text="This will erase your personal data, including your personal name, photo, and any other data on your user profile.")
    delete_videos_and_subtitles = forms.BooleanField(required=False)

