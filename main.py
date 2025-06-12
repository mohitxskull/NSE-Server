import os
import logging
from flask import Flask, request, jsonify
from functools import wraps
from dotenv import load_dotenv
import nsepythonserver as nse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get API key from environment
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    logger.error("API_KEY environment variable is not set")
    raise ValueError("API_KEY environment variable is required")

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get authorization header
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                'error': 'Authorization header is required',
                'message': 'Please provide Authorization header with your API key'
            }), 401

        # Extract API key from header (expecting format: "Bearer <api_key>" or just "<api_key>")
        if auth_header.startswith('Bearer '):
            provided_key = auth_header[7:]  # Remove "Bearer " prefix
        else:
            provided_key = auth_header

        if provided_key != API_KEY:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 401

        return f(*args, **kwargs)

    return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        'status': 'healthy',
        'message': 'NSE Option Chain API is running'
    }), 200

@app.route('/option-chain', methods=['GET'])
@require_api_key
def get_option_chain():
    """Get NSE option chain data for a given symbol"""
    try:
        # Get symbol from query parameter
        symbol = request.args.get('symbol')

        if not symbol:
            return jsonify({
                'error': 'Symbol parameter is required',
                'message': 'Please provide a symbol as query parameter'
            }), 400

        # Convert symbol to uppercase
        symbol = symbol.upper()

        logger.info(f"Fetching option chain for symbol: {symbol}")

        # Fetch option chain data using nsepythonserver
        try:
            option_chain_data = nse.option_chain(symbol)

            if not option_chain_data:
                return jsonify({
                    'error': 'No data found',
                    'message': f'No option chain data found for symbol: {symbol}'
                }), 404

            return jsonify({
                'success': True,
                'symbol': symbol,
                'data': option_chain_data
            }), 200

        except Exception as nse_error:
            logger.error(f"NSE API error for symbol {symbol}: {str(nse_error)}")
            return jsonify({
                'error': 'NSE API error',
                'message': f'Failed to fetch data from NSE: {str(nse_error)}'
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information"""
    return jsonify({
        'message': 'NSE Option Chain API',
        'version': '1.0.0',
        'endpoints': {
            'option_chain': '/option-chain?symbol=<SYMBOL>',
            'health': '/health'
        },
        'authentication': 'Required - Pass API key in Authorization header'
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'The requested endpoint does not exist'
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method not allowed',
        'message': 'The request method is not allowed for this endpoint'
    }), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An internal server error occurred'
    }), 500

if __name__ == '__main__':
    # Get port from environment variable (Cloud Run provides this)
    port = int(os.getenv('PORT', 8080))

    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_ENV') == 'development'
    )
