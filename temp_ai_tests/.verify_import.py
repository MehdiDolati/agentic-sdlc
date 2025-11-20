import sys, pathlib
print("cwd:", pathlib.Path().resolve())
print("PYTHONPATH ok?:", any(p.endswith("agentic-sdlc") for p in sys.path))
import services
print("services package file:", services.__file__)
