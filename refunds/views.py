from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from django.utils import timezone

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@api_view(['POST'])
def request_refund(request):
    user_id = request.user.user_id
    item_id = request.data.get('item_id')
    phone_number = request.data.get('phone_number')

    # Supabase에서 구매내역 조회
    purchased = supabase.table('purchased').select('*').eq('user_id', user_id).eq('item_id', item_id).execute()
    # Supabase에서 상품 정보 조회
    item = supabase.table('items').select('*').eq('item_id', item_id).execute()

    # 이메일 전송 포맷
    subject = "환불 요청"
    body = f"""
    사용자 ID: {user_id}
    상품 ID: {item_id}
    주문 날짜: {purchased.data[0]['created_at']}
    제목: {item.data[0]['title']}
    아티스트: {item.data[0]['artist']}
    설명: {item.data[0]['descriptions']}
    가격: {item.data[0]['price']}
    결제 방법: {purchased.data[0]['payment_method']}
    주문 ID: {purchased.data[0]['order_id']}
    총 가격: {purchased.data[0]['total_price']}
    전화번호: {phone_number}
    """

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = settings.EMAIL_HOST_USER
    msg['To'] = settings.ADMIN_EMAIL

    try:
        # 이메일을 보냄
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)

        # refund_request 테이블에 환불 요청 정보 저장
        # 왜 별도의 DB에 또 저장하냐 => 이 DB는 관리자가 환불 요청을 확인할 때 사용 (슬랙 알림 등 연결 가능)
        refund_info = {
            'user_id': user_id,
            'item_id': item_id,
            'created_at': timezone.now().isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
            'order_id': purchased.data[0]['order_id'],
        }
        result = supabase.table('refund_request').insert(refund_info).execute()

        return Response({'message': '환불 요청이 성공적으로 접수되었습니다.'}, status=status.HTTP_200_OK)
    except:
        return Response({'error': f'환불 요청 처리 중 오류가 발생했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def refund_status(request, item_id):
    try:
        user_id = request.user.user_id
        # Supabase에서 해당 item_id의 환불 상태 조회
        result = supabase.table('purchased').select('refund').eq('item_id', item_id).eq('user_id', user_id).execute()
        
        if result.data:
            refund_status = result.data[0]['refund']
            return Response({'refund_status': refund_status}, status=status.HTTP_200_OK)
        else:
            return Response({'error': '해당 항목을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except:
        return Response({'error': f'환불 상태 조회 중 오류가 발생했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
