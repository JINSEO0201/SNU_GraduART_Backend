from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from supabase import create_client, Client
from django.utils import timezone

# Supabase 클라이언트 설정
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def insert_cart(request):
    try:
        # 사용자 정보와 상품 정보 가져오기
        user_id = request.user['user_id']
        item_id = request.data.get('item_id')

        # 이미 장바구니에 있는지 확인
        cart_items = supabase.table('cart_item').select('item_id').eq('user_id', user_id).eq('item_id', item_id).execute()
        if cart_items.data:
            return Response({'error': '이미 장바구니에 있는 상품입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # onSale 상태인지 확인
        item = supabase.table('items').select('*').eq('item_id', item_id).execute()
        if not item.data or not item.data[0]['onSale']:
            return Response({'error': '판매 중인 상품이 아닙니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 장바구니에 추가
        cart_item = {
            'user_id': user_id,
            'item_id': item_id,
            'created_at': timezone.now().isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        }
        result = supabase.table('cart_item').insert(cart_item).execute()
        
        if result.data:
            return Response({'message': '장바구니에 추가되었습니다.'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': '장바구니 추가에 실패했습니다.'}, status=status.HTTP_400_BAD_REQUEST)
    except:
        return Response({'error': '장바구니 추가 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_cart_items(request):
    try:
        # 사용자 ID로 장바구니 조회
        user_id = request.user['user_id']
        result = supabase.table('cart_item').select('item_id').eq('user_id', user_id).order('created_at', desc=True).execute()

        # item_id를 가지고 items 테이블에서 item 정보를 가져와서 리턴하기
        items_id = [item['item_id'] for item in result.data]
        items = supabase.table('items').select('*').eq('item_id', items_id).execute()
        
        return Response(items.data)
    except:
        return Response({'error': '장바구니 조회 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_cart_item(request, item_id):
    try:
        user_id = request.user['user_id']
        result = supabase.table('cart_item').delete().eq('user_id', user_id).eq('item_id', item_id).execute()
        
        if result.data:
            return Response({'message': '장바구니에서 삭제되었습니다.'}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({'error': '장바구니에 해당 상품이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except:
        return Response({'error': '장바구니 삭제 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
