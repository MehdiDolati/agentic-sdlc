import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'services'))

try:
    from fastapi import FastAPI
    from contextlib import asynccontextmanager
    from fastapi.middleware.cors import CORSMiddleware

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print('Starting lifespan...')
        try:
            yield
            print('Lifespan yielding back')
        except Exception as e:
            print(f'Error in lifespan: {e}')
            import traceback
            traceback.print_exc()
            raise
        finally:
            print('Lifespan shutdown')

    app = FastAPI(lifespan=lifespan)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:8080', 'http://127.0.0.1:8080'],
        allow_methods=['*'],
        allow_headers=['*'],
    )

    print('FastAPI app created with CORS')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()