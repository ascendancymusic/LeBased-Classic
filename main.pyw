import re
import random
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.event import EventDispatcher
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton
from kivy.config import Config
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.clock import Clock
from datetime import datetime, timedelta
from kivy.properties import BooleanProperty
from kivy.properties import NumericProperty
from kivymd.uix.dialog import MDDialog
from kivy.uix.boxlayout import BoxLayout
import sqlite3
from kivymd.icon_definitions import md_icons
from kivy.properties import StringProperty
from kivy.properties import ObjectProperty, ListProperty
from tree_hierarchy import TreeLayout, TreeNode 
from weather import fetch_weather
LabelBase.register(name="Tex", fn_regular="fonts/tex-gyre-adventor.regular.otf")
LabelBase.register(name="TexBold", fn_regular="fonts/tex-gyre-adventor.bold.otf")
Window.maximize()
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')



class SwitchState(EventDispatcher):
    switch_active = BooleanProperty(False)
    background_image_source = StringProperty("graphics/gradient.jpg")
    color1 = ListProperty([0.341, 0.773, 0.714]) 
    color2 = ListProperty([0.082, 0.596, 0.584]) 
    color3 = ListProperty([0.102, 0.373, 0.478]) 
    color4 = ListProperty([0, 0.169, 0.357]) 
    color5 = ListProperty([0.341, 0.773, 0.714]) 
    title_image = StringProperty("graphics/title.png")

    def load_switch_state(self):
        conn = sqlite3.connect("data/theme.db")
        c = conn.cursor()
        c.execute('SELECT switch_state FROM switch_status WHERE id = 1')
        result = c.fetchone()
        conn.close()

        if result is not None:
            switch_state = result[0]
            self.switch_active = bool(switch_state)
            if self.switch_active:
                self.background_image_source = "graphics/gradient2.jpg"
                self.color1 = [1, 0.984, 0, 0.5]
                self.color2 = [0.145, 0.325, 0.529, 0.5]
                self.color3 = [0.169, 0.22, 0.486, 0.5]
                self.color4 = [0.173, 0.129, 0.365, 0.5]
                self.color5 = [0.173, 0.129, 0.365, 0.5]
            else:
                self.background_image_source = "graphics/gradient.jpg"

