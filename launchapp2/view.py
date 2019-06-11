"""The view may access a controller, but not vice versa"""

import os
import logging
from itertools import chain
from functools import partial
from collections import OrderedDict as odict

from .vendor.Qt import QtWidgets, QtCore, QtCompat, QtGui
from .vendor import six, qargparse
from .version import version
from . import resources as res, model, delegates, util

px = res.px


class Window(QtWidgets.QMainWindow):
    title = "Launch App 2.0"

    def __init__(self, ctrl, parent=None):
        super(Window, self).__init__(parent)
        self.setWindowTitle(self.title)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setWindowIcon(QtGui.QIcon(res.find("Logo_64.png")))

        self._count = 0

        pages = odict((
            ("home", QtWidgets.QWidget()),

            # Pages matching a particular state
            ("booting", QtWidgets.QWidget()),
            ("errored", QtWidgets.QWidget()),
            ("noapps", QtWidgets.QWidget()),
        ))

        panels = {
            "pages": QtWidgets.QStackedWidget(),
            "header": QtWidgets.QWidget(),
            "body": QtWidgets.QWidget(),
            "footer": QtWidgets.QWidget(),
        }

        widgets = {
            "bootMessage": QtWidgets.QLabel("Loading.."),
            "errorMessage": QtWidgets.QLabel("Uh oh..<br>"
                                             "See Console for details"),
            "noappsMessage": QtWidgets.QLabel("No applications found"),
            "pkgnotfoundMessage": QtWidgets.QLabel(
                "One or more packages could not be found"
            ),

            # Header
            "logo": QtWidgets.QLabel(),
            "appVersion": QtWidgets.QLabel(version),

            "projectBtn": QtWidgets.QToolButton(),
            "projectMenu": QtWidgets.QMenu(),
            "projectName": QtWidgets.QLabel("None"),
            "projectVersions": QtWidgets.QComboBox(),

            "apps": SlimTableView(),

            # Error page
            "continue": QtWidgets.QPushButton("Continue"),
            "reset": QtWidgets.QPushButton("Reset"),

            "dockToggles": QtWidgets.QWidget(),

            "stateIndicator": QtWidgets.QLabel(),
        }

        # The order is reflected in the UI
        docks = odict((
            ("app", App(ctrl)),
            ("packages", Packages(ctrl)),
            ("context", Context()),
            ("environment", Environment()),
            ("console", Console()),
            ("commands", Commands()),
            ("preferences", Preferences(self, ctrl)),
        ))

        # Expose to CSS
        for name, widget in chain(panels.items(),
                                  widgets.items(),
                                  pages.items()):
            widget.setAttribute(QtCore.Qt.WA_StyledBackground)
            widget.setObjectName(name)

        self.setCentralWidget(panels["pages"])

        # Add header to top-most portion of GUI above movable docks
        toolbar = self.addToolBar("header")
        toolbar.setObjectName("Header")
        toolbar.addWidget(panels["header"])
        toolbar.setMovable(False)

        # Fill horizontal space
        panels["header"].setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Preferred)

        for page in pages.values():
            panels["pages"].addWidget(page)

        # Layout
        layout = QtWidgets.QVBoxLayout(pages["booting"])
        layout.addWidget(QtWidgets.QWidget(), 1)
        layout.addWidget(widgets["bootMessage"], 0, QtCore.Qt.AlignHCenter)
        layout.addWidget(QtWidgets.QWidget(), 1)

        layout = QtWidgets.QGridLayout(pages["home"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(panels["body"], 1, 0)

        layout = QtWidgets.QVBoxLayout(pages["errored"])
        layout.addWidget(QtWidgets.QWidget(), 1)
        layout.addWidget(widgets["errorMessage"], 0, QtCore.Qt.AlignHCenter)
        layout.addWidget(widgets["continue"], 0, QtCore.Qt.AlignHCenter)
        layout.addWidget(widgets["reset"], 0, QtCore.Qt.AlignHCenter)
        layout.addWidget(QtWidgets.QWidget(), 1)

        layout = QtWidgets.QVBoxLayout(pages["noapps"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(QtWidgets.QWidget(), 1)
        layout.addWidget(widgets["noappsMessage"], 0, QtCore.Qt.AlignHCenter)
        layout.addWidget(QtWidgets.QWidget(), 1)

        #  _______________________________________________________
        # |          |         |         |               |        |
        # |   logo   | project |---------|               |--------|
        # |__________|_________|_________|_______________|________|
        #

        layout = QtWidgets.QGridLayout(panels["header"])
        layout.setHorizontalSpacing(px(10))
        layout.setVerticalSpacing(0)

        def addColumn(widgets, *args, **kwargs):
            """Convenience function for adding columns to GridLayout"""
            addColumn.row = getattr(addColumn, "row", -1)
            addColumn.row += kwargs.get("offset", 1)

            for row, widget in enumerate(widgets):
                layout.addWidget(widget, row, addColumn.row, *args)

            if kwargs.get("stretch"):
                layout.setColumnStretch(addColumn.row, 1)

        addColumn([widgets["projectBtn"]], 2, 1)
        addColumn([widgets["projectName"],
                   widgets["projectVersions"]])

        addColumn([QtWidgets.QWidget()], stretch=True)  # Spacing
        addColumn([widgets["dockToggles"]], 2, 1)

        addColumn([QtWidgets.QWidget()], stretch=True)  # Spacing

        addColumn([QtWidgets.QLabel("launchapp2"),
                   widgets["appVersion"]])
        addColumn([widgets["logo"]], 2, 1)  # spans 2 rows

        layout = QtWidgets.QHBoxLayout(widgets["dockToggles"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for name, dock in docks.items():
            toggle = QtWidgets.QPushButton()
            toggle.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                 QtWidgets.QSizePolicy.Expanding)
            toggle.setObjectName(name + "Toggle")
            toggle.setCheckable(True)
            toggle.setFlat(True)
            toggle.setProperty("type", "toggle")
            toggle.setToolTip("%s\n%s" % (type(dock).__name__, dock.__doc__ or ""))
            toggle.setIcon(res.icon(dock.icon))
            toggle.setIconSize(QtCore.QSize(px(32), px(32)))

            def on_toggled(dock, toggle):
                dock.setVisible(toggle.isChecked())
                self.on_dock_toggled(dock, toggle.isChecked())

            def on_visible(dock, toggle, state):
                toggle.setChecked(dock.isVisible())

            toggle.clicked.connect(partial(on_toggled, dock, toggle))

            # Store reference for showEvent
            dock.toggle = toggle

            # Store reference for update_advanced_controls
            toggle.dock = dock

            # Create two-way connection; when dock is programatically
            # closed, or closed by other means, update toggle to reflect this.
            dock.visibilityChanged.connect(partial(on_visible, dock, toggle))

            layout.addWidget(toggle)

        layout = QtWidgets.QVBoxLayout(panels["body"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widgets["apps"])

        status_bar = self.statusBar()
        status_bar.addPermanentWidget(widgets["stateIndicator"])

        # Setup
        widgets["logo"].setPixmap(res.pixmap("Logo_64"))
        widgets["logo"].setScaledContents(True)
        widgets["projectBtn"].setMenu(widgets["projectMenu"])
        widgets["projectBtn"].setPopupMode(widgets["projectBtn"].InstantPopup)
        widgets["projectBtn"].setIcon(res.icon("Default_Project"))
        widgets["projectBtn"].setIconSize(QtCore.QSize(px(32), px(32)))

        widgets["projectVersions"].setModel(ctrl.models["projectVersions"])

        docks["packages"].set_model(ctrl.models["packages"])
        docks["context"].set_model(ctrl.models["context"])
        docks["environment"].set_model(ctrl.models["environment"])
        docks["commands"].set_model(ctrl.models["commands"])
        widgets["apps"].setModel(ctrl.models["apps"])

        widgets["projectMenu"].aboutToShow.connect(self.on_show_project_menu)
        widgets["errorMessage"].setAlignment(QtCore.Qt.AlignHCenter)

        # Signals
        widgets["reset"].clicked.connect(self.on_reset_clicked)
        widgets["continue"].clicked.connect(self.on_continue_clicked)
        widgets["apps"].activated.connect(self.on_app_clicked)
        widgets["projectName"].setText(ctrl.current_project)
        selection_model = widgets["apps"].selectionModel()
        selection_model.selectionChanged.connect(self.on_app_changed)

        ctrl.models["apps"].modelReset.connect(self.on_apps_reset)
        ctrl.models["projectVersions"].modelReset.connect(
            self.on_project_versions_reset)
        ctrl.state_changed.connect(self.on_state_changed)
        ctrl.logged.connect(self.on_logged)
        ctrl.project_changed.connect(self.on_project_changed)

        self._pages = pages
        self._widgets = widgets
        self._panels = panels
        self._docks = docks
        self._ctrl = ctrl

        self.setup_docks()
        self.on_state_changed("booting")
        self.update_advanced_controls()

        # Enable mouse tracking for tooltips
        QtWidgets.QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        """Forward tooltips to status bar whenever the mouse moves"""
        if event.type() == QtCore.QEvent.MouseMove:
            try:
                tooltip = obj.toolTip()

                # Some tooltips are multi-line, and the statusbar
                # typically ignores newlines and writes it all out
                # as one long line.
                tooltip = tooltip.splitlines()[0]

                self.statusBar().showMessage(tooltip, 2000)
            except (AttributeError, IndexError):
                pass

        # Forward the event to subsequent listeners
        return False

    def createPopupMenu(self):
        """Null; defaults to checkboxes for docks and toolbars"""

    def update_advanced_controls(self):
        shown = bool(self._ctrl.state.retrieve("showAdvancedControls"))
        self._widgets["projectVersions"].setVisible(shown)

        # Update dock toggles
        toggles = self._widgets["dockToggles"].layout()
        for index in range(toggles.count()):
            item = toggles.itemAt(index)
            widget = item.widget()
            dock = widget.dock

            visible = (not dock.advanced) or shown
            widget.setVisible(visible)

            if not visible:
                dock.hide()

    def setup_docks(self):
        for dock in self._docks.values():
            dock.hide()

        self.setTabPosition(QtCore.Qt.RightDockWidgetArea,
                            QtWidgets.QTabWidget.North)
        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea,
                            QtWidgets.QTabWidget.North)

        area = QtCore.Qt.RightDockWidgetArea
        first = list(self._docks.values())[0]
        self.addDockWidget(area, first)

        for dock in self._docks.values():
            if dock is first:
                continue

            self.addDockWidget(area, dock)
            self.tabifyDockWidget(first, dock)

    def reset(self):
        self._ctrl.reset()

    def on_reset_clicked(self):
        self.reset()

    def on_continue_clicked(self):
        self._ctrl.state.to_ready()

    def on_setting_changed(self, argument):
        if isinstance(argument, qargparse.Button):
            if argument["name"] == "resetLayout":
                self.tell("Restoring layout..")
                geometry = self._ctrl.state.retrieve("default/geometry")
                window = self._ctrl.state.retrieve("default/windowState")
                self.restoreGeometry(geometry)
                self.restoreState(window)
            return

        key = argument["name"]
        value = argument.read()

        self.tell("Storing %s = %s" % (key, value))
        self._ctrl.state.store(argument["name"], argument.read())

        # Subsequent settings are stored to disk
        if key == "showAdvancedControls":
            self.update_advanced_controls()

    def on_dock_toggled(self, dock, visible):
        """Make toggled dock the active dock"""

        if not visible:
            return

        # Handle the easy cases first
        app = QtWidgets.QApplication.instance()
        ctrl_held = app.keyboardModifiers() & QtCore.Qt.ControlModifier
        allow_multiple = bool(self._ctrl.state.retrieve("allowMultipleDocks"))

        if ctrl_held or not allow_multiple:
            for d in self._docks.values():
                d.setVisible(d == dock)
            return

        # Otherwise we'll want to make the newly visible dock the active tab.

        # Turns out to not be that easy
        # https://forum.qt.io/topic/42044/
        # tabbed-qdockwidgets-how-to-fetch-the-qwidgets-under-a-qtabbar/10

        # TabBar's are dynamically created as the user
        # moves docks around, and not all of them are
        # visible or in use at all times. (Poor garbage collection)
        bars = self.findChildren(QtWidgets.QTabBar)

        # The children of a QTabBar isn't the dock directly, but rather
        # the buttons in the tab, which are of type QToolButton.

        uid = dock.windowTitle()  # note: This must be unique

        # Find which tab is associated to this QDockWidget, if any
        def find_dock(bar):
            for index in range(bar.count()):
                if uid == bar.tabText(index):
                    return index

        for bar in bars:
            index = find_dock(bar)

            if index is not None:
                break
        else:
            # Dock isn't part of any tab and is directly visible
            return

        bar.setCurrentIndex(index)

    def on_show_project_menu(self):
        self.tell("Changing project..")

        all_projects = self._ctrl.list_projects()
        current_project = self._ctrl.current_project

        def on_accept(project):
            project = project.text()
            assert isinstance(project, six.string_types)

            self._ctrl.select_project(project)
            self._ctrl.state.store("startupProject", project)

        menu = self._widgets["projectMenu"]
        menu.clear()

        group = QtWidgets.QActionGroup(menu)
        group.triggered.connect(on_accept)

        for project in all_projects:
            action = QtWidgets.QAction(project, menu)
            action.setCheckable(True)

            if project == current_project:
                action.setChecked(True)

            group.addAction(action)
            menu.addAction(action)

    def on_project_changed(self, before, after):
        # Happens when editing requirements
        if before != after:
            action = "Changing"
        else:
            action = "Refreshing"

        self.tell("%s %s -> %s" % (action, before, after))
        self.setWindowTitle("%s - %s" % (self.title, after))
        self._widgets["projectName"].setText(after)

    def on_show_error(self):
        self._docks["console"].append(self._ctrl.current_error)
        self._docks["console"].raise_()

    def tell(self, message):
        self._docks["console"].append(message, logging.INFO)
        self.statusBar().showMessage(message, 2000)

    def on_logged(self, message, level):
        self._docks["console"].append(message, level)

    def on_state_changed(self, state):
        self.tell("State: %s" % state)

        page = self._pages.get(str(state), self._pages["home"])
        page_name = page.objectName()
        self._panels["pages"].setCurrentWidget(page)

        launch_btn = self._docks["app"]._widgets["launchBtn"]
        launch_btn.setText("Launch")

        for dock in self._docks.values():
            dock.setEnabled(True)

        if page_name == "home":
            self._widgets["apps"].setEnabled(state == "ready")
            self._widgets["projectBtn"].setEnabled(state == "ready")
            self._widgets["projectVersions"].setEnabled(state == "ready")

        elif page_name == "noapps":
            self._widgets["projectBtn"].setEnabled(True)
            self._widgets["noappsMessage"].setText(
                "No applications found for %s" % self._ctrl.current_project
            )

        if state == "launching":
            self._docks["app"].setEnabled(False)

        if state == "loading":
            for dock in self._docks.values():
                dock.setEnabled(False)

        if state in ("pkgnotfound", "errored"):
            console = self._docks["console"]
            console.show()
            self.on_dock_toggled(console, visible=True)

            page = self._pages["errored"]
            self._panels["pages"].setCurrentWidget(page)

            self._widgets["apps"].setEnabled(False)
            launch_btn.setEnabled(False)
            launch_btn.setText("Package not found")

        if state == "notresolved":
            self._widgets["apps"].setEnabled(False)
            launch_btn.setEnabled(False)
            launch_btn.setText("Failed to resolve")

        self._widgets["stateIndicator"].setText(str(state))
        self.update_advanced_controls()

    def on_launch_clicked(self):
        self._ctrl.launch()

    def on_project_versions_reset(self):
        self._widgets["projectVersions"].setCurrentIndex(0)

    def on_apps_reset(self):
        app = self._ctrl.state.retrieve("startupApplication")

        index = 0
        model = self._ctrl.models["apps"]

        if app:
            for row in range(model.rowCount()):
                index = model.index(row, 0, QtCore.QModelIndex())
                name = index.data(QtCore.Qt.DisplayRole)

                if app == name:
                    index = row
                    self.tell("Using startup application %s" % name)
                    break

        self._widgets["apps"].selectRow(index)

    def on_app_clicked(self, index):
        """An app was double-clicked or Return was hit"""

        app = self._docks["app"]
        app.show()
        self.on_dock_toggled(app, visible=True)

    def on_app_changed(self, selected, deselected):
        """The current app was changed

        Arguments:
            selected (QtCore.QItemSelection): ..
            deselected (QtCore.QItemSelection): ..

        """

        index = selected.indexes()[0]
        app_name = index.data(QtCore.Qt.DisplayRole)
        self._ctrl.select_application(app_name)
        self._docks["app"].refresh(index)

    def showEvent(self, event):
        super(Window, self).showEvent(event)
        self._ctrl.state.store("default/geometry", self.saveGeometry())
        self._ctrl.state.store("default/windowState", self.saveState())

        if self._ctrl.state.retrieve("geometry"):
            self.tell("Restoring layout..")
            self.restoreGeometry(self._ctrl.state.retrieve("geometry"))
            self.restoreState(self._ctrl.state.retrieve("windowState"))

    def closeEvent(self, event):
        self.tell("Storing state..")
        self._ctrl.state.store("geometry", self.saveGeometry())
        self._ctrl.state.store("windowState", self.saveState())

        super(Window, self).closeEvent(event)


class DockWidget(QtWidgets.QDockWidget):
    """Default HTML <b>docs</b>"""

    icon = ""
    advanced = False

    def __init__(self, title, parent=None):
        super(DockWidget, self).__init__(title, parent)
        self.layout().setContentsMargins(15, 15, 15, 15)

        panels = {
            "body": QtWidgets.QStackedWidget(),
            "help": QtWidgets.QLabel(),
        }

        for name, widget in panels.items():
            widget.setObjectName(name)

        central = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(panels["help"])
        layout.addWidget(panels["body"])

        if self.__doc__:
            panels["help"].setText(self.__doc__.splitlines()[0])
        else:
            panels["help"].hide()

        self.__panels = panels

        QtWidgets.QDockWidget.setWidget(self, central)

    def setWidget(self, widget):
        body = self.__panels["body"]

        while body.widget(0):
            body.removeWidget(body.widget(0))

        body.addWidget(widget)


class App(DockWidget):
    icon = "Alert_Info_32"

    def __init__(self, ctrl, parent=None):
        super(App, self).__init__("App", parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setObjectName("App")

        panels = {
            "central": QtWidgets.QWidget(),
            "shortcuts": QtWidgets.QWidget(),
            "footer": QtWidgets.QWidget(),
        }

        widgets = {
            "icon": QtWidgets.QLabel(),
            "label": QtWidgets.QLabel("Autodesk Maya"),
            "version": QtWidgets.QComboBox(),
            "tool": QtWidgets.QToolButton(),

            "commands": SlimTableView(),
            "extras": SlimTableView(),

            # Shortcuts
            "tools": qargparse.QArgumentParser(),
            "environment": QtWidgets.QToolButton(),
            "packages": QtWidgets.QToolButton(),
            "terminal": QtWidgets.QToolButton(),

            "launchBtn": QtWidgets.QPushButton("Launch"),
        }

        # Expose to CSS
        for name, widget in chain(panels.items(), widgets.items()):
            widget.setAttribute(QtCore.Qt.WA_StyledBackground)
            widget.setObjectName(name)

        widgets["tools"].add_argument("", type=qargparse.Choice, items=[
            "maya",
            "mayapy",
            "mayabatch",
        ], default="mayapy")

        layout = QtWidgets.QHBoxLayout(panels["shortcuts"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(widgets["environment"])
        layout.addWidget(widgets["packages"])
        layout.addWidget(widgets["terminal"])
        layout.addWidget(QtWidgets.QWidget(), 1)  # push to the left

        layout = QtWidgets.QHBoxLayout(panels["footer"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widgets["launchBtn"])

        layout = QtWidgets.QGridLayout(panels["central"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(px(10))
        layout.setVerticalSpacing(0)

        layout.addWidget(widgets["icon"], 0, 0, 2, 1)
        layout.addWidget(widgets["tools"], 0, 1, 2, 1)
        # layout.addWidget(widgets["label"], 0, 1, QtCore.Qt.AlignTop)
        # layout.addWidget(QtWidgets.QWidget(), 0, 1, 1, 1)
        # layout.addWidget(widgets["version"], 1, 1, QtCore.Qt.AlignTop)
        layout.addWidget(widgets["commands"], 2, 0, 1, 2)
        # layout.addWidget(widgets["extras"], 3, 0, 1, 2)
        # layout.addWidget(panels["shortcuts"], 10, 0, 1, 2)
        layout.addWidget(QtWidgets.QWidget(), 15, 0)
        # layout.setColumnStretch(1, 1)
        layout.setRowStretch(15, 1)
        layout.addWidget(panels["footer"], 20, 0, 1, 2)

        widgets["icon"].setPixmap(res.pixmap("Alert_Info_32"))
        widgets["environment"].setIcon(res.icon(Environment.icon))
        widgets["packages"].setIcon(res.icon(Packages.icon))
        widgets["terminal"].setIcon(res.icon(Console.icon))
        widgets["tool"].setText("maya")

        for sc in ("environment", "packages", "terminal"):
            widgets[sc].setIconSize(QtCore.QSize(px(32), px(32)))

        # QtCom
        widgets["launchBtn"].setCheckable(True)
        widgets["launchBtn"].clicked.connect(self.on_launch_clicked)

        proxy_model = model.ProxyModel(ctrl.models["commands"])
        widgets["commands"].setModel(proxy_model)

        self._ctrl = ctrl
        self._panels = panels
        self._widgets = widgets
        self._proxy = proxy_model

        self.setWidget(panels["central"])

    def on_launch_clicked(self):
        self._ctrl.launch()

    def refresh(self, index):
        name = index.data(QtCore.Qt.DisplayRole)
        icon = index.data(QtCore.Qt.DecorationRole)
        icon = icon.pixmap(QtCore.QSize(px(64), px(64)))
        self._widgets["label"].setText(name)
        self._widgets["icon"].setPixmap(icon)

        self._proxy.setup(include=[
            ("appName", name),
            ("running", "running"),
        ])


class Console(DockWidget):
    """Debugging information, mostly for developers"""

    icon = "Prefs_Screen_32"

    def __init__(self, parent=None):
        super(Console, self).__init__("Console", parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setObjectName("Console")

        panels = {
            "central": QtWidgets.QWidget()
        }

        widgets = {
            "text": QtWidgets.QTextEdit()
        }

        self.setWidget(panels["central"])

        widgets["text"].setReadOnly(True)

        layout = QtWidgets.QVBoxLayout(panels["central"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widgets["text"])

        self._widgets = widgets

    def append(self, line, level=logging.INFO):
        color = {
            logging.WARNING: "<font color=\"red\">",
        }.get(level, "<font color=\"#222\">")

        line = "%s%s</font><br>" % (color, line)

        cursor = self._widgets["text"].textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)

        self._widgets["text"].setTextCursor(cursor)
        self._widgets["text"].insertHtml(line)

        scrollbar = self._widgets["text"].verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class Packages(DockWidget):
    """Packages associated with the currently selected application"""

    icon = "File_Archive_32"
    advanced = True

    def __init__(self, ctrl, parent=None):
        super(Packages, self).__init__("Packages", parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setObjectName("Packages")

        panels = {
            "central": QtWidgets.QWidget()
        }

        widgets = {
            "view": SlimTableView(),
            "status": QtWidgets.QStatusBar(),
        }

        self.setWidget(panels["central"])

        layout = QtWidgets.QVBoxLayout(panels["central"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(widgets["view"])
        layout.addWidget(widgets["status"])

        widgets["view"].setStretch(1)
        widgets["view"].setItemDelegate(delegates.Package(ctrl, self))
        widgets["view"].setEditTriggers(widgets["view"].DoubleClicked)
        widgets["view"].verticalHeader().setDefaultSectionSize(px(20))
        widgets["view"].setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        widgets["view"].customContextMenuRequested.connect(self.on_right_click)

        widgets["status"].setSizeGripEnabled(False)

        self._ctrl = ctrl
        self._widgets = widgets

    def set_model(self, model):
        self._widgets["view"].setModel(model)
        model.modelReset.connect(self.on_model_changed)
        model.dataChanged.connect(self.on_model_changed)

    def on_model_changed(self):
        model = self._widgets["view"].model()
        package_count = model.rowCount()
        override_count = len([i for i in model.items if i["override"]])
        disabled_count = len([i for i in model.items if i["disabled"]])

        self._widgets["status"].showMessage(
            "%d Packages, %d Overridden, %d Disabled" % (
                package_count,
                override_count,
                disabled_count,
            ))

    def on_right_click(self, position):
        view = self._widgets["view"]
        index = view.indexAt(position)
        model = index.model()

        menu = QtWidgets.QMenu(self)
        edit = QtWidgets.QAction("Edit")
        disable = QtWidgets.QAction("Disable")
        default = QtWidgets.QAction("Set to default")
        earliest = QtWidgets.QAction("Set to earliest")
        latest = QtWidgets.QAction("Set to latest")
        openfile = QtWidgets.QAction("Open file location")

        disable.setCheckable(True)
        disable.setChecked(model.data(index, "disabled"))

        menu.addAction(edit)
        menu.addAction(disable)
        menu.addSeparator()
        menu.addAction(default)
        menu.addAction(earliest)
        menu.addAction(latest)
        menu.addSeparator()
        menu.addAction(openfile)
        menu.move(QtGui.QCursor.pos())

        picked = menu.exec_()

        if picked is None:
            return  # Cancelled

        if picked == edit:
            self._widgets["view"].edit(index)

        if picked == default:
            model.setData(index, None, "override")
            model.setData(index, False, "disabled")

        if picked == earliest:
            versions = model.data(index, "versions")
            model.setData(index, versions[0], "override")
            model.setData(index, False, "disabled")

        if picked == latest:
            versions = model.data(index, "versions")
            model.setData(index, versions[-1], "override")
            model.setData(index, False, "disabled")

        if picked == openfile:
            package = model.data(index, "package")
            fname = os.path.join(package.root, "package.py")
            util.open_file_location(fname)

        if picked == disable:
            model.setData(index, None, "override")
            model.setData(index, disable.isChecked(), "disabled")


class Context(DockWidget):
    """Full context relative the currently selected application"""

    icon = "App_Generic_4_32"
    advanced = True

    def __init__(self, parent=None):
        super(Context, self).__init__("Context", parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setObjectName("Context")

        panels = {
            "central": QtWidgets.QWidget()
        }

        widgets = {
            "view": QtWidgets.QTreeView()
        }

        layout = QtWidgets.QVBoxLayout(panels["central"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widgets["view"])

        self._panels = panels
        self._widgets = widgets

        self.setWidget(panels["central"])

    def set_model(self, model):
        self._widgets["view"].setModel(model)


class Environment(DockWidget):
    """Full environment relative the currently selected application"""

    icon = "App_Heidi_32"
    advanced = True

    def __init__(self, parent=None):
        super(Environment, self).__init__("Environment", parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setObjectName("Environment")

        panels = {
            "central": QtWidgets.QWidget()
        }

        widgets = {
            "view": QtWidgets.QTreeView()
        }

        layout = QtWidgets.QVBoxLayout(panels["central"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widgets["view"])

        self._panels = panels
        self._widgets = widgets

        self.setWidget(panels["central"])

    def set_model(self, model):
        self._widgets["view"].setModel(model)


class Commands(DockWidget):
    """Currently running commands"""

    icon = "App_Pulse_32"
    advanced = True

    def __init__(self, parent=None):
        super(Commands, self).__init__("Commands", parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setObjectName("Commands")

        panels = {
            "central": QtWidgets.QWidget(),
            "body": QtWidgets.QWidget(),
            "footer": QtWidgets.QWidget(),
        }

        widgets = {
            "view": SlimTableView(),
            "stdout": QtWidgets.QTextEdit(),
            "stderr": QtWidgets.QTextEdit(),
        }

        layout = QtWidgets.QVBoxLayout(panels["central"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(panels["body"])
        # layout.addWidget(panels["footer"])

        layout = QtWidgets.QVBoxLayout(panels["body"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widgets["view"])

        layout = QtWidgets.QVBoxLayout(panels["footer"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widgets["stdout"])
        layout.addWidget(widgets["stderr"])

        self._panels = panels
        self._widgets = widgets

        self.setWidget(panels["central"])

    def set_model(self, model):
        self._widgets["view"].setModel(model)


class Preferences(DockWidget):
    """Preferred settings relative the current user"""

    icon = "Action_GoHome_32"

    options = [
        qargparse.Info("startupProject", help=(
            "Load this project on startup"
        )),
        qargparse.Info("startupApplication", help=(
            "Load this application on startup"
        )),

        qargparse.Separator("Theme"),

        qargparse.Info("primaryColor", default="white", help=(
            "Main color of the GUI"
        )),
        qargparse.Info("secondaryColor", default="steelblue", help=(
            "Secondary color of the GUI"
        )),

        qargparse.Button("resetLayout", help=(
            "Reset stored layout to their defaults"
        )),

        qargparse.Separator("Settings"),

        qargparse.Boolean("smallIcons", enabled=False, help=(
            "Draw small icons"
        )),
        qargparse.Boolean("allowMultipleDocks", help=(
            "Allow more than one dock to exist at a time"
        )),
        qargparse.Boolean("showAdvancedControls", help=(
            "Show developer-centric controls"
        )),

        qargparse.Separator("System"),

        # Provided by controller
        qargparse.Info("pythonExe"),
        qargparse.Info("pythonVersion"),
        qargparse.Info("qtVersion"),
        qargparse.Info("qtBinding"),
        qargparse.Info("qtBindingVersion"),
        qargparse.Info("rezLocation"),
        qargparse.Info("rezVersion"),
        qargparse.Info("memcachedURI"),
        qargparse.InfoList("rezPackagesPath"),
        qargparse.InfoList("rezLocalPath"),
        qargparse.InfoList("rezReleasePath"),
        qargparse.Info("settingsPath"),
    ]

    def __init__(self, window, ctrl, parent=None):
        super(Preferences, self).__init__("Preferences", parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setObjectName("Preferences")

        panels = {
            "scrollarea": QtWidgets.QScrollArea(),
            "central": QtWidgets.QWidget(),
        }

        widgets = {
            "options": qargparse.QArgumentParser(
                self.options, storage=ctrl._storage)
        }

        layout = QtWidgets.QVBoxLayout(panels["central"])
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widgets["options"])

        panels["scrollarea"].setWidget(panels["central"])
        panels["scrollarea"].setWidgetResizable(True)

        widgets["options"].changed.connect(self.handler)

        self._panels = panels
        self._widgets = widgets
        self._ctrl = ctrl
        self._window = window

        self.setWidget(panels["scrollarea"])

    def handler(self, argument):
        self._window.on_setting_changed(argument)


class SlimTableView(QtWidgets.QTableView):
    def __init__(self, parent=None):
        super(SlimTableView, self).__init__(parent)
        self.setShowGrid(False)
        self.verticalHeader().hide()
        self.setSelectionMode(self.SingleSelection)
        self.setSelectionBehavior(self.SelectRows)
        self._stretch = 0

    def setStretch(self, column):
        self._stretch = column

    def refresh(self):
        header = self.horizontalHeader()
        QtCompat.setSectionResizeMode(
            header, self._stretch, QtWidgets.QHeaderView.Stretch)

    def setModel(self, model):
        model.rowsInserted.connect(self.refresh)
        model.modelReset.connect(self.refresh)
        super(SlimTableView, self).setModel(model)
        self.refresh()
