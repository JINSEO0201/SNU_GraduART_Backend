from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
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
def get_items(request):
  #해당 단과대 작품들 정보 전달
  try:
    department = request.GET.get('department')
    items = supabase.table('items').select('*').eq('department', department).execute()
    for item in items.data:
      id = item['itemID']
      images = supabase.table('item_images').select('image_square, image_original').eq('id', id).execute

      #정사각 이미지가 있을 경우에만 정사각 이미지 제공
      if images.data[0]['image_square']:
        item['imagePath'] = images.data[0]['image_square']
      else:
        item['imagePath'] = images.data[0]['image_original']

    return Response(items.data, status=status.HTTP_200_OK)
  except:
    return Response({'error': f'작품 정보 불러오기 실패'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_item_details(request, item_id):
  try:
  #item_id를 받아 상세 정보 및 사진 제공
    item_detail = supabase.table('items').select("*").eq('id', item_id).execute()
    item_images = supabase.table('item_images').select("*").eq('id', item_id).execute()
    item_artist = supabase.table('artists').select("*").eq('id', id).execute()

    item_detail.data['imagePath'] = item_images.data[0]
    item_detail.data['artistInfo'] = item_artist.data[0]
    return Response(item_detail.data, status=status.HTTP_200_OK)
  except:
    return Response({'error': f'작품 상세정보 불러오기 실패'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def search_items(request):
  #해당 문자가 들어간 작품 & 작가명 모두 제공
  try:
    query = request.GET.get("query", "")
    result = {}
    unique_ids = []
    #1. 작품명으로 검색
    items_searched_title = supabase.table("items").select("*").ilike("title", f"%{query}%").execute()
    items_searched_title_data = items_searched_title.data

    #각 작품 정보에 이미지 추가하기
    for item in items_searched_title_data:
      id = item["id"]
      images = supabase.table("images").select("image_original", "image_square").eq("itemID", id).execute()
      if images.data[0]["image_square"]:
        item["imagePath"] = images.data[0]["image_square"]
      else:
        item["imagePath"] = images.data[0]["image_original"]
      unique_ids.append(id) #중복 방지


    #2. 작가명으로 검색
    items_searched_artist = supabase.table("items").select("*").ilike("artist", f"%{query}%").execute()
    items_searched_artist_data = items_searched_artist.data

    #각 작품 정보에 이미지 추가하기
    for item in items_searched_artist_data:
      id = item["id"]
      #앞서 검색되었던 작품들 제외하고
      if id not in unique_ids:
        images = supabase.table("images").select("image_original", "image_square").eq("itemID", id).execute()
        if images.data[0]["image_square"]:
          item["imagePath"] = images.data[0]["image_square"]
        else:
          item["imagePath"] = images.data[0]["image_original"]


    result["items"] = list(items_searched_title_data)
    result["items"] += list(items_searched_artist_data)
    return Response(result, status=status.HTTP_200_OK)
  except:
    return Response({'error': f'작품 검색 실패'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 과별 대표 작품들은 프론트 static파일로 제공
# @api_view(['GET'])
# def get_representative_items(request):
#   #과별로 메인페이지에 띄울 대표 작품들 제공

#   return 0