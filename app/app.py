import os
from pathlib import Path
from flask import Flask, request, jsonify,send_from_directory, abort
import aq,user

class WebApp:
    def __init__(self, static_folder='static'):
        noaa_data_path = os.path.join(Path.cwd().parent, "model/data/noaa-gsod")
        self.air_quality = aq.AirQuality(noaa_data_path)
        self.app = Flask(
            __name__,
            static_folder=static_folder
        )
        self.register_routes()

    def register_routes(self):
        @self.app.route('/')
        def serve_root():
            return self.send_static_html('index.html')

        @self.app.route('/<path:filename>')
        def serve_static(filename):
            return self.send_static_html(filename)
        
        @self.app.route('/predict')
        def serve_predict():
            city  = request.args.get('city')
            if city is None or city == '':
                return "bad request, need parameter city",400
            else:
                predict_data = self.air_quality.predict(city)
                if predict_data is None:
                    return f"can not predict weather and air quality for {city}", 204
                return jsonify(predict_data)
            
        @self.app.route('/login', methods=['POST'])
        def serve_login():
            username = request.json.get('username')
            password = request.json.get('password')
            type = request.json.get('type')

            if user.UserManager().check_user(username,password,type):
                return jsonify({"success": True, "message": "登录成功"})
            else:
                return jsonify({"success": False, "message": "用户名或密码错误"})

    def send_static_html(self, filename):
        try:
            return send_from_directory(self.app.static_folder, filename)
        except FileNotFoundError:
            abort(404)

    def run(self, host='0.0.0.0', port=5000, debug=False, **options):
        self.app.run(host=host, port=port, debug=debug, **options)


if __name__ == '__main__':
    app = WebApp()
    app.run(debug=True)