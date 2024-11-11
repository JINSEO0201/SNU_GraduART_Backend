from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from supabase import create_client, Client
from django.utils import timezone

# Supabase 클라이언트 설정
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@api_view(['GET'])
def get_delivery_status(request):
  try:
    # 사용자 정보와 결제 내역 가져오기
    user_id = request.user.user_id
    item_id = request.data.get("item_id")

    # 유저 검증
    purchased_info = supabase.table("purchased").select("user_id", "id").eq("item_id", item_id).execute()
    if not purchased_info.data or user_id != purchased_info.data[0]['user_id']:
      return Response("error: 권한 없음", status=status.HTTP_401_UNAUTHORIZED)

    # 운송장 번호 가져오기
    delivery_info = supabase.table("delivery").select("tracking_num", "courier_name").eq("purchased_id", purchased_info[0]["id"]).execute()
    tracking_num = delivery_info[0]["tracking_num"]
    courier_name = delivery_info[0]["courier_name"]

    # 네이버 배송조회 url
    redirect_url = f"https://search.naver.com/search.naver?query={courier_name}{tracking_num}"

    return Response({redirect_url}, status=status.HTTP_200_OK)

  except:
    return Response("error: 배송 조회 실패", status=status.HTTP_400_BAD_REQUEST)
