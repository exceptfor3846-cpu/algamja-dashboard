"""
Gunicorn 설정 파일 - Railway 배포용
PORT 환경변수를 Python에서 직접 읽어 안정적으로 바인딩
"""
import os

bind    = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1
timeout = 120
accesslog = "-"   # stdout으로 액세스 로그 출력
errorlog  = "-"   # stdout으로 에러 로그 출력
loglevel  = "info"
