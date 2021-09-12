'''
This file is a part of dirscan, a tool for recursively
scanning and comparing directories and files

Copyright (C) 2010-2021 Svein Seldal, sveinse@seldal.com
URL: https://github.com/sveinse/dirscan

This application is licensed under GNU GPL version 3
<http://gnu.org/licenses/gpl.html>. This is free software: you are
free to change and redistribute it. There is NO WARRANTY, to the
extent permitted by law.
'''
import sys
import datetime


class PrintProgress:
    ''' A simple progress output manager. print() provides an ordinary print
        functionality, while progress() prints a line for displaying progress.
        Both accepts syntax similar to print(). progress() does not print the
        line with newline allowing it to be overwritten. Any subsequenct calls
        to progress() will only print the new line it if delta_ms time has
        passed, and when it does, it will overwrite the previous progress line.
        print() will also overwrite the last progress() printed line.
         '''

    def __init__(self, file=sys.stdout, delta_ms=200, show_progress=True):
        ''' file - stream to print to
            delta_ms - Minimum time between each progress() prints
            show_progress - Enables progress printing altogether
        '''
        self.file = file
        self.laststamp = datetime.datetime.now()
        self.timedelta = datetime.timedelta(milliseconds=delta_ms)
        self.show_progress = show_progress
        self.next_clear = False

    def print(self, *args, **kwargs):
        ''' Print a message '''

        if self.next_clear:
            # Go to start of line and erase rest of the line
            print('\r\x1b[K', end='', file=self.file)
            self.next_clear = False

        print(*args, file=self.file, **kwargs)
        self.file.flush()

    def progress(self, *args, **kwargs):
        ''' Print a progress message. force will print the
            progress message regardless of time '''
        force = kwargs.get('false')

        if self.show_progress:
            stamp = datetime.datetime.now()

            if force or (stamp - self.laststamp) > self.timedelta:
                self.laststamp = stamp
                self.next_clear = True
                self.print(*args, end='', **kwargs)
                self.next_clear = True

    def close(self):
        ''' Close the progress '''

        if self.next_clear:
            self.print('')

        self.file.flush()
