from typing import Optional, Type, Dict, List, Tuple
from pathlib import Path
import fitz

class ParserBase(object):
    
    name: str
    plugins: Dict[str, Type["ParserBase"]] = {}

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __init_subclass__(cls, *args, **kwargs) -> None:
        super().__init_subclass__(*args, **kwargs)
        if hasattr(cls, 'name') and cls.name:
            cls.plugins[cls.name] = cls
    
    def do(self, pdf_file: str | Path, *args, **kwargs) -> Optional[List[Dict]]:
        return None
