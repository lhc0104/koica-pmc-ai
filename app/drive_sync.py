"""
Google Drive 동기화 모듈
- CSV 파일을 Google Drive에서 다운로드/업로드
- SQLite 캐시와 자동 동기화
"""

import io
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import pandas as pd
from pathlib import Path


class GoogleDriveSync:
    """Google Drive와 로컬 CSV 파일 동기화"""
    
    def __init__(self, service_account_info: dict, drive_folder_id: str):
        """
        Args:
            service_account_info: Google 서비스 계정 JSON 정보
            drive_folder_id: Google Drive 폴더 ID
        """
        self.creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        self.service = build('drive', 'v3', credentials=self.creds)
        self.folder_id = drive_folder_id
    
    def download_csv(self, filename: str) -> pd.DataFrame:
        """
        Google Drive에서 CSV 파일 다운로드
        
        Args:
            filename: 다운로드할 파일명 (예: 'performance.csv')
            
        Returns:
            pandas DataFrame
        """
        try:
            # Drive에서 파일 찾기
            results = self.service.files().list(
                q=f"'{self.folder_id}' in parents and name='{filename}' and trashed=false",
                spaces='drive',
                fields='files(id, name)',
                pageSize=1
            ).execute()
            
            files = results.get('files', [])
            if not files:
                raise FileNotFoundError(f"Google Drive에서 '{filename}' 파일을 찾을 수 없습니다")
            
            file_id = files[0]['id']
            
            # 파일 다운로드
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO(request.execute()).getvalue()
            
            # CSV로 변환
            df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
            print(f"✓ Google Drive에서 '{filename}' 다운로드 완료 ({len(df)} 행)")
            return df
            
        except Exception as e:
            print(f"❌ 다운로드 실패: {e}")
            raise
    
    def upload_csv(self, df: pd.DataFrame, filename: str) -> bool:
        """
        Google Drive에 CSV 파일 업로드 (기존 파일 덮어쓰기)
        
        Args:
            df: 업로드할 DataFrame
            filename: 파일명
            
        Returns:
            성공 여부
        """
        try:
            # CSV 버퍼로 변환
            csv_buffer = io.BytesIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_buffer.seek(0)
            
            # Drive에서 기존 파일 찾기
            results = self.service.files().list(
                q=f"'{self.folder_id}' in parents and name='{filename}' and trashed=false",
                spaces='drive',
                fields='files(id)',
                pageSize=1
            ).execute()
            
            file_media = MediaIoBaseUpload(csv_buffer, mimetype='text/csv', resumable=True)
            
            if results['files']:
                # 기존 파일 업데이트
                file_id = results['files'][0]['id']
                self.service.files().update(
                    fileId=file_id,
                    media_body=file_media
                ).execute()
                print(f"✓ Google Drive에 '{filename}' 업로드 완료 (기존 파일 덮어쓰기)")
            else:
                # 새 파일 생성
                file_metadata = {
                    'name': filename,
                    'parents': [self.folder_id]
                }
                self.service.files().create(
                    body=file_metadata,
                    media_body=file_media
                ).execute()
                print(f"✓ Google Drive에 '{filename}' 업로드 완료 (새 파일 생성)")
            
            return True
            
        except Exception as e:
            print(f"❌ 업로드 실패: {e}")
            raise
    
    def sync_csv_to_drive(self, local_path: str, drive_filename: str) -> bool:
        """
        로컬 CSV 파일을 Google Drive에 동기화
        
        Args:
            local_path: 로컬 CSV 파일 경로
            drive_filename: Drive에 저장할 파일명
            
        Returns:
            성공 여부
        """
        try:
            df = pd.read_csv(local_path)
            self.upload_csv(df, drive_filename)
            return True
        except Exception as e:
            print(f"❌ 로컬 → Drive 동기화 실패: {e}")
            raise


def get_drive_sync(service_account_json_path: str = None, folder_id: str = None) -> GoogleDriveSync:
    """
    Google Drive 동기화 객체 생성
    
    환경변수에서 읽기:
    - GOOGLE_SERVICE_ACCOUNT_JSON: 서비스 계정 JSON 파일 경로 (또는 JSON 문자열)
    - GOOGLE_DRIVE_FOLDER_ID: Google Drive 폴더 ID
    """
    # 환경변수 또는 매개변수에서 읽기
    json_path = service_account_json_path or os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    folder = folder_id or os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    
    # JSON 파일에서 읽기
    if json_path and os.path.isfile(json_path):
        with open(json_path, 'r') as f:
            service_account_info = json.load(f)
    else:
        # 환경변수에서 직접 JSON 읽기
        service_account_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
    
    if not service_account_info or not folder:
        raise ValueError(
            "Google Drive 설정이 없습니다. 다음 환경변수를 확인하세요:\n"
            "- GOOGLE_SERVICE_ACCOUNT_JSON\n"
            "- GOOGLE_DRIVE_FOLDER_ID"
        )
    
    return GoogleDriveSync(service_account_info, folder)
