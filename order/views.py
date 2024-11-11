from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from supabase import create_client, Client

# Supabase 클라이언트 설정
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

#주문 정보 상세 조회 (purchased 한 건에 대하여)
def get_order_info(request):
  try:
    user_id = request.user.user_id
    purchased_id = request.data.get("purchased_id")

    purchased_info = supabase.table("purchased").select("*").eq("id", purchased_id).execute()

    #유저 검증
    if user_id != purchased_info[0]['user_id']:
      return Response("error: 권한 없음", status=status.HTTP_401_UNAUTHORIZED)
    
    #order_info 테이블 불러오기
    order_info = supabase.table("order_info").select("*").eq("id", purchased_info[0]['order_id']).execute()


    #데이터 정리
    final_result = {
      "item_id": purchased_info[0]["item_id"],
      "payment_method": order_info[0]["payment_method"],
      "card_info": order_info[0]["card_info"],
      "price": purchased_info[0]["price"], ##purchased테이블에는 아이템 별로 로그가 찍히므로, total_price 말고 price같긴한데...
      "refund": purchased_info[0]["refund"],
      "created_at": purchased_info[0]["created_at"], ##결제 승인 시각
      "is_confirmed": purchased_info[0]["is_confirmed"],
      "name": order_info[0]["name"],
      "phone_num": order_info[0]["phone_num"],
      "email": order_info[0]["email"]
    }
    
    return Response(final_result, status=status.HTTP_200_OK)

  except:
    return Response("error: 주문 상세 조회 실패", status=status.HTTP_400_BAD_REQUEST)