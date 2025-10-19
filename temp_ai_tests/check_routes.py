from services.api.app import app

print("Registered routes:")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        print(f"  {', '.join(route.methods):8s} {route.path}")
