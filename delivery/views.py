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
    #사용자 정보와 결제 내역 가져오기
    user_id = request.user.user_id
    purchased_id = request.data.get("purchased_id")

    #유저 검증
    user_requested = supabase.table("purchased").select("user_id").eq("purchased_id", purchased_id).execute()
    if user_id != user_requested[0]['user_id']:
      return Response("error: 권한 없음", status=status.HTTP_401_UNAUTHORIZED)

    #운송장 번호 가져오기
    delivery_info = supabase.table("delivery").select("tracking_num", "courier_name").eq("purchased_id", purchased_id).execute()
    tracking_num = delivery_info[0]["tracking_num"]
    courier_name = delivery_info[0]["courier_name"]

    #구글 배송조회 url
    redirect_url = f"https://www.google.com/search?q={courier_name}+{tracking_num}"

    return Response({redirect_url}, status=status.HTTP_200_OK)

  except:
    return Response("error: 배송 조회 실패", status=status.HTTP_400_BAD_REQUEST)
  
def get_order_info(request):
  try:
    user_id = request.user.user_id
    purchased_id = request.data.get("purchased_id")

    purchased_info = supabase.table("purchased").select("*").eq("purchased_id", purchased_id).execute()

    #유저 검증
    if user_id != purchased_info[0]['user_id']:
      return Response("error: 권한 없음", status=status.HTTP_401_UNAUTHORIZED)
    
    #order_info 테이블 불러오기
    order_info = supabase.table("order_info").select("*").eq("id", purchased_info[0]['order_id']).execute()


    #데이터 정리
    final_result = {
      ""
    }
  
    

  except:
    return Response("error: 주문 상세 조회 실패", status=status.HTTP_400_BAD_REQUEST)


#purchased table은 구매한 각 물건에 대응되고, 
#order_info table은 주문 건에 대응됨. 

#가령 A,B 물건을 한 번에 구매한 경우 order_info에는 1개, purchased table에는 2개의 행이 추가됨.