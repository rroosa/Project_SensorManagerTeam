
# configurazione di base che verrà 
#eredidata da altre configurazioni di classe figlie""

class Config(object): 
	DEBUG = False
	TESTING = False

	CONNECT_S3 = f"http://localhost:5002"
	CONNECT_DB = f"http://localhost:5003"

	UPLOAD_FOLDER = 'static/upload'
	DOWNLOAD_FOLDER = 'static/download'

	BUCKET_TEMPLATE = 'sensor-device-template'
	BUCKET_DATA_SHEET = 'sensors-data-sheet'

class ProductionConfig(Config):
	pass

class DevelopmentConfig(Config):
	DEBUG = True

class TestingConfig(Config):
	TESTING = True

