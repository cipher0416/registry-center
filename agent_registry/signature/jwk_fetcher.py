import json
import requests
from typing import Optional
from loguru import logger

from agent_registry.signature.models import JWK, JWKS


class JWKFetcher:
    """JWK获取器"""
    
    REQUEST_TIMEOUT = 10  # 10秒超时
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = self.REQUEST_TIMEOUT
    
    def fetch_jwks(self, jku: str) -> Optional[JWKS]:
        """
        从URL获取JWKS
        
        Args:
            jku: JWK Set URL
        
        Returns:
            Optional[JWKS]: JWKS对象，失败返回None
        """
        try:
            logger.info(f"Fetching JWKS from: {jku}")
            
            # 验证URL使用HTTPS
            if not jku.startswith('https://'):
                logger.error(f"JKU must use HTTPS: {jku}")
                return None
            
            response = self.session.get(jku)
            if response.status_code != 200:
                logger.error(f"Failed to fetch JWKS, status: {response.status_code}")
                return None
            
            jwks_data = response.json()
            return JWKS(**jwks_data)
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching JWKS from: {jku}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching JWKS: {e}")
            return None
        except Exception as e:
            logger.error(f"Error while fetching JWKS: {e}")
            return None
    
    def find_key_by_id(self, jwks: JWKS, kid: str) -> Optional[JWK]:
        """
        根据kid从JWKS中查找公钥
        
        Args:
            jwks: JWKS对象
            kid: 密钥ID
        
        Returns:
            Optional[JWK]: JWK对象，不存在返回None
        """
        try:
            for key in jwks.keys:
                if key.kid == kid:
                    logger.info(f"Found key by kid: {kid}")
                    return key
            
            logger.warning(f"Key not found in JWKS: {kid}")
            return None
        except Exception as e:
            logger.error(f"Error while finding key: {e}")
            return None