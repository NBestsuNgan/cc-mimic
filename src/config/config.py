from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(override=True)

class ModelConfig(BaseModel): # separate for "Modle" configuration params, easily to extendable in the future
    name: str = "openrouter/owl-alpha" 
    temperature: float = Field(default=1, ge=0.0, le=2.0) 
    context_window: int = 1_000_000

class Config(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    cwd: Path = Field(default_factory=Path.cwd)

    max_turns: int = 100

    developer_instructions: str | None = None
    user_instructions: str | None = None

    debug: bool = False

    @property
    def api_key(self) -> str | None:
        return os.environ.get("API_KEY")
    
    @property
    def base_url(self) -> str | None:
        return os.environ.get("BASE_URL")
    
    @property
    def model_name(self) -> str:
        return self.model.name
    
    @model_name.setter
    def model_name(self, value: str) -> None:
        #re-write the model name in the config
        self.model.name = value

    @property
    def temperature(self) -> float:
        return self.model.temperature
    
    @temperature.setter
    def temperature(self, value: float) -> None:
        self.model.temperature = value

    def validate(self) -> list[str]:
        # usage in validating the config
        errors: list[str] = []

        if not self.api_key:
            errors.append("NO API key found. Set API_KEY environment variables.")

        if not self.cwd.exists():
            errors.append(f"Current working directory does not exist: {self.cwd}")

        return errors
