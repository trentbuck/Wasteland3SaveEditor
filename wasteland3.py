#!/usr/bin/python3
import argparse
import re
import tempfile
import ctypes
import pathlib
import pprint
import subprocess


__DOC__ = """ Save Game editor for Wasteland 3

Wasteland 3 save games use XML, which would be a no-brainer, except that
  * The XML is compressed with LZF, which is like DEFLATE only worse.
  * "XLZF\n" is prepended
  * Ten key/value pairs are prepended.
  * Two of these keys are the XML's compressed size and uncompressed size.

This script is written for Debian 10 GNU/NTOSkrnl a.k.a. "WSL1".
Known dependencies are:

  apt install python3 liblzf1
  apt install xmlstarlet   # pretty-print the XML (optional)
  apt install emacs        # or vim or whatever

Probably you can run this with Python on the Windows kernel personaliity, but
seriously, who wants to program on Windows?
"""


# This is "apt install liblzf1".
# We cannot just "./lzf -d" to decode, because the file has 11 lines of other garbage at the start.
# We could use head -11 or something, but at that point it's easier to do it directly in Python, I guess...
lzf = ctypes.cdll.LoadLibrary('liblzf.so.1')

class Game:
    def __init__(self, path: pathlib.Path):
        self.original_path = path
        with path.open('rb') as f:
            assert b'XLZF\n' == f.readline()
            self.Version =           re.fullmatch(rb'Version:=(.*)\n',      f.readline()).group(1)
            self.Location =          re.fullmatch(rb'Location:=(.*)\n',     f.readline()).group(1)
            self.SaveTime =          re.fullmatch(rb'SaveTime:=(.*)\n',     f.readline()).group(1)
            self.DataSize =      int(re.fullmatch(rb'DataSize:=(.*)\n',     f.readline()).group(1))
            self.SaveDataSize =  int(re.fullmatch(rb'SaveDataSize:=(.*)\n', f.readline()).group(1))
            self.Hash =              re.fullmatch(rb'Hash:=(.*)\n',         f.readline()).group(1)
            self.Indices =           re.fullmatch(rb'Indices:=(.*)\n',      f.readline()).group(1)
            self.Names =             re.fullmatch(rb'Names:=(.*)\n',        f.readline()).group(1)
            self.Levels =            re.fullmatch(rb'Levels:=(.*)\n',       f.readline()).group(1)
            self.Permadeath =        re.fullmatch(rb'Permadeath:=(.*)\n',   f.readline()).group(1)
            input_bytes = f.read()
            output_bytes = ctypes.create_string_buffer(self.DataSize)
            n = lzf.lzf_decompress(input_bytes, self.SaveDataSize,
                                    output_bytes, self.DataSize)
            if n != self.DataSize:
                print(f'n is {n}')
                print(f'self.DataSize is {self.DataSize}')
                print(f'self.SaveDataSize is {self.SaveDataSize}')
                print(output_bytes)
                print(ctypes.string_at(output_bytes, self.DataSize))
                raise RuntimeError('Shit happened')
            self.xml_bytes = ctypes.string_at(output_bytes, self.DataSize)

    def edit(self):
        tmp_path = pathlib.Path('tmp.xml')  # meh, use PWD
        with tmp_path.open('wb') as f:
            if True:
                # pretty-print the XML
                subprocess.run(['xmlstarlet', 'format'], input=self.xml_bytes, stdout=f)
            else:
                f.write(xml)
        subprocess.check_call(['sensible-editor', tmp_path])
        with tmp_path.open('rb') as f:
            self.xml_bytes = f.read()
            self.DataSize = len(self.xml_bytes)

    def save(self):
        # Compress the data again, remembering the new compressed size.
        max_output_length = self.DataSize * 2  # wild-ass guess
        output_bytes = ctypes.create_string_buffer(max_output_length)
        n = lzf.lzf_compress(self.xml_bytes, self.DataSize,
                             output_bytes, max_output_length)
        if n == 0:
            raise RuntimeError('Shit happened')
        self.SaveDataSize = n
        # /foo/bar/X/X.xml ==> /foo/bar/X_1/X_1.xml
        name = self.original_path.stem
        self.updated_path = (self.original_path.parent.parent) / f'{name}_HACKED' / f'{name}_HACKED.xml'
        self.updated_path.parent.mkdir(exist_ok=True)
        with self.updated_path.open('wb') as f:
            f.write(b'XLZF\n')
            f.write(b'Version:=' + self.Version + b'\n')
            f.write(b'Location:=' + self.Location + b'\n')
            f.write(b'SaveTime:=' + self.SaveTime + b'\n')
            f.write(b'DataSize:=' + str(self.DataSize).encode('UTF-8') + b'\n')
            f.write(b'SaveDataSize:=' + str(self.SaveDataSize).encode('UTF-8') + b'\n')
            f.write(b'Hash:=' + self.Hash + b'\n')
            f.write(b'Indices:=' + self.Indices + b'\n')
            f.write(b'Names:=' + self.Names + b'\n')
            f.write(b'Levels:=' + self.Levels + b'\n')
            f.write(b'Permadeath:=' + self.Permadeath + b'\n')
            f.write(ctypes.string_at(output_bytes, self.SaveDataSize))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_path',
                        nargs='?',
                        type=pathlib.Path,
                        default=pathlib.Path('Documents/My Games/Wasteland3/Save Games/test/test.xml'))
    args = parser.parse_args()
    game = Game(args.input_path)
    game.edit()
    game.save()


if __name__ == '__main__':
    main()
