from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from supabase import create_client, Client
from django.utils import timezone

# Supabase 클라이언트 설정
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@api_view(['POST'])
def insert_cart(request):
    try:
        # 사용자 정보와 상품 정보 가져오기
        user_id = request.user.user_id
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
            'created_at': timezone.localtime().isoformat(timespec='milliseconds') + '+09:00'
        }
        result = supabase.table('cart_item').insert(cart_item).execute()
        
        if result.data:
            return Response({'message': '장바구니에 추가되었습니다.'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': '장바구니 추가에 실패했습니다.'}, status=status.HTTP_400_BAD_REQUEST)
    except:
        return Response({'error': '장바구니 추가 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_cart_items(request):
    try:
        # 사용자 ID로 장바구니 조회
        user_id = request.user.user_id
        result = supabase.table('cart_item').select('item_id').eq('user_id', user_id).order('created_at', desc=True).execute()

        # 장바구니에 담긴 상품 정보 가져오기
        items_ids = [item['item_id'] for item in result.data]
        items = supabase.table('items').select("*").in_('item_id', items_ids).execute()

        # image 정보 가져오기
        item_images = supabase.table('item_images').select("*").in_('id', items_ids).execute()
        images_dict = {img['id']: img for img in item_images.data}

        # artist 정보 가져오기
        artists = supabase.table('artists').select("*").execute()
        artists_dict = {artist['id']: artist for artist in artists.data}

        # 결과 재구성
        items_data = []
        for item in items.data:
            items_data.append({
                'item_id': item['item_id'],
                'title': item['title'],
                'name': artists_dict[item['artist_id']]['name'] if item['artist_id'] in artists_dict else None,
                'description': item['description'],
                'image_original': images_dict[item['item_id']]['image_original'] if item['item_id'] in images_dict else None,
                'image_square': images_dict[item['item_id']]['image_square'] if item['item_id'] in images_dict else None,
                'price': item['price'],
                'onSale': item['onSale'],
                'department': item['department'],
            })
        
        return Response(items_data, status=status.HTTP_200_OK)
    except:
        return Response({'error': '장바구니 조회 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
def delete_cart_item(request, item_id):
    try:
        user_id = request.user.user_id
        item_id = str(item_id)
        result = supabase.table('cart_item').delete().eq('user_id', user_id).eq('item_id', item_id).execute()
        
        if result.data:
            return Response({'message': '장바구니에서 삭제되었습니다.'}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({'error': '장바구니에 해당 상품이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    except:
        return Response({'error': '장바구니 삭제 중 오류 발생'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
