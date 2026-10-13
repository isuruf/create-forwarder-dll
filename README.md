# create-forwarder-dll

Given an input DLL, creates an output DLL of a different name that
forwards all exported symbol names of input DLL from output DLL
to the input DLL.

Needs a Visual Studio installation to run `cl.exe`, `dumpbin.exe`
and `lib.exe`.

```
usage: create_dll_forwarder [-h]
                            [--implementing-dll-name IMPLEMENTING_DLL_NAME]
                            [--machine MACHINE] [--no-temp-dir]
                            [--symbol-filter-regex SYMBOL_FILTER_REGEX]
                            input output [import_library]

Create a DLL that forwards to another DLL

positional arguments:
  input                 path to input DLL
  output                path to output DLL
  import_library        path to install the import library of the output DLL

options:
  -h, --help            show this help message and exit
  --implementing-dll-name IMPLEMENTING_DLL_NAME
                        When the `input` DLL is only the reference for the
                        symbols, but the actual implementation for them is
                        elsewhere
  --machine MACHINE     machine argument to cl.exe
  --no-temp-dir         Do not use a temporary directory to create
                        intermediaries
  --symbol-filter-regex SYMBOL_FILTER_REGEX
                        Only add symbols to forwarder DLL that match this
                        regex
```
