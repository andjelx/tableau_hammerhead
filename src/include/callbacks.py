class FileTransferProgress:
    def __init__(self, file_size: int):
        self._bytes = 0
        self._percentSize = file_size // 100
        self._next = 0
        self._percent = -1

    def __call__(self, bytes_transferred):
        self._bytes += bytes_transferred
        if self._bytes > self._next:
            self._next += self._percentSize
            self._percent += 1
            print(f'{self._percent}% ', end='')
