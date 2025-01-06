import sqlite3
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.graphics import Line, Color
from kivy.properties import ObjectProperty, ListProperty, BooleanProperty, NumericProperty
from kivy.core.window import Window
from kivy.uix.scatter import Scatter
from kivy.uix.scatter import ScatterPlane
from kivy.input.providers.mouse import MotionEvent

# Database setup
conn = sqlite3.connect('data/plans.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS nodes
             (id INTEGER PRIMARY KEY,
              parent_id INTEGER,
              text TEXT,
              pos_x REAL,
              pos_y REAL,
              checkbox_active INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS lines
             (parent_id INTEGER,
              child_id INTEGER)''')

conn.commit()

class TreeNode(BoxLayout):
    node_button = ObjectProperty(None)
    children_nodes = ListProperty([])
    parent_layout = ObjectProperty(None)
    is_drawing = False
    is_dragging = False
    start_pos = None
    line = None
    parent_node = None
    is_root = BooleanProperty(False)
    checkbox_active = BooleanProperty(False)
    node_id = NumericProperty(-1)  # Unique ID for each node

    def __init__(self, **kwargs):
        super(TreeNode, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.children_nodes = []
        self.bind(children_nodes=self.on_children_nodes_change)
        self.ids.text_input.bind(text=self.update_text_in_database)
        self.ctrl_pressed = False  # Track if the CTRL key is pressed
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_key_up=self.on_key_up)

    def on_key_down(self, window, key, *args):
        if key == 305:  
            self.ctrl_pressed = True

    def on_key_up(self, window, key, *args):
        if key == 305: 
            self.ctrl_pressed = False

    def start_drawing_line(self, instance):
        self.is_drawing = True
        self.start_pos = (self.center_x, self.top)
        Window.bind(mouse_pos=self.update_line)
        Window.bind(on_touch_up=self.create_child_node)

    def update_line(self, window, pos):
        if not self.is_drawing:
            return

        if self.line:
            self.parent_layout.canvas.remove(self.line)

        scatter = self.parent_layout.parent
        if isinstance(scatter, Scatter):
            scatter_pos = scatter.to_local(*pos)

            mouse_x, mouse_y = scatter_pos
            with self.parent_layout.canvas:
                Color(1, 1, 1, 1)
                self.line = Line(points=[self.start_pos[0], self.start_pos[1], mouse_x, mouse_y], width=4)

    def create_child_node(self, window, touch):
        if not self.is_drawing:
            return

        self.is_drawing = False
        Window.unbind(mouse_pos=self.update_line)
        Window.unbind(on_touch_up=self.create_child_node)

        if self.line:
            self.parent_layout.canvas.remove(self.line)
            self.line = None

        scatter = self.parent_layout.parent
        if isinstance(scatter, Scatter):
            touch_pos = scatter.to_local(*touch.pos)

            new_node = TreeNode()
            new_node.is_root = False
            new_node.center_x = touch_pos[0]
            new_node.top = touch_pos[1]
            new_node.parent_layout = self.parent_layout
            new_node.parent_node = self
            self.children_nodes.append(new_node)
            self.parent_layout.add_widget(new_node)
            self.parent_layout.update_node_positions()

            # Save node data to database
            new_node.save_to_database()

            # Save line data to database
            self.save_line_to_database(new_node)

    def delete_node(self):
        if self.parent_layout and self.parent_layout.root_node != self:
            for child in self.children_nodes[:]:
                child.delete_node()

            if self.parent_node:
                self.parent_node.children_nodes.remove(self)

            self.parent_layout.remove_widget(self)

            if self.line:
                self.parent_layout.canvas.remove(self.line)
                self.line = None

            self.parent_layout.update_node_positions()

            # Delete node data from database
            self.delete_from_database()

            # Delete line data from database
            self.delete_lines_from_database()

    def update_hint_text(self, instance):
        if instance.text:
            instance.hint_text = ""

    def on_checkbox_active(self, instance, value):
        self.checkbox_active = value
        if value:
            for child in self.children_nodes:
                child.on_checkbox_active(instance, value)
        self.update_parent_checkbox()

        # Update checkbox state in the database
        self.update_checkbox_in_database()

    def on_children_nodes_change(self, instance, value):
        for child in value:
            child.bind(checkbox_active=self.on_child_checkbox_active_change)
        self.update_parent_checkbox()

    def on_child_checkbox_active_change(self, instance, value):
        self.update_parent_checkbox()

    def update_parent_checkbox(self):
        if not self.children_nodes:
            return
        
        all_children_active = all(child.checkbox_active for child in self.children_nodes)
        self.checkbox_active = all_children_active
        
        if self.parent_node:
            self.parent_node.update_parent_checkbox()

        # Update checkbox state in the database
        self.update_checkbox_in_database()

    def start_dragging(self, instance):
        self.is_dragging = True
        self.initial_pos = self.center_x, self.center_y
        self.subnode_positions = self.get_all_subnode_positions()
        Window.bind(mouse_pos=self.update_drag)
        Window.bind(on_touch_up=self.stop_dragging)

    def get_all_subnode_positions(self):
        positions = []

        def recurse(node):
            positions.append((node, node.center_x, node.center_y))
            for child in node.children_nodes:
                recurse(child)

        recurse(self)
        return positions

    def update_drag(self, window, pos):
        if not self.is_dragging:
            return
        
        scatter = self.parent_layout.parent
        if isinstance(scatter, Scatter):
            scatter_pos = scatter.to_local(*pos)

            dx = scatter_pos[0] - self.initial_pos[0]
            dy = scatter_pos[1] - self.initial_pos[1]

            self.center_x = scatter_pos[0]
            self.center_y = scatter_pos[1]

            if self.ctrl_pressed:
                for node, orig_x, orig_y in self.subnode_positions:
                    node.center_x = orig_x + dx
                    node.center_y = orig_y + dy

            self.parent_layout.update_node_positions()

    def stop_dragging(self, window, touch):
        if not self.is_dragging:
            return
        
        self.is_dragging = False
        Window.unbind(mouse_pos=self.update_drag)
        Window.unbind(on_touch_up=self.stop_dragging)

        # Update node positions in the database
        self.update_position_in_database()
        if self.ctrl_pressed:
            for node, _, _ in self.subnode_positions:
                node.update_position_in_database()

    def save_to_database(self):
        # Check if the node already exists in the database
        c.execute('''SELECT id FROM nodes WHERE id = ?''', (self.node_id,))
        if c.fetchone():
            # Update existing node
            c.execute('''UPDATE nodes SET parent_id = ?, text = ?, pos_x = ?, pos_y = ?, checkbox_active = ?
                         WHERE id = ?''',
                      (self.parent_node.node_id if self.parent_node else None,
                       self.ids.text_input.text,
                       self.center_x,
                       self.top,
                       1 if self.checkbox_active else 0,
                       self.node_id))
        else:
            # Insert new node
            c.execute('''INSERT INTO nodes (id, parent_id, text, pos_x, pos_y, checkbox_active)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (self.node_id if self.node_id != -1 else None,
                       self.parent_node.node_id if self.parent_node else None,
                       self.ids.text_input.text,
                       self.center_x,
                       self.top,
                       1 if self.checkbox_active else 0))
            if self.node_id == -1:
                self.node_id = c.lastrowid

        conn.commit()

    def update_checkbox_in_database(self):
        c.execute('''UPDATE nodes SET checkbox_active = ?
                     WHERE id = ?''',
                  (1 if self.checkbox_active else 0,
                   self.node_id))
        conn.commit()

    def update_position_in_database(self):
        c.execute('''UPDATE nodes SET pos_x = ?, pos_y = ?
                     WHERE id = ?''',
                  (self.center_x,
                   self.top,
                   self.node_id))
        conn.commit()

    def update_text_in_database(self, instance, value):
        c.execute('''UPDATE nodes SET text = ?
                     WHERE id = ?''',
                  (value,
                   self.node_id))
        conn.commit()

    def delete_from_database(self):
        c.execute('''DELETE FROM nodes WHERE id = ?''', (self.node_id,))
        conn.commit()

    def save_line_to_database(self, child_node):
        c.execute('''INSERT INTO lines (parent_id, child_id)
                     VALUES (?, ?)''',
                  (self.node_id, child_node.node_id))
        conn.commit()

    def delete_lines_from_database(self):
        c.execute('''DELETE FROM lines WHERE parent_id = ? OR child_id = ?''', (self.node_id, self.node_id))
        conn.commit()


class TreeLayout(Widget):
    root_node = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(TreeLayout, self).__init__(**kwargs)
        self.root_node = TreeNode()
        self.root_node.is_root = True
        self.root_node.node_id = 0  # Set root node ID to 0
        self.root_node.pos_hint = {'center_x': 0.5, 'top': 1}
        self.root_node.parent_layout = self
        self.add_widget(self.root_node)
        self.bind(size=self.update_node_positions, pos=self.update_node_positions)

        # Load nodes from database on initialization
        self.load_nodes_from_database()

        # Save root node to database if it doesn't already exist
        if not self.node_exists_in_database(self.root_node.node_id):
            self.root_node.save_to_database()

        self.load_lines_from_database()

        # Bind mouse wheel scroll for zooming
        Window.bind(on_scroll=self.on_scroll)

    def node_exists_in_database(self, node_id):
        c.execute('''SELECT id FROM nodes WHERE id = ?''', (node_id,))
        return c.fetchone() is not None

    def load_nodes_from_database(self):
        # Fetch all nodes from the database
        c.execute('''SELECT * FROM nodes''')
        rows = c.fetchall()

        # Create TreeNode objects for each row and add them to the TreeLayout
        node_dict = {0: self.root_node}
        for row in rows:
            node_id, parent_id, text, pos_x, pos_y, checkbox_active = row
            if node_id == 0:
                # Update root node properties from the database
                self.root_node.center_x = pos_x
                self.root_node.top = pos_y
                self.root_node.checkbox_active = True if checkbox_active == 1 else False
                self.root_node.ids.text_input.text = text
            else:
                new_node = TreeNode()
                new_node.node_id = node_id
                new_node.center_x = pos_x
                new_node.top = pos_y
                new_node.checkbox_active = True if checkbox_active == 1 else False
                new_node.ids.text_input.text = text
                new_node.parent_layout = self
                new_node.parent_node = node_dict.get(parent_id)

                # Add node to the parent node or root if it's a root node
                if new_node.parent_node:
                    new_node.parent_node.children_nodes.append(new_node)

                node_dict[node_id] = new_node
                self.add_widget(new_node)

    def load_lines_from_database(self):
        c.execute('''SELECT parent_id, child_id FROM lines''')
        lines = c.fetchall()

        for parent_id, child_id in lines:
            parent_node = self.get_node_by_id(parent_id)
            child_node = self.get_node_by_id(child_id)
            if parent_node and child_node:
                with self.canvas.before:
                    Color(1, 1, 1, 1)
                    Line(points=[parent_node.center_x, parent_node.top - 25, child_node.center_x, child_node.top], width=4)

    def get_node_by_id(self, node_id):
        for child in self.children:
            if isinstance(child, TreeNode) and child.node_id == node_id:
                return child
        return None

    def draw_tree(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.draw_lines(self.root_node, self.root_node.center_x, self.root_node.top - 25)

    def draw_lines(self, node, parent_x, parent_y):
        if not node.children_nodes:
            return
        for child in node.children_nodes:
            Color(1, 1, 1, 1)
            Line(points=[parent_x, parent_y, child.center_x, child.top], width=4)
            self.draw_lines(child, child.center_x, child.top)

    def update_node_positions(self, *args):
        self.root_node.center_x = self.width / 2
        self.root_node.top = self.height
        self.draw_tree()

    def on_touch_down(self, touch):
        if super(TreeLayout, self).on_touch_down(touch):
            return True
        if 'button' in touch.profile and touch.button in ('scrollup', 'scrolldown'):
            # If the touch is a scroll event (like mousewheel), handle it
            self.on_scroll(None, 0, 1 if touch.button == 'scrollup' else -1)
            return True
        return False

    def on_touch_move(self, touch):
        if super(TreeLayout, self).on_touch_move(touch):
            return True
        return False

    def on_touch_up(self, touch):
        if super(TreeLayout, self).on_touch_up(touch):
            return True
        return False

    def on_scroll(self, window, scroll_x, scroll_y, *args):
        scatter = self.parent
        if isinstance(scatter, ScatterPlane):
            if scroll_y > 0:
                scatter.scale *= 0.9
            elif scroll_y < 0:
                scatter.scale *= 1.1
