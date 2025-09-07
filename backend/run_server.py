import uvicorn
import os

def main():
    """
    Runs the FastAPI application using uvicorn.
    This script provides a standardized way to start the server.
    """
    # It's good practice to set the app location dynamically
    # to avoid issues with the current working directory.
    app_location = "app.main:app"
    
    uvicorn.run(
        app_location,
        host="127.0.0.1",
        port=8001,
        reload=False,
        # The reload_dirs parameter is useful if you have other directories
        # with code that should trigger a reload on change.
        # reload_dirs=[os.path.dirname(os.path.abspath(__file__))]
    )

if __name__ == "__main__":
    main()
