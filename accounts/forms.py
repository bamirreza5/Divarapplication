from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="نام کاربری", widget=forms.TextInput(attrs={
        "autocomplete": "username", "dir": "ltr", "placeholder": "نام کاربری شما",
    }))
    password = forms.CharField(label="رمز عبور", strip=False, widget=forms.PasswordInput(
        attrs={"autocomplete": "current-password", "dir": "ltr"}
    ))


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="نام شما", max_length=150)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"dir": "ltr", "autocomplete": "username"})
        for name in ("password1", "password2"):
            self.fields[name].widget.attrs.update({"dir": "ltr", "autocomplete": "new-password"})