class AddToDoScreen(Screen, SwitchState):
    task_id = None

    def set_task_details(self, task_id, title, description):
        self.task_id = task_id
        self.ids.title.text = title
        self.ids.description.text = description

    def validate_and_add_task(self):
        title = self.ids.title.text
        description = self.ids.description.text
        if title and description:
            if self.task_id:
                self.update_task(self.task_id, title, description)
            else:
                self.add_new_task(title, description)
            self.manager.current = 'todo'
            self.manager.transition.direction = 'right'

    def initialize_database():
        conn = sqlite3.connect('data/tasks.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tasks
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      title TEXT NOT NULL,
                      description TEXT,
                      date TEXT,
                      checkbox_state INTEGER)''')
        conn.commit()
        conn.close()

    initialize_database()

    def add_new_task(self, title, description):
        current_date_str = self.manager.get_screen('todo').current_date.strftime("%d.%m.%Y")
        conn = sqlite3.connect('data/tasks.db')
        c = conn.cursor()
        c.execute("INSERT INTO tasks (title, description, date, checkbox_state) VALUES (?, ?, ?, ?)", (title, description, current_date_str, 0))
        conn.commit()
        conn.close()
        self.manager.get_screen('todo').refresh_tasks()

    def update_task(self, task_id, title, description):
        conn = sqlite3.connect('data/tasks.db')
        c = conn.cursor()
        c.execute("UPDATE tasks SET title=?, description=? WHERE id=?", (title, description, task_id))
        conn.commit()
        conn.close()
        self.manager.get_screen('todo').refresh_tasks()

    def on_pre_leave(self, *args):
        self.ids.title.text = ''
        self.ids.description.text = ''
        self.task_id = None
        
    def on_pre_enter(self, *args):
        Window.bind(on_keyboard=self.on_back_button)
        self.load_switch_state()

    def on_leave(self, *args):
        Window.unbind(on_keyboard=self.on_back_button)        
        
    def on_back_button(self, window, key, *args):
        if key == 27:
            self.manager.current = 'todo'
            self.manager.transition.direction = 'right'
            return True
        return False


class TaskBoxLayout(BoxLayout):
    title_label = ObjectProperty(None)
    description_label = ObjectProperty(None)
    checkbox = ObjectProperty(None)
    task_id = None
    checkbox_state = NumericProperty(0)
    switch_state = ObjectProperty(None)  
    bg_color = ListProperty([0.173, 0.129, 0.365, 0.75])

    def on_checkbox_active(self, checkbox, active):
        self.checkbox_state = 1 if active else 0
        if self.task_id:
            conn = sqlite3.connect('data/tasks.db')
            c = conn.cursor()
            c.execute("UPDATE tasks SET checkbox_state=? WHERE id=?", (self.checkbox_state, self.task_id))
            conn.commit()
            conn.close()

        if active:
            self.title_label.text = '[s]' + self.title_label.text + '[/s]'
            self.description_label.text = '[s]' + self.description_label.text + '[/s]'
        else:
            self.title_label.text = self.title_label.text.replace('[s]', '').replace('[/s]', '')
            self.description_label.text = self.description_label.text.replace('[s]', '').replace('[/s]', '')

        self.bg_color = (1, 0.988, 0.259, 0.5) if active else (0.173, 0.129, 0.365, 0.75)

    def set_checkbox_state(self, state):
        self.checkbox_state = state
        if self.checkbox:
            self.checkbox.active = bool(state)

    def on_checkbox_state(self, instance, value):
        if self.checkbox:
            self.checkbox.active = bool(value)



class ToDoScreen(Screen, SwitchState):
    current_date = datetime.now()
    touch_start_x = None

    def __init__(self, **kwargs):
        super(ToDoScreen, self).__init__(**kwargs)
        self.refresh_tasks()

    def on_pre_enter(self, *args):
        Window.bind(on_keyboard=self.on_back_button)
        Window.bind(on_keyboard=self.on_key_down)
        Window.bind(on_touch_move=self.on_touch_move_window)
        Window.bind(on_touch_up=self.on_touch_up_window)
        self.load_switch_state()

    def on_leave(self, *args):
        Window.unbind(on_keyboard=self.on_back_button)
        Window.unbind(on_touch_move=self.on_touch_move_window)
        Window.unbind(on_touch_up=self.on_touch_up_window)

    def on_back_button(self, window, key, *args):
        if key == 27:
            self.manager.current = 'main'
            self.manager.transition.direction = 'right'
            return True
        return False

    def on_touch_down(self, touch):
        self.touch_start_x = touch.x
        return super(ToDoScreen, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        return super(ToDoScreen, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.touch_start_x is not None:
            dx = touch.x - self.touch_start_x
            if dx > 200:  # Right swipe
                self.update_date(-1)
            elif dx < -200:  # Left swipe
                self.update_date(1)
        self.touch_start_x = None
        return super(ToDoScreen, self).on_touch_up(touch)

    def on_touch_move_window(self, window, touch):
        return self.on_touch_move(touch)

    def on_touch_up_window(self, window, touch, *args):
        return self.on_touch_up(touch)

    def on_key_down(self, window, key, *args):
        if key == 275:  # D button
            self.update_date(1)
            return True
        elif key == 276:
            self.update_date(-1)
            return True
        return False

    def update_date(self, delta):
        self.current_date += timedelta(days=delta)
        self.ids.date_label.text = self.current_date.strftime("%A, %B %d, %Y")
        self.refresh_tasks()
        self.update_weather()

    def update_weather(self):
        weather_info = fetch_weather(self.current_date)
        self.ids.weather_label.text = weather_info

    def on_enter(self):
        self.update_weather()

    def refresh_tasks(self):
        current_date_str = self.current_date.strftime("%d.%m.%Y")
        task_layout = self.ids.task_list
        task_layout.clear_widgets()
        conn = sqlite3.connect('data/tasks.db')
        c = conn.cursor()
        c.execute("SELECT * FROM tasks WHERE date=?", (current_date_str,))
        tasks = c.fetchall()
        for task in tasks:
            task_widget = TaskBoxLayout()
            task_widget.title_label.text = task[1]
            task_widget.description_label.text = task[2]
            task_widget.task_id = task[0]
            task_widget.set_checkbox_state(task[4])
            task_layout.add_widget(task_widget)
        conn.close()

    def add_task(self, title, description):
        current_date_str = self.current_date.strftime("%d.%m.%Y")
        conn = sqlite3.connect('data/tasks.db')
        c = conn.cursor()
        c.execute("INSERT INTO tasks (title, description, date, checkbox_state) VALUES (?, ?, ?, ?)", (title, description, current_date_str, 0))
        conn.commit()
        conn.close()
        self.refresh_tasks()

    def delete_task(self, task_id):
        conn = sqlite3.connect('data/tasks.db')
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
        conn.close()
        self.refresh_tasks()

    def edit_task(self, task_id):
        conn = sqlite3.connect('data/tasks.db')
        c = conn.cursor()
        c.execute("SELECT title, description FROM tasks WHERE id=?", (task_id,))
        task = c.fetchone()
        conn.close()
        if task:
            self.manager.get_screen('add_todo').set_task_details(task_id, task[0], task[1])
            self.manager.current = 'add_todo'
            self.manager.transition.direction = 'left'



class StatsScreen(Screen, SwitchState):
    def on_pre_enter(self, *args):
        Window.bind(on_keyboard=self.on_back_button)
        self.load_switch_state()

    def on_leave(self, *args):
        Window.unbind(on_keyboard=self.on_back_button)

    def on_back_button(self, window, key, *args):
        if key == 27:
            self.manager.current = 'main'
            return True
        return False
    
    stats_text = StringProperty()
    average_sleep_time = StringProperty("N/A")
    average_get_up_time = StringProperty("N/A")

    def on_enter(self):
        self.refresh_stats()

    def refresh_stats(self):
        stats_text = self.get_stats_text()
        stats_label = self.ids.stats_label
        stats_label.text = stats_text
        stats_label.color = (1, 1, 1, 1)

        self.update_average_sleep_time()


        self.update_average_get_up_time()

    def get_stats_text(self):
        stats_text = ""
        with open("data/stats.txt", "r") as file:
            lines = file.readlines()
            entries = [] 
            current_entry = ""
            for line in lines:
                if line.strip():
                    current_entry += line
                else: 
                    entries.append(current_entry.strip())
                    current_entry = ""

            if current_entry: 
                entries.append(current_entry.strip())

            entries.sort(reverse=True)

            for entry in entries:
                lines = entry.split('\n')
                for index, line in enumerate(lines):
                    if (index + 1) % 7 == 1: 
                        stats_text += f"[font=TexBold]{line.strip()}[/font]\n"
                    else:
                        stats_text += f"[font=Tex]{line.strip()}[/font]\n"
                stats_text += "\n\n"  

        return stats_text

        

    def update_average_sleep_time(self):
        sleep_times = []
        with open("data/stats.txt", "r") as file:
            lines = file.readlines()
            for line in lines:
                if "Sleep: " in line:
                    try:
                        sleep_time = line.strip().split(": ")[1]
                        hours, minutes = map(int, sleep_time.split(":"))
                        total_minutes = hours * 60 + minutes
                        sleep_times.append(total_minutes)
                    except ValueError:
                        pass

        if sleep_times:
            average_minutes = sum(sleep_times) // len(sleep_times)
            average_hours = average_minutes // 60
            average_minutes %= 60
            self.average_sleep_time = f"{average_hours:02d}:{average_minutes:02d}"
        else:
            self.average_sleep_time = "N/A"

    def update_average_get_up_time(self):
        get_up_times = []
        with open("data/stats.txt", "r") as file:
            lines = file.readlines()
            for line in lines:
                if "Got up: " in line:
                    try:
                        get_up_time = line.strip().split(": ")[1]
                        hours, minutes = map(int, get_up_time.split(":"))
                        total_minutes = hours * 60 + minutes
                        get_up_times.append(total_minutes)
                    except ValueError:
                        pass

        if get_up_times:
            average_minutes = sum(get_up_times) // len(get_up_times)
            average_hours = average_minutes // 60
            average_minutes %= 60
            self.average_get_up_time = f"{average_hours:02d}:{average_minutes:02d}"
        else:
            self.average_get_up_time = "N/A"

    def show_delete_confirmation_dialog(self):
        dialog = MDDialog(
            title="Delete Confirmation",
            text="Are you sure you want to delete all data?",
            size_hint=(0.8, 0.18),
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    on_release=lambda *args: dialog.dismiss()
                ),
                MDFlatButton(
                    text="Delete",
                    on_release=lambda *args: self.delete_stats_data(dialog)
                ),
            ]
        )
        dialog.open()

    def delete_stats_data(self, dialog):
        with open("data/stats.txt", "w") as file:
            file.write("")
        dialog.dismiss()
        self.refresh_stats()  # Refresh the stats screen after deletion 


class SleeparScreen(Screen, SwitchState):
    def on_pre_enter(self, *args):
        Window.bind(on_keyboard=self.on_back_button)
        self.load_switch_state()

    def on_leave(self, *args):
        Window.unbind(on_keyboard=self.on_back_button)

    def on_back_button(self, window, key, *args):
        if key == 27:  # The back button key code on Android and ESC key on Windows
            self.manager.current = 'main'
            return True 
        return False
    sleep_button_disabled = BooleanProperty(False)
    text_input_visible = BooleanProperty(False)
    done_button_visible = BooleanProperty(False)
    cleanar_options_visible = BooleanProperty(False)
    get_up_data = None

    def on_enter(self):
        Clock.schedule_interval(self.update_time, 0)

    def update_time(self, dt):
        current_time = datetime.now().strftime("%H:%M")
        self.ids.current_time_label.text = current_time

    def switch_buttons(self, mode):
        sleep_button = self.ids.sleep_button
        get_up_button = self.ids.get_up_button
        cleanar_label = self.ids.cleanar_label
        cleanar_options = self.ids.cleanar_options

        if mode == 'sleep':
            sleep_button.disabled = True
            get_up_button.disabled = True
            cleanar_label.opacity = 1
            cleanar_options.opacity = 1
        elif mode == 'get_up':
            sleep_button.disabled = True
            get_up_button.disabled = True
            cleanar_label.opacity = 0
            cleanar_options.opacity = 0

    def show_cleanar_options(self):
        self.switch_buttons('sleep')
        self.cleanar_options_visible = BooleanProperty(True)

    def hide_cleanar_options(self):
        cleanar_label = self.ids.cleanar_label
        cleanar_options = self.ids.cleanar_options
        cleanar_label.opacity = 0
        cleanar_options.opacity = 0

    def set_sleep_button_state(self, status):
        self.sleep_button_disabled = status == 'ofc' or status == 'no'

    def on_cleanar_button_press(self, status):
        self.hide_cleanar_options()
        get_up_button = self.ids.get_up_button

        # Get current time
        current_time = datetime.now().strftime("%H:%M")

        # Determine text based on current time
        if "20:00" <= current_time <= "21:29":
            dialog_text = "Alien sleepar early af dude!"
        elif "21:30" <= current_time <= "21:59":
            dialog_text = "WOW! Early sleepar! Good night!"
        elif "22:00" <= current_time <= "22:15":
            dialog_text = "Great! Sleepar well!"
        elif "22:16" <= current_time <= "22:30":
            dialog_text = "Nice! Good night!"
        elif "22:31" <= current_time <= "22:45":
            dialog_text = "Not bad!"
        elif "22:46" <= current_time <= "23:00":
            dialog_text = "You can do better, but good night!"
        elif "23:01" <= current_time <= "23:59":
            dialog_text = "Go to sleep earlier tomorrow."
        elif "00:00" <= current_time <= "05:00":
            dialog_text = "What is wrong with you?"
        else:
            dialog_text = "Alien time sleepar"

        # Create and display the dialog
        dialog = MDDialog(title='Sleep time!', text=dialog_text, size_hint=(0.8, 0.1))
        dialog.font_name = "TexBold"
        dialog.open()

        # Automatically dismiss the dialog after 3 seconds
        Clock.schedule_once(lambda dt: dialog.dismiss(), 3)

        # Update sleep and clean status in data/stats.txt
        current_date = datetime.now().strftime("%d.%m.%Y")
        current_time = datetime.now().strftime("%H:%M")

        # Check if sleep time is between 0:00 and 5:00 to consider it part of the previous day
        if 0 <= int(current_time.split(':')[0]) <= 5:
            current_date = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")

        with open("data/stats.txt", "r+") as file:
            lines = file.readlines()
            found = False
            for index, line in enumerate(lines):
                if line.startswith(current_date):
                    found = True
                    lines[index + 2] = f"Sleep: {current_time}\n"
                    lines[index + 3] = f"Clean: {'Yes' if status == 'ofc' else 'No'}\n"
                    file.seek(0)
                    file.truncate()
                    file.writelines(lines)
                    break

            if not found:
                lines.append(f"{current_date}\n")
                lines.append(f"Got up: -\n")
                lines.append(f"Sleep: {current_time}\n")
                lines.append(f"Clean: {'Yes' if status == 'ofc' else 'No'}\n\n\n")
                file.seek(0)
                file.writelines(lines)

        get_up_button.disabled = False

    def get_up_pressed(self):
        current_date = datetime.now().strftime("%d.%m.%Y")
        current_time = datetime.now().strftime("%H:%M")
        self.text_input_visible = True
        self.done_button_visible = True
        self.get_up_data = (current_date, current_time)
        get_up_button = self.ids.get_up_button
        get_up_button.disabled = True
        self.switch_buttons('get_up')

    def done_button_pressed(self):
        current_date, current_time = self.get_up_data
        dream_text = self.ids.dream_input.text.strip()
        self.text_input_visible = False
        self.done_button_visible = False
        get_up_button = self.ids.get_up_button
        sleep_button = self.ids.sleep_button
        get_up_button.disabled = True
        sleep_button.disabled = False
        dream_text = self.ids.dream_input.text if self.ids.dream_input.text.strip() else "No dreams"

        # Determine text based on current time
        if "05:00" <= current_time <= "06:59":
            dialog_text = "Alien wake upar early af dude!"
        elif "07:00" <= current_time <= "07:45":
            dialog_text = "WOW! Early get up! Good Morning King!"
        elif "07:46" <= current_time <= "08:15":
            dialog_text = "Great! Good morning!"
        elif "08:16" <= current_time <= "08:45":
            dialog_text = "Nice! Good morning!"
        elif "08:46" <= current_time <= "09:15":
            dialog_text = "Not bad! Go seize the day!"
        elif "09:16" <= current_time <= "09:59":
            dialog_text = "You can do better, but good morning!"
        elif "10:00" <= current_time <= "11:00":
            dialog_text = "Get up a lot earlier tomorrow."
        elif "11:01" <= current_time <= "12:00":
            dialog_text = "What is wrong with you?"
        else:
            dialog_text = "What's wrong with you dude who gets up this late?"

        # Create and display the dialog
        dialog = MDDialog(title='Morning!', text=dialog_text, size_hint=(0.8, 0.1))
        dialog.font_name = "TexBold"
        dialog.open()

        # Automatically dismiss the dialog after 3 seconds
        Clock.schedule_once(lambda dt: dialog.dismiss(), 3)

        with open("data/stats.txt", "r+") as file:
            lines = file.readlines()
            found = False
            for index, line in enumerate(lines):
                if line.startswith(current_date):
                    found = True
                    lines[index + 1] = f"Got up: {current_time}\n"
                    lines[index + 4] = f"Dreams: {dream_text}\n\n"  
                    file.seek(0)
                    file.truncate()
                    file.writelines(lines)
                    break

            if not found:
                lines.append(f"{current_date}\n")
                lines.append(f"Got up: {current_time}\n")
                lines.append(f"Sleep: -\n")
                lines.append(f"Clean: -\n")
                lines.append(f"Dreams: {dream_text}\n\n\n")  
                file.seek(0)
                file.writelines(lines)

    def sleep_button_pressed(self):
        self.show_cleanar_options()


class PlannerScreen(Screen, SwitchState):
    def on_pre_enter(self, *args):
        Window.bind(on_keyboard=self.on_back_button)
        self.load_switch_state()

    def on_leave(self, *args):
        Window.unbind(on_keyboard=self.on_back_button)

    def on_back_button(self, window, key, *args):
        if key == 27:  # The back button key code on Android and ESC key on Windows
            self.manager.current = 'main'
            return True
        return False


class AboutScreen(Screen, SwitchState):
    def on_pre_enter(self, *args):
        Window.bind(on_keyboard=self.on_back_button)
        self.load_switch_state() 

    def on_leave(self, *args):
        Window.unbind(on_keyboard=self.on_back_button)

    def on_back_button(self, window, key, *args):
        if key == 27:  # The back button key code on Android and ESC key on Windows
            self.manager.current = 'main'
            return True
        return False


class MainScreen(Screen, SwitchState):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.create_table()  # Ensure the table exists in the database
        self.load_switch_state()  # Load switch state from database during initialization

    def create_table(self):
        conn = sqlite3.connect("data/theme.db")
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS switch_status (
                        id INTEGER PRIMARY KEY,
                        switch_state INTEGER
                     )''')
        conn.commit()
        conn.close()

    def update_switch_state(self, state):
        conn = sqlite3.connect("data/theme.db")
        c = conn.cursor()
        # Check if record exists
        c.execute('SELECT id FROM switch_status WHERE id = 1')
        result = c.fetchone()
        
        if result:
            # Update existing record
            c.execute('UPDATE switch_status SET switch_state = ? WHERE id = 1', (state,))
        else:
            # Insert new record
            c.execute('INSERT INTO switch_status (id, switch_state) VALUES (1, ?)', (state,))
        
        conn.commit()
        conn.close()
        self.load_switch_state()

    def on_switch_active(self, instance, value):
        if value:
            self.update_switch_state(1)
        else:
            self.update_switch_state(0)

    def on_pre_enter(self, *args):
        self.load_switch_state() 
        


