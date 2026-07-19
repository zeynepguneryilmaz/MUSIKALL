import sys
import os
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtWebEngineWidgets import QWebEngineView


class ViewerWindow(QMainWindow):
    def closeEvent(self, event):
        try:
            tabs = self.centralWidget()
            if tabs is not None:
                for i in range(tabs.count()):
                    w = tabs.widget(i)
                    try:
                        if isinstance(w, QWebEngineView):
                            w.setHtml("")
                            w.stop()
                        if w is not None:
                            w.deleteLater()
                    except Exception:
                        pass

            self.setCentralWidget(None)

            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(0, app.quit)
        except Exception:
            pass

        event.accept()


def main():
    if len(sys.argv) < 2:
        print("Usage: python MUSIKALL_3d_viewer.py <html_file_1> [<html_file_2> ...]")
        sys.exit(1)

    html_files = sys.argv[1:]

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setQuitOnLastWindowClosed(True)

    win = ViewerWindow()
    win.setWindowTitle("3D Structures")
    win.resize(1200, 900)

    tabs = QTabWidget()
    win.setCentralWidget(tabs)

    for html_path in html_files:
        title = os.path.splitext(os.path.basename(html_path))[0]
        view = QWebEngineView()
        view.load(QUrl.fromLocalFile(os.path.abspath(html_path)))
        tabs.addTab(view, title)

    win.show()
    ret = app.exec()

    # WebEngine bazen process'i bırakmaz; kısa gecikmeli sert çıkış güvenlik ağı
    QTimer.singleShot(50, lambda: os._exit(0))
    sys.exit(ret)


if __name__ == "__main__":
    main()