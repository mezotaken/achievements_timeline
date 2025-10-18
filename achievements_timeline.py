import requests
import sys
import datetime
import json
import os
from PyQt6 import QtWidgets, uic


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


class APIError(Exception):
    pass


class SimpleSteamAPI:
    def __init__(self, steam_api_key, vanity_name):
        self.steam_api_key = steam_api_key,
        self.steam_id = self.resolve_vanity_url(vanity_name)


    def resolve_vanity_url(self, vanity_name):
        url = 'https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/'
        params = {'key': self.steam_api_key, 'vanityurl': vanity_name}
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            raise APIError(f'Error {resp.status_code} while retrieving Steam ID {resp.text}')
        else:
            return resp.json()['response']['steamid']


    def get_player_achievements(self, app_id):
        url = 'https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/'
        params = {'key': self.steam_api_key, 'steamid': self.steam_id, 'appid': app_id, 'l': 'en'}
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            raise APIError(f'Error {resp.status_code} while retrieving achievements {resp.text}')
        else:
            return resp.json()['playerstats']['achievements']


    def get_playtime(self, app_id):
        url = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/'
        req_body = {'steamid': self.steam_id, 'appids_filter': [int(app_id)]}
        params = {'key': self.steam_api_key, 'input_json': json.dumps(req_body)}
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            raise APIError(f'Error {resp.status_code} while retrieving playtime {resp.text}')
        else:
            return resp.json()['response']['games'][0]['playtime_forever']


class AchievementsTimelineApp(QtWidgets.QMainWindow):
    def __init__(self):
        # Load UI
        super().__init__()
        uic.loadUi(resource_path('achievements_timeline.ui'), self)
        # Syntax highlight
        self.app_id_value: QtWidgets.QLabel
        self.vanity_name_value: QtWidgets.QLabel
        self.api_key_value: QtWidgets.QLabel
        self.fetch_button: QtWidgets.QPushButton
        self.save_button: QtWidgets.QPushButton
        self.load_button: QtWidgets.QPushButton
        self.orig_pt_value: QtWidgets.QLabel
        self.new_pt_value: QtWidgets.QLabel
        # Button actions
        self.fetch_button.clicked.connect(self.fetch_data)
        self.save_button.clicked.connect(self.save_data)
        self.load_button.clicked.connect(self.load_data)


    def fetch_data(self):
        app_id = self.app_id_value.text()

        try:
            steam_api = SimpleSteamAPI(self.api_key_value.text(), self.vanity_name_value.text())
            achievements = steam_api.get_player_achievements(app_id)
            playtime = steam_api.get_playtime(app_id)
        except APIError as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))
            return

        unlocked = [a for a in achievements if a['achieved']]
        unlocked.sort(key=lambda x: x['unlocktime'])
        self.orig_pt_value.setText(f'{playtime//60}h {playtime%60}m')


    def save_data(self):
        data = {
            'api_key': self.api_key_value.text(),
            'vanity_name': self.vanity_name_value.text(),
            'app_id': self.app_id_value.text(),
            'original_timeline': {
            },
            'new_timeline': {
            }
        }
        with open('current_data.json', 'w') as f:
            json.dump(data, f)


    def load_data(self):
        if not os.path.isfile('current_data.json'):
            return
        with open('current_data.json', 'r') as f:
            data = json.load(f)
        self.api_key_value.setText(data['api_key'])
        self.vanity_name_value.setText(data['vanity_name'])
        self.app_id_value.setText(data['app_id'])
        self.fetch_data()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = AchievementsTimelineApp()
    window.show()
    sys.exit(app.exec())
