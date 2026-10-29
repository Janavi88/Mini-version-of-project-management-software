from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config=None):
    app = Flask(__name__, static_folder='../static', static_url_path='')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskboard.db'
    app.config['SECRET_KEY'] = 'change-this-secret-before-deploying'
    if config:
        app.config.update(config)
    db.init_app(app)

    from .routes import api
    app.register_blueprint(api, url_prefix='/api')

    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    with app.app_context():
        db.create_all()
    return app
