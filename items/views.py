from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from supabase import create_client, Client
from django.conf import settings

# Supabase 클라이언트 설정
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

DEPARTMENT_LIST = ['Design', 'MediaArts', 'Sculpture', 'Craft', 'Oriental Painting', 'Western Painting']

@api_view(['GET'])
@permission_classes([AllowAny])
def get_items(request):
  try:
    department = request.GET.get('department')
    # query parameter로 학과 정보를 전달해주지 않았다면
    if not department:
      return Response({'error': f'학과 정보가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
    # 대소문자 구분 없이 학과 정보를 받아올 수 있도록
    dept = next((d for d in DEPARTMENT_LIST if d.lower() == department.lower()), None)
    if not dept:
      return Response({'error': f'학과 정보가 잘못되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # db 한 번 접근에서 전부 가져옴 (오버헤드 줄임)
    items = supabase.table('items').select('*').eq('department', dept).execute()
    item_images = supabase.table('item_images').select('*').execute()
    artists = supabase.table('artists').select('*').execute()

    # 빠른 검색을 위한 딕셔너리 생성
    images_dict = {img['id']: img for img in item_images.data}
    artists_dict = {artist['id']: artist for artist in artists.data}

    # 결과 재구성
    item_results = []
    for item in items.data:
      item_data = {
        'item_id': item['item_id'],
        'title': item['title'],
        'artist_name': artists_dict[item['artist_id']]['name'] if item['artist_id'] in artists_dict else None,
        'size': item['size'],
        'material': item['material'],
        'image_original': images_dict[item['item_id']]['image_original'] if item['item_id'] in images_dict else None,
        'image_square': images_dict[item['item_id']]['image_square'] if item['item_id'] in images_dict else None,
      }
      item_results.append(item_data)

    return Response(item_results, status=status.HTTP_200_OK)
  except:
    return Response({'error': f'작품 정보 불러오기 실패'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_item_details(request, item_id):
  try:
    # UUID 형식의 item_id를 문자열로 변환
    item_id = str(item_id)

    # 작품 정보 조회
    item_detail = supabase.table('items').select("*").eq('item_id', item_id).execute()
    if not item_detail.data:
      return Response({'error': f'해당 작품이 존재하지 않습니다.'}, status=status.HTTP_404_NOT_FOUND)

    # 작품 이미지 및 작가 정보 조회 (foreign key로 연결 = 반드시 대응되는 정보가 있어야 함)
    id = item_detail.data[0]['artist_id']
    item_image = supabase.table('item_images').select("*").eq('id', item_id).execute()
    item_artist = supabase.table('artists').select("*").eq('id', id).execute()

    # 결과 재구성 (뺄 것들 빼고 추가할 것들 추가)
    item_result = {k: v for k, v in item_detail.data[0].items() if k not in ['created_at', 'artist_id']}
    # 작가 정보 추가 
    item_result.update({k: v for k, v in item_artist.data[0].items() if k not in ['created_at', 'id']})
    # 이미지 정보 추가
    item_result.update({k: v for k, v in item_image.data[0].items() if k not in ['created_at', 'id']})

    return Response(item_result, status=status.HTTP_200_OK)
  except:
    return Response({'error': f'작품 상세정보 불러오기 실패'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_items(request):
  #해당 문자가 들어간 작품 & 작가명 모두 제공
  try:
    query = request.GET.get("query", "")
    if not query:
      return Response([], status=status.HTTP_200_OK)

    # 작품명으로 검색
    search_result = supabase.table("items").select("*").ilike("title", f"%{query}%").execute()
    item_ids = [item['item_id'] for item in search_result.data]
    search_result = [] if not search_result.data else search_result.data

    # 작가명으로 검색
    artist_search = supabase.table("artists").select("id").ilike("name", f"%{query}%").execute()
    artist_ids = [artist['id'] for artist in artist_search.data]
    
    # 작가 id로 검색된 작품들 가져오기
    items_searched_by_artist = supabase.table("items").select("*").in_("artist_id", artist_ids).execute()
    for item in items_searched_by_artist.data:
      if item['item_id'] not in item_ids:
        search_result.append(item)
    
    # 이미지 및 작가 정보 가져오기
    item_images = supabase.table('item_images').select('*').execute()
    artists = supabase.table('artists').select('*').execute()
    images_dict = {img['id']: img for img in item_images.data}
    artists_dict = {artist['id']: artist for artist in artists.data}

    # 결과 재구성
    final_result = []
    for result in search_result:
      result_data = {
        'item_id': result['item_id'],
        'department': result['department'],
        'title': result['title'],
        'description': result['description'],
        'artist_name': artists_dict[result['artist_id']]['name'] if result['artist_id'] in artists_dict else None,
        'size': result['size'],
        'material': result['material'],
        'image_original': images_dict[result['item_id']]['image_original'] if result['item_id'] in images_dict else None,
        'image_square': images_dict[result['item_id']]['image_square'] if result['item_id'] in images_dict else None,
      }
      final_result.append(result_data)

    return Response(final_result, status=status.HTTP_200_OK)
  except:
    return Response({'error': f'작품 검색 실패'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
