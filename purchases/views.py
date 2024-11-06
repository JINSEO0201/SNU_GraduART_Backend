from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
import os
import requests
from supabase import create_client, Client
import time
from django.utils import timezone
from django.conf import settings

# Supabase 클라이언트 설정
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

@api_view(['GET'])
def get_purchases(request):
    try:
        # 사용자 ID로 구매 내역 조회
        user_id = request.user.user_id
        purchased = supabase.table('purchased').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()

        # 결과 재구성
        purchased_list = []
        for purchase in purchased.data:
            purchased_list.append({
                'order_id': purchase['order_id'],
                'item_id': purchase['item_id'],
                'payment_method': purchase['payment_method'],
                'total_price': purchase['total_price'],
            })

        return Response(purchased_list)
    except:
        return Response({'error': '구매 내역 조회 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def prepare_purchase(request):
    try:
        data = json.loads(request.body)
        user_id = request.user.user_id
        item_ids = data.get('item_ids')

        if not isinstance(item_ids, list):
            return Response({'error': '유효하지 않은 요청 본문'}, status=status.HTTP_400_BAD_REQUEST)

        total_price = 0
        item_names = []
        item_codes = []

        # 상품 정보 조회, total_price 계산
        for item_id in item_ids:
            item = fetch_item_details(item_id)
            if not item['onSale']:
                return Response({'error': f'상품 {item["item_id"]}는 판매 중이 아닙니다'}, status=status.HTTP_400_BAD_REQUEST)
            total_price += item['price']
            item_names.append(item['title'])
            item_codes.append(str(item['num_code']))

        item_name = ', '.join(item_names[:3])
        if len(item_names) > 3:
            item_name += f' 외 {len(item_names) - 3}건'

        order_id = f"{user_id}_{int(time.time())}"

        payment_response = requests.post(
            'https://open-api.kakaopay.com/online/v1/payment/ready',
            headers={
                'Authorization': f"SECRET_KEY {settings.KAKAO_API_KEY}",
                'Content-Type': 'application/json',
            },
            json={
                'cid': settings.KAKAO_CID,
                'partner_order_id': order_id,
                'partner_user_id': user_id,
                'item_name': item_name,
                'item_code': ','.join(item_codes),
                'quantity': len(item_ids),
                'total_amount': total_price,
                'tax_free_amount': 0,
                'approval_url': f"{settings.FRONT_URL}/purchaseApprove?oid={order_id}",
                'fail_url': f"{settings.FRONT_URL}/purchaseFail",
                'cancel_url': f"{settings.FRONT_URL}/purchaseFail",
            }
        )

        payment_result = payment_response.json()
        return Response(payment_result)

    except:
        return Response({'error': f'결제 준비 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def approve_purchase(request):
    try:
        data = json.loads(request.body)
        oid = data.get('oid')
        tid = data.get('tid')
        user_id = request.user.user_id
        pg_token = data.get('pg_token')

        if not all([oid, tid, pg_token]):
            return Response({'error': '유효하지 않은 요청 본문'}, status=status.HTTP_400_BAD_REQUEST)

        approval_response = requests.post(
            'https://open-api.kakaopay.com/online/v1/payment/approve',
            headers={
                'Authorization': f"SECRET_KEY {settings.KAKAO_API_KEY}",
                'Content-Type': 'application/json',
            },
            json={
                'cid': settings.KAKAO_CID,
                'tid': tid,
                'partner_order_id': oid,
                'partner_user_id': user_id,
                'pg_token': pg_token
            }
        )

        approval_result = approval_response.json()

        product_codes = approval_result['item_code'].split(',')
        for num_code in product_codes:
            item = update_item_by_code(num_code)
            if item:
                insert_purchase(item, user_id, approval_result['payment_method_type'],
                                oid, approval_result.get('card_info'),
                                approval_result['amount']['total'], item['price'])
                delete_cart_item(item['item_id'], user_id)

        return Response(approval_result)

    except:
        return Response({'error': f'결제 승인 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def fetch_item_details(item_id):
    result = supabase.table('items').select('*').eq('item_id', item_id).execute()
    if result.data:
        return result.data[0]
    raise Exception(f'상품 {item_id}를 찾을 수 없습니다')

def update_item_by_code(code):
    result = supabase.table('items').update({'onSale': False}).eq('num_code', int(code)).execute()
    return result.data[0] if result.data else None

def insert_purchase(item, user_id, pay_type, order_id, card_info, total_price, single_price):
    supabase.table('purchased').insert({
        'user_id': user_id,
        'item_id': item['item_id'],
        'title': item['title'],
        'artist': item['artist'],
        'descriptions': item['descriptions'],
        'imagePath': item['imagePath'],
        'payment_method': pay_type,
        'order_id': order_id,
        'card_info': card_info,
        'total_price': int(total_price),
        'price': int(single_price),
        'refund': False,
        'created_at': timezone.now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    }).execute()

def delete_cart_item(item_id, user_id):
    supabase.table('cart_item').delete().match({'item_id': item_id, 'user_id': user_id}).execute()
