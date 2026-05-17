#!/usr/bin/env python
import os
from app import create_app

if __name__ == '__main__':
    app = create_app()
    # Create upload directory if it doesn't exist
    os.makedirs('uploads', exist_ok=True)
    # Run the development server
    app.run(debug=True, host='127.0.0.1', port=5000)
