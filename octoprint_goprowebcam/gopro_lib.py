import time

import requests


class GoPro:

    def __init__(self, serial, _logger):
        self.serial = serial
        self._logger = _logger

    def get_ip_address(self):
        ip_address = f'http://172.2{self.serial[-3]}.1{self.serial[-2:]}.51:8080'
        return ip_address

    def send_gopro_command(self, method, endpoint, body=None):
        url = f'{self.get_ip_address()}{endpoint}'
        self._logger.info("Executing gopro command: %s" % url)
        if body:
            response = requests.request(method, url, json=body, timeout=3)
        else:
            response = requests.request(method, url, timeout=3)
        return response

    def set_camera_as_third_party(self):
        return self.send_gopro_command('GET', '/gopro/camera/analytics/set_client_info').status_code == 200

    def enable_wired_camera_control(self):
        return self.send_gopro_command('GET', '/gopro/camera/control/wired_usb?p=1').status_code == 200

    def get_file_stream(self, path):
        download_url = f'{self.get_ip_address()}/videos/DCIM/{path}'
        r = requests.get(download_url, stream=True)
        return r.iter_content(chunk_size=1024)

        # with open(file_name, 'wb') as f:
        #     for chunk in r.iter_content(chunk_size=1024):
        #         if chunk:
        #             f.write(chunk)
        # return file_name

    def delete_file(self, file_path):
        self._logger.info('deleting file %s from GoPro' % file_path)
        return self.send_gopro_command('GET', '/gopro/media/delete/file?path=' + file_path).status_code == 200

    def set_photo_mode(self):
        return self.send_gopro_command('POST', '/gp/gpControl/command/mode?p=1&submode=1&sub_mode=0').status_code == 200

    def take_photo(self):
        return self.send_gopro_command('POST', '/gp/gpControl/command/shutter?p=1').status_code == 200

    def parse_media_list(self, media):
        files = []
        for item in media:
            if 'fs' and 'd' in item:
                for file_item in item['fs']:
                    path = f"{item['d']}/{file_item['n']}"
                    files.append({'mod': file_item['mod'], 'path': path})
        return files

    def get_media_list(self, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.send_gopro_command('GET', '/gp/gpMediaList')
            if response.status_code == 200:
                return self.parse_media_list(response.json()['media'])
            time.sleep(0.1)  # Wait for 0.1 seconds before retrying
        return []


