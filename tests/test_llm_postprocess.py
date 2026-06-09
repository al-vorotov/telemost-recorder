from services.gateway.services.llm_postprocess import LlmPostProcessor
from shared.config.settings import Settings


def test_llm_disabled_without_key() -> None:
    p = LlmPostProcessor(Settings(llm_api_key=""))
    assert p.enabled is False


def test_llm_enabled_with_key() -> None:
    p = LlmPostProcessor(Settings(llm_api_key="sk-test"))
    assert p.enabled is True
