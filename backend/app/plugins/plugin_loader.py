"""
Sistema di caricamento dinamico dei sensori da repository esterno
Ottimizzato per zero overhead a runtime
"""

import os
import json
import aiohttp
import aiofiles
from pathlib import Path
from typing import Dict, List, Optional, Any
import importlib.util
import sys


class PluginLoader:
    """Carica i plugin sensori da repository esterno - zero overhead a runtime"""
    
    def __init__(self, plugins_dir: Path = None):
        self.plugins_dir = plugins_dir or Path("/app/plugins")
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.registry_url = os.getenv(
            "SENSOR_REGISTRY_URL", 
            "https://raw.githubusercontent.com/edoxb/smart-home-sensors/main"
        )
        # Cache dei router caricati (zero lookup a runtime)
        self._loaded_routers: Dict[str, Any] = {}
    
    async def download_sensor_plugin(
        self, 
        sensor_id: str, 
        version: Optional[str] = None
    ) -> bool:
        """
        Scarica un plugin sensore dal registry (solo all'avvio)
        
        Args:
            sensor_id: ID del sensore (es: 'shelly_rgbw2')
            version: Versione del plugin (opzionale, default: 'latest')
        
        Returns:
            True se il download è riuscito
        """
        try:
            version = version or "latest"
            sensor_dir = self.plugins_dir / sensor_id
            
            # Crea directory del sensore
            sensor_dir.mkdir(parents=True, exist_ok=True)
            
            # Verifica se il plugin è già scaricato (cache)
            backend_path = sensor_dir / f"{sensor_id}.py"
            if backend_path.exists():
                print(f"✓ Plugin {sensor_id} già presente (cache)")
                return True
            
            # Download file backend route
            backend_url = f"{self.registry_url}/{sensor_id}/backend/{sensor_id}.py"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(backend_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.read()
                        async with aiofiles.open(backend_path, 'wb') as f:
                            await f.write(content)
                        print(f"✓ Scaricato backend route per {sensor_id}")
                    else:
                        print(f"✗ Errore download backend route per {sensor_id}: HTTP {response.status}")
                        return False
                
                # Download metadata (opzionale)
                metadata_url = f"{self.registry_url}/{sensor_id}/metadata.json"
                metadata_path = sensor_dir / "metadata.json"
                
                try:
                    async with session.get(metadata_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            content = await response.read()
                            async with aiofiles.open(metadata_path, 'wb') as f:
                                await f.write(content)
                except:
                    pass  # Metadata opzionale
            
            return True
            
        except Exception as e:
            print(f"✗ Errore download plugin {sensor_id}: {e}")
            return False
    
    def load_sensor_router(self, sensor_id: str):
        """
        Carica dinamicamente il router di un sensore (solo all'avvio)
        Dopo il caricamento, zero overhead a runtime!
        
        Returns:
            Router FastAPI o None
        """
        # Controlla cache
        if sensor_id in self._loaded_routers:
            return self._loaded_routers[sensor_id]
        
        try:
            sensor_file = self.plugins_dir / sensor_id / f"{sensor_id}.py"
            
            if not sensor_file.exists():
                print(f"✗ File plugin non trovato: {sensor_file}")
                return None
            
            # Carica il modulo dinamicamente (una volta, poi in sys.modules)
            spec = importlib.util.spec_from_file_location(
                f"sensor_{sensor_id}", 
                sensor_file
            )
            if spec is None or spec.loader is None:
                print(f"✗ Impossibile creare spec per {sensor_id}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"sensor_{sensor_id}"] = module
            spec.loader.exec_module(module)
            
            # Restituisce il router
            router = getattr(module, 'router', None)
            
            # Salva in cache (zero lookup futuro)
            if router:
                self._loaded_routers[sensor_id] = router
            
            return router
            
        except Exception as e:
            print(f"✗ Errore caricamento router {sensor_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def load_enabled_sensors(self, enabled_sensors: List[str]) -> List[tuple]:
        """
        Scarica e carica tutti i sensori abilitati (solo all'avvio)
        Dopo questo, zero overhead a runtime!
        
        Args:
            enabled_sensors: Lista di ID sensori da caricare
        
        Returns:
            Lista di tuple (sensor_id, router)
        """
        routers = []
        
        if not enabled_sensors:
            print("Nessun sensore abilitato")
            return routers
        
        print(f"Caricamento {len(enabled_sensors)} sensori...")
        
        for sensor_id in enabled_sensors:
            sensor_id = sensor_id.strip()
            if not sensor_id:
                continue
            
            print(f"  - Caricamento {sensor_id}...")
            
            # Verifica se il plugin è già scaricato
            sensor_dir = self.plugins_dir / sensor_id
            if not sensor_dir.exists() or not (sensor_dir / f"{sensor_id}.py").exists():
                print(f"    Download plugin {sensor_id}...")
                success = await self.download_sensor_plugin(sensor_id)
                if not success:
                    print(f"    ⚠ Impossibile scaricare plugin {sensor_id}, saltato")
                    continue
            
            # Carica il router
            router = self.load_sensor_router(sensor_id)
            if router:
                routers.append((sensor_id, router))
                print(f"    ✓ Plugin {sensor_id} caricato e registrato")
            else:
                print(f"    ✗ Impossibile caricare router per {sensor_id}")
        
        return routers
    
    def get_plugin_metadata(self, sensor_id: str) -> Optional[Dict[str, Any]]:
        """
        Legge i metadata di un plugin (se disponibili)
        """
        try:
            metadata_path = self.plugins_dir / sensor_id / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    return json.load(f)
        except:
            pass
        return None

