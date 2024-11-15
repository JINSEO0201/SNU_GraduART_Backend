from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import requests
from supabase import create_client, Client
import time
from django.utils import timezone
from datetime import datetime, timedelta
from django.conf import settings

# Supabase 클라이언트 설정
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
PAYREADY_URL = 'https://open-api.kakaopay.com/online/v1/payment/ready'
PAYAPPROVE_URL = 'https://open-api.kakaopay.com/online/v1/payment/approve'

@api_view(['GET'])
def get_purchases(request):
    try:
        # 사용자 ID로 구매 내역 조회
        user_id = request.user.user_id
        purchased = supabase.table('purchased').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()

        if not purchased.data:
            return Response([], status=status.HTTP_200_OK)

        # 구매한 상품 정보 조회
        item_ids = [purchase['item_id'] for purchase in purchased.data]
        items = supabase.table('items').select('*').in_('item_id', item_ids).execute()
        item_dict = {item['item_id']: item for item in items.data}
        
        item_images = supabase.table('item_images').select('id, image_original').in_('id', item_ids).execute()
        item_images_dict = {image['id']: image['image_original'] for image in item_images.data}

        authors = supabase.table('artists').select('id, name').execute()
        authors_dict = {author['id']: author['name'] for author in authors.data}

        # 결제 2주 이후 구매확정
        try:
            two_weeks = timedelta(days=14)
            now = timezone.now()

            for record in purchased.data:
                created_at_datetime = datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
                if now - created_at_datetime >= two_weeks:
                    item_id = record["item_id"]
                    record["is_confirmed"] = True
                    response = supabase.table("purchased").update({"is_confirmed" : True}).eq("item_id", item_id).execute()
        except:
            pass

        # 결과 재구성 (마이페이지에 들어갈 내용들)
        purchased_list = []
        for purchase in purchased.data:
            item = item_dict.get(purchase['item_id'])
            if not item:
                continue

            purchased_list.append({
                'item_id': item['item_id'],
                'image_original': item_images_dict.get(item['item_id']),
                'title': item['title'],
                'name': authors_dict.get(item['artist_id']),
                'size': item['size'],
                'material': item['material'],
                'price': item['price'],
                'refund': purchase['refund'],
                'is_confirmed': purchase['is_confirmed'],
            })

        return Response(purchased_list, status=status.HTTP_200_OK)
    except:
        return Response({'error': '구매 내역 조회 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def get_purchase_detail(request, item_id):
    try:
        # 사용자 ID + item_id로 주문/결제 상세 정보 조회
        user_id = request.user.user_id
        item_id = str(item_id)

        purchase = supabase.table('purchased').select('order_id').eq('user_id', user_id).eq('item_id', item_id).execute()

        if not purchase.data:
            return Response({'error': '구매 내역을 찾을 수 없습니다'}, status=status.HTTP_404_NOT_FOUND)
        
        # 추가적인 주문 정보 리턴
        order_id = purchase.data[0]['order_id']
        order_info = supabase.table('order_info').select('address', 'name', 'phone_num', 'email', 'payment_method', 'total_price').eq('order_id', order_id).execute()

        # 결과 재구성
        order_info = order_info.data[0] if order_info.data else {}
        return Response(order_info, status=status.HTTP_200_OK)
    except:
        return Response({'error': '구매 내역 조회 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def prepare_purchase(request):
    try:
        user_id = request.user.user_id
        item_ids = request.data.get('item_ids')

        if not isinstance(item_ids, list):
            return Response({'error': '유효하지 않은 요청 본문'}, status=status.HTTP_400_BAD_REQUEST)

        total_price = 0
        item_names = []

        # 상품 정보 조회, total_price 계산
        for item_id in item_ids:
            item = supabase.table('items').select('*').eq('item_id', item_id).execute()
            if not item.data:
                return Response({'error': f'상품 {item_id}를 찾을 수 없습니다'}, status=status.HTTP_400_BAD_REQUEST)

            item = item.data[0]
            if not item['onSale']:
                return Response({'error': f"상품 <{item['title']}>는 판매 중이 아닙니다"}, status=status.HTTP_400_BAD_REQUEST)
            
            total_price += item['price']
            item_names.append(item['title'])

        item_name = ', '.join(item_names[:3])
        if len(item_names) > 3:
            item_name += f' 외 {len(item_names) - 3}건'

        order_id = f"{user_id}_{int(time.time())}"

        payment_response = requests.post(
            PAYREADY_URL,
            headers={
                'Authorization': f"SECRET_KEY {settings.KAKAO_API_KEY}",
                'Content-Type': 'application/json',
            },
            json={
                'cid': settings.KAKAO_CID,
                'partner_order_id': order_id,
                'partner_user_id': user_id,
                'item_name': item_name,
                'item_code': ','.join(item_ids),
                'quantity': len(item_ids),
                'total_amount': total_price,
                'tax_free_amount': 0,
                'approval_url': f"{settings.FRONT_URL}/purchaseApprove?oid={order_id}",
                'fail_url': f"{settings.FRONT_URL}/purchaseFail",
                'cancel_url': f"{settings.FRONT_URL}/purchaseFail",
            }
        )
        if payment_response.status_code != 200:
            return Response({'error': f'결제 준비 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payment_result = payment_response.json()

        # 결제 관련 정보를 db에 일시적으로 저장 (데이터 신뢰성 확보, 추후 approval 시 검증 용도)
        supabase.table('payment_temporary_data').insert({
            'order_id': order_id,
            'user_id': user_id,
            'tid': payment_result['tid'],
        }).execute()
        
        return Response(payment_result)

    except:
        return Response({'error': f'결제 준비 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def approve_purchase(request):
    try:
        # 결제 관련 정보 가져오기
        oid = request.data.get('oid')
        pg_token = request.data.get('pg_token')
        
        # 사용자 정보 가져오기
        user_id = request.user.user_id
        address = request.data.get('address')
        name = request.data.get('name')
        phone_num = request.data.get('phone_num')
        email = request.data.get('email')

        if not all([oid, pg_token]):
            return Response({'error': '유효하지 않은 요청 본문'}, status=status.HTTP_400_BAD_REQUEST)
        
        # tid 값 가져오기 (데이터 신뢰성을 위해 client로부터 받지 않고 db에서 가져옴)
        payment_temporary_data = supabase.table('payment_temporary_data').select('*').eq('order_id', oid).eq('user_id', user_id).execute()
        if not payment_temporary_data.data:
            return Response({'error': '유효하지 않은 결제 정보'}, status=status.HTTP_400_BAD_REQUEST)
        tid = payment_temporary_data.data[0]['tid']

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

        # order_info table에 데이터 추가
        supabase.table('order_info').insert({
            'order_id': oid,
            'transaction_id': tid,
            'address': address,
            'name': name,
            'phone_num': phone_num,
            'email': email,
            'payment_method': approval_result['payment_method_type'],
            'total_price': approval_result['amount']['total'],
            'card_info': approval_result.get('card_info'),
        }).execute()

        for item_id in product_codes:
            # item's onSale status를 false로 변경
            result = supabase.table('items').update({'onSale': False}).eq('item_id', item_id).execute()
            if not result.data:
                return Response({'error: 상품 정보 업데이트 실패'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # purchased table에 데이터 추가
            supabase.table('purchased').insert({
                'order_id': oid,
                'user_id': user_id,
                'item_id': item_id,
                'created_at': timezone.now().isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                'refund': False,
                'is_confirmed': False,
            }).execute()

            # 장바구니에서 삭제
            supabase.table('cart_item').delete().match({'item_id': item_id, 'user_id': user_id}).execute()

        # 결제 관련 임시 정보 삭제
        supabase.table('payment_temporary_data').delete().eq('order_id', oid).eq('user_id', user_id).execute()

        return Response({'message': '결제가 성공적으로 완료되었습니다'}, status=status.HTTP_200_OK)

    except:
        return Response({'error': f'결제 승인 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
