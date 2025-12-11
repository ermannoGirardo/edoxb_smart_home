import yaml
import json
from pathlib import Path
from typing import Optional
from app.models import SensorTemplate, SensorFieldTemplate


class ConfigLoader:
    """Carica il template dei sensori da file YAML o JSON"""
    
    def __init__(self, config_path: str = "sensors_config.yaml"):
        self.config_path = Path(config_path)
        self.template: Optional[SensorTemplate] = None
    
    def load_template(self) -> SensorTemplate:
        """Carica il template dal file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"File di configurazione non trovato: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            if self.config_path.suffix in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            elif self.config_path.suffix == '.json':
                config_data = json.load(f)
            else:
                raise ValueError(f"Formato file non supportato: {self.config_path.suffix}")
        
        # Carica il template
        if 'sensor_template' not in config_data:
            raise ValueError("Template 'sensor_template' non trovato nel file di configurazione")
        
        template_data = config_data['sensor_template']
        
        # Converti i campi in SensorFieldTemplate
        def convert_fields(fields_data):
            return [SensorFieldTemplate(**field) for field in fields_data]
        
        template = SensorTemplate(
            common_fields=convert_fields(template_data.get('common_fields', [])),
            http_fields=convert_fields(template_data.get('http_fields', [])),
            websocket_fields=convert_fields(template_data.get('websocket_fields', [])),
            custom_fields=convert_fields(template_data.get('custom_fields', []))
        )
        
        self.template = template
        return template
    
    def reload_template(self) -> SensorTemplate:
        """Ricarica il template"""
        return self.load_template()

