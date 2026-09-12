from PySide6.QtCore import QThread, Signal
from core.ollama_client import OllamaClient
from utils.logger import logger

class StreamWorker(QThread):
    """Background worker for streaming chat responses from Ollama."""
    
    # Signals
    chunk_received = Signal(str)
    generation_finished = Signal(str)
    generation_error = Signal(str)
    stats_received = Signal(dict)
    
    def __init__(self, client: OllamaClient, model: str, messages: list, options: dict = None):
        super().__init__()
        self.client = client
        self.model = model
        self.messages = messages
        self.options = options
        self._is_running = True
        self.full_response = ""
        
    def stop(self):
        """Signal the worker to stop generating."""
        self._is_running = False
        
    def run(self):
        logger.debug("StreamWorker started for model %s", self.model)
        try:
            for chunk in self.client.stream_chat(self.model, self.messages, self.options):
                if not self._is_running:
                    logger.info("StreamWorker stopped by user request.")
                    break
                    
                if "message" in chunk and "content" in chunk["message"]:
                    content_chunk = chunk["message"]["content"]
                    self.full_response += content_chunk
                    self.chunk_received.emit(content_chunk)
                    
                if chunk.get("done", False):
                    eval_count = chunk.get("eval_count", 0)
                    eval_duration = chunk.get("eval_duration", 0)
                    prompt_eval_count = chunk.get("prompt_eval_count", 0)
                    prompt_eval_duration = chunk.get("prompt_eval_duration", 0)
                    total_duration = chunk.get("total_duration", 0)
                    
                    eval_rate = 0.0
                    if eval_duration > 0 and eval_count > 0:
                        eval_rate = eval_count / (eval_duration / 1e9)
                        
                    stats = {
                        "eval_count": eval_count,
                        "eval_duration": eval_duration,
                        "prompt_eval_count": prompt_eval_count,
                        "prompt_eval_duration": prompt_eval_duration,
                        "total_duration": total_duration,
                        "eval_rate": round(eval_rate, 1),
                    }
                    self.stats_received.emit(stats)
                    break
                    
            logger.debug("StreamWorker finished generating response.")
            self.generation_finished.emit(self.full_response)
        except Exception as e:
            logger.error("StreamWorker encountered an error: %s", e)
            self.generation_error.emit(str(e))
