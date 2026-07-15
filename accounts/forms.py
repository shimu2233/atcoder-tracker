from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import CustomUser
class SignupForm(UserCreationForm):
    class Meta:
        model=CustomUser
        fields=['username', 'email', 'atcoder_username']
        labels = {
            'username': 'ユーザー名',
            'email': 'メールアドレス',
            'atcoder_username': 'AtCoderユーザー名',
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'パスワード'
        self.fields['password2'].label = 'パスワード（確認）'
        self.fields['password1'].help_text = '8文字以上で、数字だけにならないようにしてください。'
        self.fields['email'].help_text = '入力は不要です'

