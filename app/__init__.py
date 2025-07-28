from flask_cors import CORS
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flasgger import Swagger
from .config import Config

db = SQLAlchemy()
ma = Marshmallow()

swagger_config = {
    'title': 'Jhon Team API', 
    'uiversion': 3,
    'openapi': '3.0.2',
    'specs': [
        {
            'endpoint': 'apispec_1',
            'route': '/swagger.json',
            'rule_filter': lambda rule: True,  
            'model_filter': lambda tag: True,  
        }
    ],
    'headers': [],
    'static_url_path': '/flasgger_static',
    'swagger_ui': True,
    'specs_route': '/docs/'
}

def create_app(config_class=Config):
    # Global OPTIONS handler for CORS preflight
    # Remove custom OPTIONS handler and rely on Flask-CORS
    app = Flask(__name__, static_folder='../static', static_url_path='/static')
    from flask_cors import CORS
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True, allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    app.config.from_object(config_class)


    db.init_app(app)
    ma.init_app(app)
    Swagger(app, config=swagger_config)

    # Global error handler for all unhandled exceptions
    @app.errorhandler(Exception)
    def handle_exception(e):
        from flask import jsonify
        import traceback
        code = getattr(e, 'code', 500)
        return jsonify({
            'error': str(e),
            'type': type(e).__name__,
            'traceback': traceback.format_exc()
        }), code

    # Serve HTML files from root directory
    import os
    from flask import send_from_directory
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    @app.route('/')
    def serve_index():
        return send_from_directory(PROJECT_ROOT, 'INDEX.html')

    @app.route('/index.html')
    def serve_index_html():
        return send_from_directory(PROJECT_ROOT, 'INDEX.html')

    @app.route('/generate.html')
    def serve_generate_html():
        return send_from_directory(PROJECT_ROOT, 'generate.html')

    @app.route('/about.html')
    def serve_about_html():
        return send_from_directory(PROJECT_ROOT, 'ABOUT.html')

    # Optionally serve JS files
    @app.route('/generate.js')
    def serve_generate_js():
        return send_from_directory(PROJECT_ROOT, 'generate.js')

    with app.app_context():
        from .v1 import api_v1_bp
        db.create_all()
        app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
    return app