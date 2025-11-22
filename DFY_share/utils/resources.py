# utils/resources.py

import os
import sys


def resource_path(relative_path: str) -> str:
    """
    개발 환경에서는 프로젝트 루트를 기준으로,
    PyInstaller exe 환경에서는 _MEIPASS(임시 폴더)를 기준으로
    리소스 파일 경로를 안전하게 반환한다.
    """
    # PyInstaller로 빌드된 exe 안에서 실행될 때
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        # 개발 중일 때: utils/ 기준으로 한 단계 올라가면 프로젝트 루트
        base_path = os.path.dirname(os.path.abspath(__file__))  # .../utils
        base_path = os.path.dirname(base_path)                  # 프로젝트 루트

    return os.path.join(base_path, relative_path)
