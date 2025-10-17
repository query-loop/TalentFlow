from typing import Dict, Any, Optional
import importlib

# A small registry of recommended models for different agent tasks.
# Keys: task name, value: list of model ids (HF hub / GitHub repo paths) sorted by preference.
MODEL_REGISTRY: Dict[str, list] = {
    "embedder": [
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-MiniLM-L12-v2",
    ],
    "generator": [
        "google/flan-t5-small",
        "t5-small",
        # GitHub model (via Azure GitHub Inference endpoint)
        "deepseek/DeepSeek-R1-0528",
    ],
    "token-classifier": [
        "dbmdz/bert-large-cased-finetuned-conll03-english",
    ],
    "qa": [
        "deepset/roberta-base-squad2",
    ],
}


def list_models() -> Dict[str, list]:
    """Return the registry mapping task -> model ids."""
    return MODEL_REGISTRY


def _transformers_available() -> bool:
    return importlib.util.find_spec("transformers") is not None


def try_load_model(model_id: str, task: Optional[str] = None) -> Dict[str, Any]:
    """Attempt to load a model via transformers (if available).

    Returns a dict with status and message. Does not raise on import failures.
    """
    # Prefer transformers loader when available and the model is on HF
    if model_id and _transformers_available():
        try:
            from transformers import AutoModel, AutoTokenizer

            tok = AutoTokenizer.from_pretrained(model_id)
            mdl = AutoModel.from_pretrained(model_id)
            return {"status": "loaded", "via": "transformers", "model_id": model_id, "tokenizer_vocab_size": getattr(tok, "vocab_size", None)}
        except Exception as e:
            return {"status": "error", "via": "transformers", "message": str(e)}

    # If the model_id corresponds to a GitHub-hosted model that is exposed via
    # the GitHub inference endpoint (Azure-style wrapper), attempt a minimal
    # connectivity check if azure.ai.inference is installed and GITHUB_TOKEN is set.
    try:
        import os
        from importlib import util

        if model_id and model_id.lower().startswith("deepseek") or "deepseek" in model_id.lower():
            # Check for azure.ai.inference availability and GITHUB_TOKEN
            if util.find_spec("azure.ai.inference") is None:
                return {"status": "fallback", "via": "azure", "message": "azure.ai.inference not installed"}

            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                return {"status": "fallback", "via": "azure", "message": "GITHUB_TOKEN not set in environment"}

            # If we reach here, attempt to create a client and return loaded status.
            try:
                from azure.core.credentials import AzureKeyCredential
                from azure.ai.inference import ChatCompletionsClient

                endpoint = os.environ.get("GITHUB_INFERENCE_ENDPOINT", "https://models.github.ai/inference")
                client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(token))
                # Do not make a network call here; just return success that client constructed.
                return {"status": "loaded", "via": "azure", "model_id": model_id, "endpoint": endpoint}
            except Exception as e:
                return {"status": "error", "via": "azure", "message": str(e)}
    except Exception:
        pass

    # Default fallback when transformer/azure loaders not available
    return {"status": "fallback", "message": "no local loader available for model"}
