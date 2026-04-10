from agent_registry.signature.agent_card_validator import AgentCardValidator
from agent_registry.signature.public_key_manager import PublicKeyManager
from agent_registry.signature.jwk_fetcher import JWKFetcher


def get_agent_card_validator() -> AgentCardValidator:
    """获取AgentCard验证器单例"""
    from functools import lru_cache
    
    @lru_cache(maxsize=1)
    def _get_validator() -> AgentCardValidator:
        public_key_manager = PublicKeyManager()
        jwk_fetcher = JWKFetcher()
        return AgentCardValidator(public_key_manager, jwk_fetcher)
    
    return _get_validator()