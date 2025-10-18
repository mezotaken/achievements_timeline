import requests
import sys
import json
import os
import asyncio
import aiohttp
from PyQt6 import QtWidgets, QtGui, uic, QtCore
from PyQt6.QtWidgets import QSpacerItem, QSizePolicy

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


async def multi_fetch(elements, key='name', value='icon'):
    async def fetch_task(session, name, url):
        async with session.get(url) as resp:
            if resp.status == 200:
                return name, await resp.read()
            else:
                return name, None

    response = {}
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_task(session, elem[key], elem[value]) for elem in elements]
        for future in asyncio.as_completed(tasks):
            name, data = await future
            if data:
                response[name] = data
    return response


class TimeFormatter:
    intervals = {
        'd': 60 * 60 * 24,
        'h': 60 * 60,
        'm': 60,
        's': 1
    }
    @classmethod
    def hf_valid(cls, interval_string):
        if not isinstance(interval_string, str):
            return False, None
        parts = interval_string.strip(' ').split(' ')
        result = {}
        for part in parts:
            key = part[-1]
            if key not in 'dhms':
                return False, None
            try:
                value = int(part[:-1])
            except Exception:
                return False, None
            if value < 0:
                return False, None
            result[key] = value
        return True, result


    @classmethod
    def hf_to_ts(cls, interval_string):
        res, parsed = TimeFormatter.hf_valid(interval_string)
        if not res:
            raise Exception('Invalid interval format')
        seconds = 0
        for suffix, length in parsed.items():
            seconds += TimeFormatter.intervals[suffix]*length
        return seconds


    @classmethod
    def ts_to_hf(cls, seconds, precision='s'):
        seconds = int(seconds)
        parts = []
        for suffix, length in TimeFormatter.intervals.items():
            value = seconds // length
            if value > 0:
                parts.append(f"{value}{suffix}")
                seconds %= length
            if suffix == precision:
                break
        return ' '.join(parts) if parts else f'0{precision}'


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
        return resp.json()['response']['steamid']


    def get_player_achievements(self, app_id):
        personal_ach_url = 'https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/'
        params = {'key': self.steam_api_key, 'steamid': self.steam_id, 'appid': app_id, 'l': 'en'}
        pa_resp = requests.get(personal_ach_url, params=params)
        if pa_resp.status_code != 200:
            raise APIError(f'Error {pa_resp.status_code} while retrieving achievements {pa_resp.text}')

        game_schema_url = 'https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/'
        params = {'key': self.steam_api_key, 'appid': app_id}
        gs_resp = requests.get(game_schema_url, params=params)
        if gs_resp.status_code != 200:
            raise APIError(f'Error {gs_resp.status_code} while retrieving achievements {gs_resp.text}')
        # Подгрузка и добавление иконок
        ach_icons = asyncio.run(multi_fetch(gs_resp.json()['game']['availableGameStats']['achievements'], 'name', 'icon'))
        full_response = pa_resp.json()['playerstats']['achievements']
        for ach in full_response:
            ach['icon'] = ach_icons[ach['apiname']]

        return full_response


    def get_playtime(self, app_id):
        url = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/'
        req_body = {'steamid': self.steam_id, 'appids_filter': [int(app_id)]}
        params = {'key': self.steam_api_key, 'input_json': json.dumps(req_body)}
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            raise APIError(f'Error {resp.status_code} while retrieving playtime {resp.text}')
        return resp.json()['response']['games'][0]['playtime_forever']


