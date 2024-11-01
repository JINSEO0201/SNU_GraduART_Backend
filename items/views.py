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
def get_items(request, department):
  #해당 단과대 작품들 정보 전달
  return 0

@api_view(['GET'])
def get_item_details(request, item_id):
  #item_id를 받아 상세 정보 및 사진 제공
  return 0

@api_view(['GET'])
def search_items(request):
  #해당 문자가 들어간 작품 & 작가명 모두 제공
  return 0


@api_view(['GET'])
def get_representative_items(request):
  #과별로 메인페이지에 띄울 대표 아이템들 제공
  return 0