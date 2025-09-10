# create-forwarder-dll

Given an input DLL, creates an output DLL of a different name that
forwards all exported symbol names of input DLL from output DLL
to the input DLL.

Needs a Visual Studio installation to run `cl.exe`, `dumpbin.exe`
and `lib.exe`.

```
usage: create_dll_forwarder [-h] [--machine MACHINE] [--no-temp-dir] input output

Create a DLL that forwards to another DLL

positional arguments:
  input              path to input DLL
  output             path to output DLL

options:
  -h, --help         show this help message and exit
  --machine MACHINE  machine argument to cl.exe
  --no-temp-dir      Do not use a temporary directory to create intermediaries
```
