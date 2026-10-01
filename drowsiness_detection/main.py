import threading
import webbrowser
from app import app, detector

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8000")

def main():
    print("=" * 55)
    print("  GuardianAI | Driver Drowsiness Detection System")
    print("=" * 55)
    print("  Starting Web Server on port 8000...")
    
    # Start the detection engine
    detector.start()
    
    # Open browser after a short delay
    threading.Timer(1.5, open_browser).start()
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)

if __name__ == "__main__":
    main()
