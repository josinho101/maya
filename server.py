import os
import sys

# Set working directory to project root so all existing relative paths work
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=8080, use_reloader=False)
