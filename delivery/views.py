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
def get_delivery_status(request, item_id):
  try:
    # 사용자 정보와 결제 내역 가져오기
    user_id = request.user.user_id
    item_id = str(item_id)

    print(f"user_id: {user_id}, item_id: {item_id}")

    # 구매 내역 조회
    purchased_info = supabase.table("purchased").select("*").eq("user_id", user_id).eq("item_id", item_id).execute()
    if not purchased_info.data:
      return Response("error: 구매 내역이 없습니다.", status=status.HTTP_400_BAD_REQUEST)
  
    # 운송장 번호 가져오기
    purchased_id = purchased_info.data[0]["id"]
    print(f"purchased_id: {purchased_id}")
    delivery_info = supabase.table("delivery").select("tracking_num", "courier_name").eq("purchased_id", purchased_id).execute()
    tracking_num = delivery_info.data[0]["tracking_num"]
    courier_name = delivery_info.data[0]["courier_name"]

    # 네이버 배송조회 url
    redirect_url = f"https://search.naver.com/search.naver?query={courier_name}{tracking_num}"

    return Response({"redirect_url": redirect_url}, status=status.HTTP_200_OK)

  except:
    return Response("error: 배송 조회 실패", status=status.HTTP_400_BAD_REQUEST)
