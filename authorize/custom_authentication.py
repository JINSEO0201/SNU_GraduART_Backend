# rest_framework_simplejwt.authentication의 JWTAuthentication을 상속받아 CustomJWTAuthentication 클래스를 작성
# get_user 메서드를 오버라이드하여 사용자 정보를 Supabase에서 가져오도록 수정
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _
from .custom_user import CustomUser  # Import your custom user class
from supabase import create_client
from django.conf import settings

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = validated_token['user_id']
        except KeyError:
            raise exceptions.AuthenticationFailed(
                _('Token contained no recognizable user identification'),
                code='token_invalid'
            )

        # Fetch the user from Supabase
        user_data = supabase.table('users').select('*').eq('user_id', user_id).execute()
        if not user_data.data:
            raise exceptions.AuthenticationFailed(_('User not found'), code='user_not_found')

        user_info = user_data.data[0]
        return CustomUser(user_info)
