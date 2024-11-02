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
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


@api_view(['GET'])
def get_items(request, department):
  #해당 단과대 작품들 정보 전달
  try:
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

    item_detail.data['imagePath'] = item_images.data[0]
    return Response(item_detail.data, status=status.HTTP_200_OK)
  except:
    return Response({'error': f'작품 상세정보 불러오기 실패'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def search_items(request):
  #해당 문자가 들어간 작품 & 작가명 모두 제공
  
  return 0


# 프론트 static파일로 제공
# @api_view(['GET'])
# def get_representative_items(request):
#   #과별로 메인페이지에 띄울 대표 작품들 제공

#   return 0