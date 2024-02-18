import os

import octoprint.plugin
from flask import Response, Flask
from octoprint.schema.webcam import Webcam, WebcamCompatibility

from PIL import Image
import io

from octoprint_goprowebcam.gopro_lib import GoPro

app = Flask(__name__)


class GoProWebcamPlugin(octoprint.plugin.StartupPlugin,
                        octoprint.plugin.TemplatePlugin,
                        octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.AssetPlugin,
                        octoprint.plugin.BlueprintPlugin,
                        octoprint.plugin.WebcamProviderPlugin, ):

    def __init__(self):
        self._flask_app = Flask(__name__)
        super().__init__()

    def is_blueprint_protected(self):
        return False

    @octoprint.plugin.BlueprintPlugin.route("/snapshot", methods=["GET"])
    def get_snapshot(self):
        file_stream = self.get_snapshot_bytes_stream()
        def generate():
            for chunk in file_stream:
                if chunk:
                    yield chunk
        return Response(generate(), mimetype='image/jpeg')

    def get_snapshot_bytes_stream(self):
        self._logger.info('Got GOPRO snapshot request!')
        serial = self._settings.get(["serial"])
        keep_files_on_camera = self._settings.get(["keep_files_on_camera"])
        enable_camera_control = self._settings.get(["enable_camera_control"])
        if not serial:
            raise 'Camera serial not provided'
        gopro = GoPro(serial, self._logger)
        if enable_camera_control:
            if not gopro.set_camera_as_third_party():
                raise Exception('Failed to get control of GoPro')
            gopro.enable_wired_camera_control()
            # no need to check if succeeded ^
        if not gopro.set_photo_mode():
            raise  Exception('Failed to set GoPro to photo mode')
        if not gopro.take_photo():
            raise  Exception('Failed to take photo')

        media_list = gopro.get_media_list()
        if not media_list:
            raise  Exception('Failed to get media list')

        most_recent_file_path = sorted(media_list, key=lambda x: x['mod'], reverse=True)[0]['path']

        file_stream = gopro.get_file_stream(most_recent_file_path)

        # Assuming `mpo_data` contains the MPO image data as bytes
        mpo_image = Image.open(io.BytesIO(b''.join(file_stream)))
        mpo_image.seek(0)  # Select the first image (the JPEG side of the MPO)
        jpeg_image = mpo_image.convert('RGB')

        # Convert the JPEG image to a byte stream
        output_stream = io.BytesIO()
        jpeg_image.save(output_stream, format='JPEG')
        output_stream.seek(0)

        if not keep_files_on_camera:
            gopro.delete_file(most_recent_file_path)

        return output_stream

    def is_blueprint_csrf_protected(self):
        return True


    def get_webcam_configurations(self):
        return [
            Webcam(
                name="gopro",
                displayName="GoPro",
                canSnapshot=True,
                snapshot="GoPro image",
                compat=WebcamCompatibility(
                    snapshot="/plugin/gopro_server/snapshot",
                    stream="/plugin/gopro_server/snapshot",
                ),
            )
        ]

    def take_webcam_snapshot(self, webcamName):
        return self.get_snapshot_bytes_stream()

    def on_after_startup(self):
        self._logger.info("GoPro Server plugin started!")

    def get_settings_defaults(self):
        return dict(serial="",
                    keep_files_on_camera=False,
                    enable_camera_control=True,
                    )

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

    def get_assets(self):
        return {
            "js": ["js/goprowebcam.js"],
            "css": ["css/goprowebcam.css"],
            "less": ["less/goprowebcam.less"]
        }


__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = GoProWebcamPlugin()
