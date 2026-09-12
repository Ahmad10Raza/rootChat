from PySide6.QtCore import QThread, Signal
from core.ollama_client import OllamaClient
from utils.logger import logger

class OllamaConnectionWorker(QThread):
    """Background worker to check the Ollama server connection."""
    # Signals to communicate results back to the main thread
    # Emits (is_connected: bool, status_message: str)
    finished = Signal(bool, str)

    def __init__(self, client: OllamaClient):
        super().__init__()
        self.client = client

    def run(self):
        logger.debug("OllamaConnectionWorker running...")
        is_connected, message = self.client.check_connection()
        logger.debug("OllamaConnectionWorker finished. Connected: %s, Message: %s", is_connected, message)
        self.finished.emit(is_connected, message)


class OllamaModelsWorker(QThread):
    """Background worker to fetch the list of installed models from Ollama."""
    # Signals to communicate results back to the main thread
    # Emits list of models on success, or error string on failure
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, client: OllamaClient):
        super().__init__()
        self.client = client

    def run(self):
        logger.debug("OllamaModelsWorker running...")
        try:
            models = self.client.list_models()
            logger.debug("OllamaModelsWorker finished. Found %d models.", len(models))
            self.finished.emit(models)
        except Exception as e:
            logger.error("OllamaModelsWorker error: %s", e)
            self.error.emit(str(e))

class OllamaStartWorker(QThread):
    """Background worker to start the Ollama systemd service via sudo."""
    finished = Signal(bool, str)

    def __init__(self, password: str):
        super().__init__()
        self.password = password

    def run(self):
        import subprocess
        logger.debug("OllamaStartWorker running...")
        try:
            # We use sudo -S to read password from stdin
            process = subprocess.Popen(
                ['sudo', '-S', 'systemctl', 'start', 'ollama'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(input=self.password + '\n')
            
            if process.returncode == 0:
                logger.info("Successfully started Ollama service via systemctl.")
                self.finished.emit(True, "Service started successfully.")
            else:
                err_msg = stderr.strip() if stderr else "Unknown error."
                logger.error(f"Failed to start Ollama: {err_msg}")
                self.finished.emit(False, err_msg)
        except Exception as e:
            logger.error(f"Exception while starting Ollama: {e}")
            self.finished.emit(False, str(e))


class OllamaPullWorker(QThread):
    """Background worker to stream pull a model from Ollama."""
    progress = Signal(dict)   # {"status": str, "completed": int, "total": int, "percent": float}
    finished = Signal(str)    # model_name
    error = Signal(str)

    def __init__(self, client: OllamaClient, model_name: str):
        super().__init__()
        self.client = client
        self.model_name = model_name
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        logger.info("OllamaPullWorker started for model: %s", self.model_name)
        try:
            for chunk in self.client.pull_model(self.model_name):
                if self._is_stopped:
                    logger.info("OllamaPullWorker stopped by user for %s", self.model_name)
                    self.error.emit("Download cancelled by user.")
                    return
                
                status = chunk.get("status", "")
                completed = chunk.get("completed", 0)
                total = chunk.get("total", 0)
                percent = (completed / total * 100.0) if total and total > 0 else 0.0

                self.progress.emit({
                    "status": status,
                    "completed": completed,
                    "total": total,
                    "percent": percent
                })

            if not self._is_stopped:
                logger.info("OllamaPullWorker finished successfully for %s", self.model_name)
                self.finished.emit(self.model_name)
        except Exception as e:
            logger.error("OllamaPullWorker error for %s: %s", self.model_name, e)
            if not self._is_stopped:
                self.error.emit(str(e))


class OllamaDeleteWorker(QThread):
    """Background worker to delete a model from Ollama."""
    finished = Signal(bool, str)

    def __init__(self, client: OllamaClient, model_name: str):
        super().__init__()
        self.client = client
        self.model_name = model_name

    def run(self):
        logger.info("OllamaDeleteWorker started for model: %s", self.model_name)
        success, message = self.client.delete_model(self.model_name)
        self.finished.emit(success, message)


class OllamaShowWorker(QThread):
    """Background worker to fetch detailed metadata for a model."""
    finished = Signal(str, dict)
    error = Signal(str)

    def __init__(self, client: OllamaClient, model_name: str):
        super().__init__()
        self.client = client
        self.model_name = model_name

    def run(self):
        logger.debug("OllamaShowWorker started for model: %s", self.model_name)
        try:
            info = self.client.get_model_info(self.model_name)
            self.finished.emit(self.model_name, info)
        except Exception as e:
            logger.error("OllamaShowWorker error for %s: %s", self.model_name, e)
            self.error.emit(str(e))
