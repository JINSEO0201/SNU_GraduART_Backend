# rest_framework_simplejwt.authentication의 JWTAuthentication을 상속받아 CustomJWTAuthentication 클래스를 작성
# get_user 메서드를 오버라이드하여 사용자 정보를 Supabase에서 가져오도록 수정
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import exceptions
from .custom_user import CustomUser
from supabase import create_client
from django.conf import settings
from rest_framework.permissions import AllowAny
# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

class CustomJWTAuthentication(JWTAuthentication):
    # 코드 흐름을 보자면 다음과 같다
    # @permission_classes([IsAuthenticated]) 데코레이터가 호출되면
    # CustomJWTAuthentication.authenticate(request) 메서드가 호출된다.
    # authenticate 메서드는 쿠키에서 access_token을 가져와서 유효성 검사를 한다.
    # 토큰이 유효하다면 get_user 메서드를 호출하여 사용자 정보를 가져온다.
    # 최종적으로 CustomUser 인스턴스와 토큰을 반환한다.
    def authenticate(self, request):
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
        
        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            return (user, validated_token)
        except exceptions.AuthenticationFailed:
            # Return None to indicate authentication failure without raising an exception
            return None

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
