from django.shortcuts import redirect
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
import requests
from supabase import create_client, Client
import uuid
import re

# Supabase 클라이언트 설정
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@api_view(['GET'])
def google_login(request):
    # Supabase OAuth URL 생성
    # google을 provider로 지정하고, google 인증 후 사용자가 돌아올 redirect_uri를 지정
    redirect_uri = request.build_absolute_uri('/api/v1/auth/google/callback')
    auth_url = f"{settings.SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to={redirect_uri}"
    return redirect(auth_url)

@api_view(['GET'])
def google_callback(request):
    # google 인증 결과 받은 code
    code = request.GET.get('code')
    
    # Supabase에 액세스 토큰 요청
    token_url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=authorization_code"
    headers = {
        'Content-Type': 'application/json',
        'apikey': settings.SUPABASE_KEY
    }
    data = {
        'code': code,
        'redirect_to': request.build_absolute_uri('/api/v1/auth/google/callback')
    }
    response = requests.post(token_url, json=data, headers=headers)
    token_data = response.json()

    if 'error' in token_data:
        return Response({'error': token_data['error_description']}, status=status.HTTP_400_BAD_REQUEST)

    # 받아온 토큰으로 사용자 정보 조회
    user_data = supabase.auth.get_user(token_data['access_token'])
    user_id = user_data.user.id

    # 이미 등록된 사용자인지 검색
    existing_user = supabase.table('users').select('*').eq('user_id', user_id).eq('oauth_provider', 'google').execute()

    if not existing_user.data:
        # 새 사용자인 경우 DB에 추가
        email = user_data.user.email
        dummy_password = str(uuid.uuid4()) # 임의의 비밀번호 생성
        hashed_password = make_password(dummy_password)

        user_info = {
            'user_id': user_id,
            'email': email,
            'password': hashed_password,
            'oauth_provider': 'google',
            'full_name': user_data.user.user_metadata.get('full_name', ''),
            'created_at': timezone.now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        }
        result = supabase.table('users').insert(user_info).execute()
        user_id = result.data[0]['user_id']
    else:
        user_id = existing_user.data[0]['user_id']

    # JWT 토큰 생성
    refresh = RefreshToken()
    refresh['user_id'] = user_id
    refresh.set_exp(lifetime=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'])
    access_token = refresh.access_token
    access_token.set_exp(lifetime=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'])
    
    return Response({
        'access_token': str(access_token),
        'refresh_token': str(refresh)
    })


@api_view(['POST'])
def token_refresh(request):
    refresh_token = request.data.get('refresh_token')
    if not refresh_token:
        return Response({'error': '리프레시 토큰이 제공되지 않았습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(refresh_token)
        access_token = refresh.access_token
        access_token.set_exp(lifetime=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'])

        return Response({
            'access_token': str(access_token),
        })
    except TokenError:
        return Response({'error': '유효하지 않거나 만료된 토큰입니다.'}, status=status.HTTP_401_UNAUTHORIZED)


def is_password_valid(password):
    if len(password) < 8:
        return False
    if not re.search('[a-zA-Z]', password):
        return False
    if not re.search('[0-9]', password):
        return False
    if not re.search('[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True


@api_view(['POST'])
def register(request):
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        full_name = request.data.get('full_name')

        # 필수 입력 항목 검사
        if not email or not password:
            return Response({'error': '이메일과 비밀번호는 필수 입력 항목입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not is_password_valid(password):
            return Response({'error': '비밀번호는 8자 이상, 영문, 숫자, 특수문자를 포함해야 합니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # unique 항목인 이메일 중복 검사
        existing_user = supabase.table('users').select('*').eq('email', email).execute()
        if existing_user.data:
            return Response({'error': '이미 등록된 이메일입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 중복되지 않는 uuid 생성
        while True:
            user_id = str(uuid.uuid4())
            existing_user = supabase.table('users').select('*').eq('user_id', user_id).execute()
            if not existing_user.data:
                break
        
        hashed_password = make_password(password)
        user_info = {
            'user_id': user_id,
            'email': email,
            'password': hashed_password,
            'oauth_provider': 'local',
            'full_name': full_name,
            'created_at': timezone.now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        }

        # 사용자 정보 저장
        result = supabase.table('users').insert(user_info).execute()

        if result.data:
            # JWT 토큰 생성
            refresh = RefreshToken()
            refresh['user_id'] = user_id
            refresh.set_exp(lifetime=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'])
            access_token = refresh.access_token
            access_token.set_exp(lifetime=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'])

            return Response({
                'access_token': str(access_token),
                'refresh_token': str(refresh)
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': '회원가입 실패'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except:
        return Response({'error': f'회원가입 중 오류가 발생했습니다'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def login(request):
    try:
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': '이메일과 비밀번호는 필수 입력 항목입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_data = supabase.table('users').select('*').eq('email', email).execute()

        if not user_data.data:
            return Response({'error': '존재하지 않는 계정입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = user_data.data[0]
        if not check_password(password, user['password']):
            return Response({'error': '비밀번호가 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # JWT 토큰 생성
        refresh = RefreshToken()
        refresh['user_id'] = user['user_id']
        refresh.set_exp(lifetime=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'])
        access_token = refresh.access_token
        access_token.set_exp(lifetime=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'])

        return Response({
            'access_token': str(access_token),
            'refresh_token': str(refresh)
        })
    except:
        return Response({'error': f'로그인 중 오류가 발생했습니다'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get('refresh_token')
        refresh = RefreshToken(refresh_token)
        refresh.blacklist()
        return Response({'message': '로그아웃 되었습니다.'})
    except:
        return Response({'error': '로그아웃 중 오류가 발생했습니다.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    try:
        user_id = request.user['user_id']
        user_data = supabase.table('users').select('*').eq('user_id', user_id).execute()
        
        if len(user_data.data) == 0:
            return Response({'error': '사용자를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        
        user = user_data.data[0]
        return Response({
            'email': user['email'],
            'full_name': user['full_name'],
            'oauth_provider': user['oauth_provider']
        })
    except:
        return Response({'error': f'사용자 정보 조회 중 오류가 발생했습니다'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
