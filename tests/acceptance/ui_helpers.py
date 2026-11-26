from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest


def find_item(item, name, visible=False):
    if item.objectName() == name and (not visible or item.isVisible()):
        return item
    for child in item.childItems():
        found = find_item(child, name, visible)
        if found is not None:
            return found
    return None


def find_items(item, name):
    items = [item] if item.objectName() == name and item.isVisible() else []
    for child in item.childItems():
        items.extend(find_items(child, name))
    return items


def click(window, item):
    assert item is not None and item.isEnabled()
    center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    assert 0 <= center.x() < window.width() and 0 <= center.y() < window.height()
    QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=center.toPoint())
    QTest.qWait(50)