class LeBasedApp(MDApp):
    def build(self):
        self.icon = "graphics/LeBased.png"
        self.switch_state = SwitchState()
        self.switch_state.load_switch_state()  # Load the switch state at the beginning

        # Load KV files for each screen
        Builder.load_file('screens/todo_screen.kv')
        Builder.load_file('screens/stats_screen.kv')
        Builder.load_file('screens/sleepar_screen.kv')
        Builder.load_file('screens/planner_screen.kv')
        Builder.load_file('screens/about_screen.kv')
        Builder.load_file('screens/add_todo.kv')
        Builder.load_file('screens/lebased.kv')

        # Screen Manager
        sm = ScreenManager(transition=FadeTransition())

        # Add screens
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(ToDoScreen(name='todo'))
        sm.add_widget(StatsScreen(name='stats'))
        sm.add_widget(SleeparScreen(name='sleepar'))
        sm.add_widget(PlannerScreen(name='planner'))
        sm.add_widget(AboutScreen(name='about'))
        sm.add_widget(AddToDoScreen(name='add_todo'))

        Window.bind(on_keyboard=self.on_keyboard)

        return sm

    def on_start(self):
        
        self.update_quote()

    def load_quotes(self):
        quotes = []
        with open('data/quotes.txt', 'r') as file:
            quote = ''
            for line in file:
                line = line.strip()
                if re.match(r'^\d+: ', line):
                    if quote:
                        quotes.append(quote)
                    quote = line
                else:
                    quote += '\n' + line
            if quote:
                quotes.append(quote)
        return quotes

    def switch_to_main(self, instance):
        self.root.current = 'main'

    def switch_to_todo(self, instance):
        self.root.current = 'todo'

    def switch_to_stats(self, instance):
        self.root.current = 'stats'

    def switch_to_sleepar(self, instance):
        self.root.current = 'sleepar'

    def switch_to_planner(self, instance):
        self.root.current = 'planner'

    def switch_to_about(self, instance):
        self.root.current = 'about'

    def switch_to_add_todo(self, instance):
        self.root.current = 'add_todo'

    def update_quote(self):
        main_screen = self.root.get_screen('main')
        quotes = self.load_quotes()
        random_quote = random.choice(quotes)
        random_quote = re.sub(r'^\d+: ', '', random_quote)
        main_screen.ids.quote_label.text = f"[font=TexBold]Random insight[/font]: [font=Tex]{random_quote}[/font]"
        main_screen.ids.quote_label_shadow.text = main_screen.ids.quote_label.text

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        if key == 292:
            Window.fullscreen = not Window.fullscreen

if __name__ == '__main__':
    LeBasedApp().run()