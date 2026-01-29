from flask import Flask, jsonify, request
import os

app = Flask(__name__)

# Feature flag to simulate a bug
SIMULATE_FAILURE = os.getenv("SIMULATE_FAILURE", "false").lower() == "true"

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "version": os.getenv("VERSION", "1.0.0")})

@app.route('/')
def home():
    if SIMULATE_FAILURE:
        # Simulate a 500 error for the AI to detect
        return jsonify({"error": "Internal Server Error", "details": "NullPointerException in payment_gateway"}), 500
    
    return jsonify({
        "message": "Self-Healing CI/CD Demo", 
        "version": os.getenv("VERSION", "1.0.0"),
        "status": "Operational"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
