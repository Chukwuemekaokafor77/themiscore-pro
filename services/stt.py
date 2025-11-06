import os
import requests
from typing import Dict, Any, Optional, Generator

ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
ASSEMBLYAI_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIPTION_URL = "https://api.assemblyai.com/v2/transcript"

class STTProvider:
    """Interface for STT providers"""
    def upload_and_transcribe(self, file_path: str) -> str:
        raise NotImplementedError

    def get_status(self, external_id: str) -> Dict[str, Any]:
        raise NotImplementedError

class AssemblyAIProvider(STTProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ASSEMBLYAI_API_KEY
        if not self.api_key:
            raise ValueError("ASSEMBLYAI_API_KEY is not set")
        self.headers_json = {
            'authorization': self.api_key,
            'content-type': 'application/json'
        }
        self.headers_upload = {
            'authorization': self.api_key
        }

    def _read_file(self, file_path: str, chunk_size: int = 5 * 1024 * 1024) -> Generator[bytes, None, None]:
        with open(file_path, 'rb') as _file:
            while True:
                data = _file.read(chunk_size)
                if not data:
                    break
                yield data

    def upload_and_transcribe(self, file_path: str) -> str:
        # upload
        up = requests.post(ASSEMBLYAI_UPLOAD_URL, headers=self.headers_upload, data=self._read_file(file_path))
        up.raise_for_status()
        upload_url = up.json()['upload_url']
        # request transcript
        payload = {
            'audio_url': upload_url,
            'speaker_labels': True,
            'sentiment_analysis': True,
            'entity_detection': True,
            'iab_categories': True,
            'auto_highlights': True
        }
        tr = requests.post(ASSEMBLYAI_TRANSCRIPTION_URL, json=payload, headers=self.headers_json)
        tr.raise_for_status()
        return tr.json()['id']

    def get_status(self, external_id: str) -> Dict[str, Any]:
        r = requests.get(f"{ASSEMBLYAI_TRANSCRIPTION_URL}/{external_id}", headers=self.headers_json)
        r.raise_for_status()
        data = r.json()
        resp = {
            'status': data.get('status'),
            'id': data.get('id'),
            'text': data.get('text', '') if data.get('status') == 'completed' else None,
            'entities': data.get('entities'),
            'sentiment_analysis': data.get('sentiment_analysis_results') or data.get('sentiment_analysis'),
            'auto_highlights': data.get('auto_highlights_result'),
            'iab_categories': data.get('iab_categories_result'),
        }
        if data.get('status') == 'error':
            resp['error'] = data.get('error')
        return resp

class STTService:
    """Factory to get the configured STT provider"""
    def __init__(self, provider_name: Optional[str] = None):
        name = (provider_name or os.getenv('STT_PROVIDER') or 'assemblyai').lower()
        if name == 'assemblyai':
            self.provider = AssemblyAIProvider()
        else:
            raise ValueError(f"Unsupported STT provider: {name}")

    def start_transcription(self, file_path: str) -> str:
        return self.provider.upload_and_transcribe(file_path)

    def get_transcription_status(self, external_id: str) -> Dict[str, Any]:
        return self.provider.get_status(external_id)
