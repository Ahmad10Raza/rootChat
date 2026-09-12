import requests
import json
from utils.logger import logger

class OllamaClient:
    """Communicates with the locally running Ollama API server."""
    
    def __init__(self, endpoint="http://localhost:11434"):
        self.endpoint = endpoint.rstrip("/")
        logger.info("OllamaClient initialized with endpoint: %s", self.endpoint)

    def set_endpoint(self, endpoint):
        """Updates the Ollama API endpoint."""
        self.endpoint = endpoint.rstrip("/")
        logger.info("OllamaClient endpoint updated to: %s", self.endpoint)

    def check_connection(self) -> tuple[bool, str]:
        """
        Checks if the Ollama server is running and reachable.
        
        Returns:
            A tuple of (is_connected, status_message).
        """
        url = self.endpoint
        logger.debug("Checking Ollama connection at %s", url)
        try:
            # Send simple GET request to the root or tags endpoint
            response = requests.get(url, timeout=3.0)
            if response.status_code == 200:
                logger.info("Ollama connection check successful at %s", url)
                return True, "Connected"
            else:
                msg = f"Ollama returned unexpected status code {response.status_code}."
                logger.warning("Ollama connection check warning: %s", msg)
                return False, msg
        except requests.exceptions.Timeout:
            msg = f"Connection timeout after 3 seconds at {self.endpoint}."
            logger.warning("Ollama connection check failure: %s", msg)
            return False, "Connection Timeout"
        except requests.exceptions.ConnectionError:
            msg = f"Could not connect to Ollama at {self.endpoint}. Make sure the service is running."
            logger.warning("Ollama connection check failure: %s", msg)
            return False, "Offline"
        except Exception as e:
            msg = f"An unexpected error occurred: {str(e)}"
            logger.error("Ollama connection check error: %s", msg)
            return False, "Error"

    def list_models(self) -> list[dict]:
        """
        Retrieves the list of installed models from Ollama.
        
        Returns:
            A list of dictionaries representing installed models.
        """
        url = f"{self.endpoint}/api/tags"
        logger.debug("Retrieving Ollama models from %s", url)
        try:
            response = requests.get(url, timeout=3.0)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                logger.info("Successfully retrieved %d models from Ollama.", len(models))
                
                # Format the response data for application use
                formatted_models = []
                for m in models:
                    formatted_models.append({
                        "name": m.get("name"),
                        "model": m.get("model", m.get("name")),
                        "size": m.get("size", 0),
                        "modified_at": m.get("modified_at", ""),
                        "family": m.get("details", {}).get("family", "")
                    })
                return formatted_models
            else:
                logger.error("Failed to list models, server returned status %d", response.status_code)
                return []
        except Exception as e:
            logger.error("Failed to retrieve models from Ollama: %s", e)
            return []

    def get_model_info(self, model_name: str) -> dict:
        """
        Retrieves details about a specific model.
        
        Returns:
            A dictionary containing model details.
        """
        url = f"{self.endpoint}/api/show"
        logger.debug("Retrieving info for model '%s' from %s", model_name, url)
        try:
            response = requests.post(url, json={"name": model_name}, timeout=3.0)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to get model info for %s: %d", model_name, response.status_code)
                return {}
        except Exception as e:
            logger.error("Error retrieving info for model %s: %s", model_name, e)
            return {}

    def generate_embeddings(self, model: str, text: str) -> list:
        """Generates embeddings using the specified model."""
        url = f"{self.endpoint}/api/embeddings"
        payload = {
            "model": model,
            "prompt": text
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("embedding", [])
        except requests.RequestException as e:
            logger.error("Failed to generate embedding: %s", e)
            raise

    def stream_chat(self, model: str, messages: list, options: dict = None):
        """
        Streams a chat response from Ollama.
        Yields dictionaries representing each chunk.
        """
        url = f"{self.endpoint}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        if options:
            payload["options"] = options
            
        logger.debug("Streaming chat from %s with model %s", url, model)
        
        try:
            with requests.post(url, json=payload, stream=True, timeout=10.0) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        yield json.loads(line)
        except Exception as e:
            logger.error("Error during streaming chat with model %s: %s", model, e)
            raise

    def pull_model(self, model_name: str):
        """
        Pulls a model from the Ollama library.
        Yields dictionaries with progress information:
        e.g. {'status': 'downloading ...', 'completed': int, 'total': int}
        """
        url = f"{self.endpoint}/api/pull"
        payload = {"name": model_name, "stream": True}
        logger.info("Pulling model %s from %s", model_name, url)
        try:
            with requests.post(url, json=payload, stream=True, timeout=60.0) as response:
                if response.status_code != 200:
                    try:
                        err = response.json().get("error", response.text)
                    except Exception:
                        err = response.text
                    raise Exception(f"Failed to pull model: {err}")
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if "error" in data:
                            raise Exception(data["error"])
                        yield data
        except Exception as e:
            logger.error("Error during pulling model %s: %s", model_name, e)
            raise

    def delete_model(self, model_name: str) -> tuple[bool, str]:
        """
        Deletes a model from Ollama.
        Returns:
            (success: bool, message: str)
        """
        url = f"{self.endpoint}/api/delete"
        logger.info("Deleting model %s at %s", model_name, url)
        try:
            response = requests.delete(url, json={"name": model_name}, timeout=10.0)
            if response.status_code == 200:
                logger.info("Successfully deleted model %s", model_name)
                return True, f"Model '{model_name}' deleted successfully."
            else:
                try:
                    err = response.json().get("error", response.text)
                except Exception:
                    err = response.text
                logger.warning("Failed to delete model %s: %s (status %d)", model_name, err, response.status_code)
                return False, f"Failed to delete model: {err}"
        except Exception as e:
            logger.error("Error deleting model %s: %s", model_name, e)
            return False, str(e)
