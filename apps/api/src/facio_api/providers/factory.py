from facio_api.config import Settings, UnknownModelError, provider_family
from facio_api.providers.anthropic import AnthropicProvider
from facio_api.providers.openai import OpenAIProvider
from facio_api.providers.scripted import ScriptedProvider
from facio_api.providers.types import LiveProviderError, ModelProvider


def provider_for(settings: Settings, utterance: str) -> ModelProvider:
    if settings.talk_mode != "live":
        return ScriptedProvider.for_utterance(utterance)
    try:
        family = provider_family(settings.model_name)
    except UnknownModelError as error:
        raise LiveProviderError(str(error)) from error
    key = settings.key_for(family)
    if not key:
        raise LiveProviderError(f"{family} key missing")
    if family == "anthropic":
        return AnthropicProvider(settings)
    return OpenAIProvider(settings)