class AchievementRow(QtWidgets.QWidget):
    def __init__(self, idx, offset, original_time, icon, name, callback):
        super().__init__()
        self.idx = idx
        self.callback = callback
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(10)
        self.offset = QtWidgets.QLineEdit(TimeFormatter.ts_to_hf(offset))
        self.offset.setFixedWidth(100)
        self.offset.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.offset.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.offset.textEdited.connect(self.on_text_edited)
        layout.addWidget(self.offset)
        self.unlock_time = QtWidgets.QLabel(TimeFormatter.ts_to_hf(original_time))
        self.unlock_time.setFixedWidth(100)
        self.unlock_time.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.unlock_time.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.unlock_time)

        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(icon)
        icon_label = QtWidgets.QLabel()
        if icon is not None:
            scaled = pixmap.scaled(64, 64, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                           QtCore.Qt.TransformationMode.SmoothTransformation)
        else:
            scaled = pixmap
        icon_label.setPixmap(scaled)
        icon_label.setFixedSize(64, 64)
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        name_label = QtWidgets.QLabel(name)
        name_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                 QtWidgets.QSizePolicy.Policy.Preferred)
        layout.addWidget(name_label)
        self.setLayout(layout)


    def on_text_edited(self, text):
        self.callback(self.idx)


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
        self.timeline_scroll: QtWidgets.QScrollArea
        self.timeline = self.timeline_scroll.widget().layout()
        self.replay_button: QtWidgets.QPushButton
        self.replay_time_value: QtWidgets.QLineEdit
        self.replay_time_postfix: QtWidgets.QLabel
        self.replay_ach_count_value: QtWidgets.QLabel
        self.replay_ach_count_postfix: QtWidgets.QLabel

        # Button actions
        self.fetch_button.clicked.connect(self.fetch_data)
        self.save_button.clicked.connect(self.save_data)
        self.load_button.clicked.connect(self.load_data)
        self.replay_button.clicked.connect(self.toggle_replay)
        # Edit actions
        self.replay_time_value.textEdited.connect(self.update_replay_data)


    def fetch_data(self):
        app_id = self.app_id_value.text()

        try:
            steam_api = SimpleSteamAPI(self.api_key_value.text(), self.vanity_name_value.text())
            achievements = steam_api.get_player_achievements(app_id)
            playtime = steam_api.get_playtime(app_id)
        except APIError as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))
            return
        self.orig_pt_value.setText(TimeFormatter.ts_to_hf(playtime*60))

        unlocked = [a for a in achievements if a['achieved']]
        unlocked.sort(key=lambda x: x['unlocktime'])
        if not unlocked:
            return

        for i in reversed(range(self.timeline.count())):
            item = self.timeline.itemAt(i)
            self.timeline.removeItem(item)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                del item
        base_time = unlocked[0]['unlocktime']
        cur_time = 0
        for i, a in enumerate(unlocked):
            prev_time = cur_time
            cur_time = a['unlocktime']-base_time
            self.timeline.addWidget(AchievementRow(i, cur_time - prev_time, cur_time, a['icon'], a['name'], self.recalculate_timeline))
        self.timeline.addWidget(AchievementRow(len(unlocked), 0, cur_time, None, 'N/A', self.recalculate_timeline))
        self.new_pt_value.setText(TimeFormatter.ts_to_hf(cur_time))
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.timeline.addItem(spacer)
        self.replay_time_value.setText('0s')
        self.update_replay_data()


    def recalculate_timeline(self, idx):
        cur_time = 0
        for i in range(idx, self.timeline.count() - 1):
            row: AchievementRow = self.timeline.itemAt(i).widget()
            try:
                seconds = TimeFormatter.hf_to_ts(row.offset.text())
                row.offset.setStyleSheet('color: black;')
            except Exception:
                row.offset.setStyleSheet('color: red;')
                return
            if i == idx and i != 0:
                cur_time = TimeFormatter.hf_to_ts(self.timeline.itemAt(i - 1).widget().unlock_time.text())
            row.unlock_time.setText(TimeFormatter.ts_to_hf(cur_time + seconds))
            cur_time = cur_time + seconds
        self.new_pt_value.setText(TimeFormatter.ts_to_hf(cur_time))
        self.update_replay_data()


    def save_data(self):
        new_timeline = []
        for i in range(self.timeline.count() - 1):
            row: AchievementRow = self.timeline.itemAt(i).widget()
            new_timeline.append({
                'offset': row.offset.text(),
                'unlock_time': row.unlock_time.text()
            })

        data = {
            'api_key': self.api_key_value.text(),
            'vanity_name': self.vanity_name_value.text(),
            'app_id': self.app_id_value.text(),
            'replay_time': self.replay_time_value.text(),
            'new_timeline': new_timeline
        }
        with open('current_data.json', 'w') as f:
            json.dump(data, f, indent=4)


    def load_data(self):
        if not os.path.isfile('current_data.json'):
            return
        with open('current_data.json', 'r') as f:
            data = json.load(f)
        self.api_key_value.setText(data['api_key'])
        self.vanity_name_value.setText(data['vanity_name'])
        self.app_id_value.setText(data['app_id'])
        self.fetch_data()
        for i, v in enumerate(data['new_timeline']):
            row: AchievementRow = self.timeline.itemAt(i).widget()
            row.offset.setText(v['offset'])
            row.unlock_time.setText(v['unlock_time'])
        self.replay_time_value.setText(data['replay_time'])
        self.recalculate_timeline(0)


    def update_replay_data(self):
        try:
            current_time = TimeFormatter.hf_to_ts(self.replay_time_value.text())
            self.replay_time_value.setStyleSheet('color: black;')
        except Exception:
            self.replay_time_value.setStyleSheet('color: red;')
            return
        total_achievement_count = self.timeline.count() - 2
        last_row: AchievementRow = self.timeline.itemAt(total_achievement_count).widget()
        total_time = TimeFormatter.hf_to_ts(last_row.unlock_time.text())
        current_achievemnt_count = 0
        for i in range(self.timeline.count() - 1):
            row: AchievementRow = self.timeline.itemAt(i).widget()
            unlock_time = TimeFormatter.hf_to_ts(row.unlock_time.text())
            if current_time > unlock_time:
                current_achievemnt_count += 1
                row.setStyleSheet("background-color: lightgreen;")
            else:
                row.setStyleSheet("background-color: white;")
        QtWidgets.QApplication.processEvents()
        self.replay_time_postfix.setText(f' / {TimeFormatter.ts_to_hf(total_time)} | {round(current_time/total_time*100, 1)}%')
        self.replay_ach_count_value.setText(str(current_achievemnt_count))
        self.replay_ach_count_postfix.setText(f' / {total_achievement_count} | {round(current_achievemnt_count/total_achievement_count*100, 1)}%')


    def toggle_replay(self, checked):
        if checked:
            print('start')
        else:
            print('stop')


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = AchievementsTimelineApp()
    window.show()
    sys.exit(app.exec())
