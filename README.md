# create-forwarder-dll

Given an input DLL, creates an output DLL of a different name that
forwards all exported symbol names of input DLL from output DLL
to the input DLL.

Needs to be run from a Visual Studio activated shell in order
to find and run `cl.exe`, `dumpbin.exe` and `lib.exe`.
