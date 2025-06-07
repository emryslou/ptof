from ptof.logger import logger
from .parser import ParserBase, Optional
# from ptof.smic import SMICParser as _
# from ptof.xmc import XMCParser as _
from .package_list import PackageListParser as _

def create_parser(name: str, *args, **kwargs) -> Optional[ParserBase]:
    if name not in ParserBase.plugins.keys():
        logger.error("Parser Not Found, name: {}, names: {}", name, ParserBase.plugins.keys())
        return None
    
    return ParserBase.plugins[name](*args, **kwargs)


__import__ = ["create_parser"]
