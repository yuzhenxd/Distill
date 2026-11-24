from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """在后台线程执行耗时函数（转写、模型请求、网络推送），结果通过信号回到主线程。

    with_progress=True 时，函数会收到关键字参数 progress(percent, message)；
    percent 为 -1 表示进度未知（界面显示忙碌动画）。
    """

    progress = Signal(int, str)
    succeeded = Signal(object)
    failed = Signal(str)

    _running: set = set()  # 持有引用，避免线程运行中被垃圾回收

    def __init__(self, fn, *args, with_progress: bool = False):
        super().__init__()
        self._fn = fn
        self._args = args
        self._with_progress = with_progress
        self.finished.connect(self._release)

    def _release(self) -> None:
        self.wait()  # finished 发出时线程可能还在收尾，等它真正退出再释放引用
        Worker._running.discard(self)

    def start(self) -> None:
        Worker._running.add(self)
        super().start()

    def run(self) -> None:
        kwargs = {"progress": self.progress.emit} if self._with_progress else {}
        try:
            result = self._fn(*self._args, **kwargs)
        except Exception as e:  # 线程边界：任何异常都要转成界面可显示的消息
            self.failed.emit(str(e) or e.__class__.__name__)
        else:
            self.succeeded.emit(result)
